"""
تقارير النظام المالية والإدارية.

مكان الملف المقترح داخل مشروع Django:
    your_app/views/financial_reports.py

يعتمد هذا الملف على النماذج الموجودة في:
    your_app/models.py

القوالب التي تستعملها الدوال:
    app/reports/dashboard.html
    app/reports/companies.html
    app/reports/applicants.html
    app/reports/accepted_applicants.html
    app/reports/financial.html

جميع الدوال محمية بتسجيل الدخول. يمكن إزالة login_required إذا كان نظام
الصلاحيات في المشروع يطبق الحماية من مستوى آخر.
"""

from __future__ import annotations

import csv
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Iterable

from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, Max, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from ..models import (
    Applicant,
    Application,
    ApplicationStatus,
    Company,
    CompanyJobRequest,
    CompanyJobRequestStatus,
    CurrencyChoices,
    Job,
    Voucher,
    VoucherCategoryType,
)


ZERO = Decimal("0.00")
MONEY_FIELD = DecimalField(max_digits=18, decimal_places=2)


def _parse_date(value: str | None) -> date | None:
    """تحويل التاريخ القادم من query string مع تجاهل القيمة غير الصحيحة."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _filters(request: HttpRequest) -> dict[str, Any]:
    """قراءة فلاتر التقارير المشتركة من الرابط."""
    from_date = _parse_date(request.GET.get("from_date"))
    to_date = _parse_date(request.GET.get("to_date"))
    currency = request.GET.get("currency", "").upper()

    supported_currencies = {value for value, _label in CurrencyChoices.choices}
    if currency not in supported_currencies:
        currency = ""

    return {
        "from_date": from_date,
        "to_date": to_date,
        "currency": currency,
        "from_date_value": from_date.isoformat() if from_date else "",
        "to_date_value": to_date.isoformat() if to_date else "",
        "currency_choices": CurrencyChoices.choices,
    }


def _date_range_kwargs(
    field_name: str,
    report_filters: dict[str, Any],
) -> dict[str, Any]:
    """إنشاء شروط تاريخية تصلح لـ filter على أي حقل Date/DateTime."""
    filters: dict[str, Any] = {}
    from_date = report_filters["from_date"]
    to_date = report_filters["to_date"]

    if from_date:
        filters[f"{field_name}__gte"] = (
            timezone.make_aware(datetime.combine(from_date, time.min))
            if field_name.endswith("_at")
            else from_date
        )
    if to_date:
        filters[f"{field_name}__lte"] = (
            timezone.make_aware(datetime.combine(to_date, time.max))
            if field_name.endswith("_at")
            else to_date
        )
    return filters


def _apply_voucher_filters(
    queryset: Any,
    report_filters: dict[str, Any],
) -> Any:
    """تطبيق التاريخ والعملة على السندات."""
    filters = _date_range_kwargs("voucher_date", report_filters)
    if report_filters["currency"]:
        filters["currency"] = report_filters["currency"]
    return queryset.filter(**filters)


def _money_total(queryset: Any) -> Decimal:
    """إرجاع مجموع آمن حتى عندما لا توجد سجلات."""
    value = queryset.aggregate(total=Sum("amount"))["total"]
    return value or ZERO


def _voucher_totals(
    vouchers: Any,
    report_filters: dict[str, Any],
) -> dict[str, Any]:
    """
    إجماليات السندات مفصولة حسب العملة.

    لا يتم جمع عملات مختلفة في صافي واحد؛ لذلك يعرض التقرير إجماليًا
    مستقلًا لكل عملة، ويعرض total_* فقط عند اختيار عملة من الفلتر.
    """
    grouped = (
        vouchers.values("currency", "type")
        .annotate(total=Coalesce(Sum("amount"), ZERO, output_field=MONEY_FIELD))
        .order_by("currency", "type")
    )

    by_currency: dict[str, dict[str, Decimal]] = {}
    for row in grouped:
        currency = row["currency"]
        bucket = by_currency.setdefault(
            currency,
            {"revenue": ZERO, "expenses": ZERO, "net": ZERO},
        )
        if row["type"] == VoucherCategoryType.RECEIPT:
            bucket["revenue"] += row["total"]
        elif row["type"] == VoucherCategoryType.PAYMENT:
            bucket["expenses"] += row["total"]
        bucket["net"] = bucket["revenue"] - bucket["expenses"]

    selected_currency = report_filters["currency"]
    selected = by_currency.get(
        selected_currency,
        {"revenue": ZERO, "expenses": ZERO, "net": ZERO},
    )

    return {
        "by_currency": by_currency,
        "total_revenue": selected["revenue"],
        "total_expenses": selected["expenses"],
        "net_profit": selected["net"],
    }


def _base_context(
    request: HttpRequest,
    report_filters: dict[str, Any],
) -> dict[str, Any]:
    """بيانات مشتركة تستعملها كل صفحات التقارير."""
    return {
        "report_filters": report_filters,
        "current_path": request.path,
        "today": timezone.localdate(),
    }


def _render_report(
    request: HttpRequest,
    template_name: str,
    context: dict[str, Any],
    report_filters: dict[str, Any],
) -> HttpResponse:
    common = _base_context(request, report_filters)
    common.update(context)
    return render(request, template_name, common)


def _status_label(status: str) -> str:
    return dict(ApplicationStatus.choices).get(status, status)


def _currency_label(currency: str) -> str:
    return dict(CurrencyChoices.choices).get(currency, currency)


@require_GET
@login_required
def reports(request: HttpRequest) -> HttpResponse:
    """
    لوحة التقارير الرئيسية.

    الرابط:
        /reports/
    """
    report_filters = _filters(request)
    vouchers = _apply_voucher_filters(Voucher.objects.all(), report_filters)
    financial = _voucher_totals(vouchers, report_filters)

    applications = Application.objects.all()
    applications = applications.filter(
        **_date_range_kwargs("created_at", report_filters)
    )

    job_requests = CompanyJobRequest.objects.all().filter(
        **_date_range_kwargs("created_at", report_filters)
    )
    companies = Company.objects.all()
    applicants = Applicant.objects.all().filter(
        **_date_range_kwargs("created_at", report_filters)
    )

    application_status_counts = {
        row["status"]: row["count"]
        for row in applications.values("status").annotate(count=Count("id"))
    }
    financial_currency_chart = [
        {
            "label": _currency_label(currency),
            "revenue": str(values["revenue"]),
            "expenses": str(values["expenses"]),
            "net": str(values["net"]),
        }
        for currency, values in financial["by_currency"].items()
    ]
    application_status_chart = [
        {
            "label": _status_label(status),
            "value": count,
        }
        for status, count in application_status_counts.items()
    ]

    recent_vouchers = vouchers.select_related("company", "category").order_by(
        "-voucher_date", "-created_at"
    )[:10]
    recent_applications = (
        applications.select_related(
            "applicant",
            "job_request__company",
            "job_request__job",
        )
        .order_by("-created_at")[:10]
    )

    return _render_report(
        request,
        "app/reports/dashboard.html",
        {
            "page_title": "لوحة التقارير",
            "financial": financial,
            "stats": {
                "companies": companies.count(),
                "active_companies": companies.filter(is_active=True).count(),
                "applicants": applicants.count(),
                "job_requests": job_requests.count(),
                "open_job_requests": job_requests.filter(
                    status=CompanyJobRequestStatus.OPEN
                ).count(),
                "applications": applications.count(),
                "accepted_applicants": application_status_counts.get(
                    ApplicationStatus.ACCEPTED,
                    0,
                ),
                "hired_applicants": application_status_counts.get(
                    ApplicationStatus.HIRED,
                    0,
                ),
            },
            "application_status_counts": application_status_counts,
            "application_status_chart": application_status_chart,
            "financial_currency_chart": financial_currency_chart,
            "recent_vouchers": recent_vouchers,
            "recent_applications": recent_applications,
        },
        report_filters,
    )


@require_GET
@login_required
def companies_report(request: HttpRequest) -> HttpResponse:
    """
    تقرير الشركات وطلبات التوظيف والنتائج المالية لكل شركة.

    الرابط:
        /reports/companies/
    """
    report_filters = _filters(request)
    created_filters = _date_range_kwargs("created_at", report_filters)

    companies = (
        Company.objects.filter(**created_filters)
        .annotate(
            job_requests_count=Count(
                "job_requests",
                filter=Q(job_requests__created_at__isnull=False),
                distinct=True,
            ),
            open_job_requests_count=Count(
                "job_requests",
                filter=Q(
                    job_requests__status=CompanyJobRequestStatus.OPEN,
                ),
                distinct=True,
            ),
            applications_count=Count(
                "job_requests__applications",
                distinct=True,
            ),
            accepted_count=Count(
                "job_requests__applications",
                filter=Q(
                    job_requests__applications__status=ApplicationStatus.ACCEPTED,
                ),
                distinct=True,
            ),
            hired_count=Count(
                "job_requests__applications",
                filter=Q(
                    job_requests__applications__status=ApplicationStatus.HIRED,
                ),
                distinct=True,
            ),
        )
        .order_by("name")
    )

    company_vouchers = _apply_voucher_filters(
        Voucher.objects.filter(company_id__isnull=False),
        report_filters,
    )
    grouped_financial = (
        company_vouchers.values("company_id", "type")
        .annotate(total=Coalesce(Sum("amount"), ZERO, output_field=MONEY_FIELD))
    )

    financial_by_company: dict[int, dict[str, Decimal]] = {}
    for row in grouped_financial:
        company_id = row["company_id"]
        bucket = financial_by_company.setdefault(
            company_id,
            {"revenue": ZERO, "expenses": ZERO, "net": ZERO},
        )
        if row["type"] == VoucherCategoryType.RECEIPT:
            bucket["revenue"] += row["total"]
        elif row["type"] == VoucherCategoryType.PAYMENT:
            bucket["expenses"] += row["total"]
        bucket["net"] = bucket["revenue"] - bucket["expenses"]

    company_rows = []
    for company in companies:
        company.financial = financial_by_company.get(
            company.pk,
            {"revenue": ZERO, "expenses": ZERO, "net": ZERO},
        )
        company_rows.append(company)

    company_chart = [
        {
            "label": company.name,
            "value": company.accepted_count,
        }
        for company in company_rows[:10]
    ]

    return _render_report(
        request,
        "app/reports/companies.html",
        {
            "page_title": "تقرير الشركات",
            "companies": company_rows,
            "companies_count": len(company_rows),
            "active_companies_count": sum(
                1 for company in company_rows if company.is_active
            ),
            "financial": _voucher_totals(company_vouchers, report_filters),
            "company_chart": company_chart,
        },
        report_filters,
    )


@require_GET
@login_required
def applicants_report(request: HttpRequest) -> HttpResponse:
    """
    تقرير شامل للمتقدمين مع عدد طلباتهم وحالاتها.

    الرابط:
        /reports/applicants/
    """
    report_filters = _filters(request)
    created_filters = _date_range_kwargs("created_at", report_filters)

    applicants = (
        Applicant.objects.filter(**created_filters)
        .annotate(
            applications_count=Count("applications", distinct=True),
            accepted_count=Count(
                "applications",
                filter=Q(
                    applications__status=ApplicationStatus.ACCEPTED,
                ),
                distinct=True,
            ),
            hired_count=Count(
                "applications",
                filter=Q(
                    applications__status=ApplicationStatus.HIRED,
                ),
                distinct=True,
            ),
            rejected_count=Count(
                "applications",
                filter=Q(
                    applications__status=ApplicationStatus.REJECTED,
                ),
                distinct=True,
            ),
            latest_application_at=Max("applications__created_at"),
        )
        .order_by("full_name")
    )

    status_summary = {
        row["status"]: row["count"]
        for row in Application.objects.filter(
            applicant__in=applicants
        ).values("status").annotate(count=Count("id"))
    }
    applicant_status_chart = [
        {
            "label": _status_label(status),
            "value": count,
        }
        for status, count in status_summary.items()
    ]

    return _render_report(
        request,
        "app/reports/applicants.html",
        {
            "page_title": "تقرير المتقدمين",
            "applicants": applicants,
            "applicants_count": applicants.count(),
            "status_summary": status_summary,
            "applicant_status_chart": applicant_status_chart,
        },
        report_filters,
    )


@require_GET
@login_required
def accepted_applicants_report(request: HttpRequest) -> HttpResponse:
    """
    تقرير المتقدمين المقبولين، مع الشركة والوظيفة والرسوم والعملة.

    يستخدم تاريخ التوظيف عند توفره، مع الرجوع إلى تاريخ إنشاء الطلب
    للسجلات التي لم يحدد لها employment_date.

    الرابط:
        /reports/applicants/accepted/
    """
    report_filters = _filters(request)
    date_filters = _date_range_kwargs("created_at", report_filters)

    accepted = (
        Application.objects.filter(
            status__in=[
                ApplicationStatus.ACCEPTED,
                ApplicationStatus.HIRED,
            ],
            **date_filters,
        )
        .select_related(
            "applicant",
            "job_request__company",
            "job_request__job",
        )
        .order_by("-employment_date", "-created_at")
    )

    if report_filters["currency"]:
        accepted = accepted.filter(
            job_request__currency=report_filters["currency"]
        )

    accepted_by_currency: dict[str, dict[str, Any]] = {}
    for application in accepted:
        currency = application.job_request.currency
        bucket = accepted_by_currency.setdefault(
            currency,
            {"count": 0, "total_fees": ZERO},
        )
        bucket["count"] += 1
        bucket["total_fees"] += (
            application.fee_per_employee_snapshot
            or application.job_request.fee_per_employee
            or ZERO
        )

    accepted_currency_chart = [
        {
            "label": _currency_label(currency),
            "value": str(values["total_fees"]),
        }
        for currency, values in accepted_by_currency.items()
    ]

    return _render_report(
        request,
        "app/reports/accepted_applicants.html",
        {
            "page_title": "تقرير المتقدمين المقبولين",
            "accepted_applicants": accepted,
            "accepted_count": accepted.count(),
            "accepted_by_currency": accepted_by_currency,
            "accepted_currency_chart": accepted_currency_chart,
        },
        report_filters,
    )


@require_GET
@login_required
def financial_report(request: HttpRequest) -> HttpResponse:
    """
    التقرير المالي: الإيرادات والمصروفات وصافي كل عملة والتصنيفات.

    السندات من النوع RECEIPT تعتبر إيرادات، والسندات من النوع PAYMENT
    تعتبر مصروفات، وفق VoucherCategoryType الموجود في models.py.

    الرابط:
        /reports/financial/
    """
    report_filters = _filters(request)
    vouchers = _apply_voucher_filters(
        Voucher.objects.select_related("company", "category", "job_request"),
        report_filters,
    )
    financial = _voucher_totals(vouchers, report_filters)

    category_breakdown = (
        vouchers.values("category_id", "category__name", "type", "currency")
        .annotate(
            total=Coalesce(Sum("amount"), ZERO, output_field=MONEY_FIELD),
            vouchers_count=Count("id"),
        )
        .order_by("currency", "type", "category__name")
    )

    monthly_breakdown = (
        vouchers.values("voucher_date__year", "voucher_date__month", "type")
        .annotate(
            total=Coalesce(Sum("amount"), ZERO, output_field=MONEY_FIELD),
            vouchers_count=Count("id"),
        )
        .order_by(
            "voucher_date__year",
            "voucher_date__month",
            "type",
        )
    )

    monthly_chart_map: dict[str, dict[str, Any]] = {}
    for row in monthly_breakdown:
        month_label = (
            f"{row['voucher_date__year']}-{row['voucher_date__month']:02d}"
        )
        month_data = monthly_chart_map.setdefault(
            month_label,
            {"label": month_label, "revenue": "0.00", "expenses": "0.00"},
        )
        if row["type"] == VoucherCategoryType.RECEIPT:
            month_data["revenue"] = str(row["total"])
        elif row["type"] == VoucherCategoryType.PAYMENT:
            month_data["expenses"] = str(row["total"])
    monthly_chart = list(monthly_chart_map.values())
    category_chart = [
        {
            "label": f"{row['category__name']} - {_currency_label(row['currency'])}",
            "type": row["type"],
            "value": str(row["total"]),
        }
        for row in category_breakdown
    ]

    return _render_report(
        request,
        "app/reports/financial.html",
        {
            "page_title": "التقرير المالي",
            "financial": financial,
            "vouchers": vouchers.order_by(
                "-voucher_date",
                "-created_at",
            ),
            "category_breakdown": category_breakdown,
            "monthly_breakdown": monthly_breakdown,
            "monthly_chart": monthly_chart,
            "category_chart": category_chart,
            "vouchers_count": vouchers.count(),
        },
        report_filters,
    )


def _csv_response(filename: str, headers: Iterable[str]) -> tuple[
    HttpResponse,
    csv.writer,
]:
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(headers)
    return response, writer


@require_GET
@login_required
def export_report_csv(request: HttpRequest) -> HttpResponse:
    """
    تصدير التقارير إلى CSV بواسطة query parameter اسمه report.

    أمثلة:
        /reports/export/csv/?report=companies
        /reports/export/csv/?report=applicants
        /reports/export/csv/?report=accepted
        /reports/export/csv/?report=financial
    """
    report_name = request.GET.get("report", "financial").lower()
    report_filters = _filters(request)

    if report_name == "companies":
        response, writer = _csv_response(
            "companies-report.csv",
            [
                "اسم الشركة",
                "الهاتف",
                "البريد الإلكتروني",
                "نشطة",
                "طلبات الشركات",
                "الطلبات المفتوحة",
                "عدد المتقدمين",
                "المقبولون",
                "تم توظيفهم",
                "الإيرادات",
                "المصروفات",
                "الصافي",
            ],
        )
        companies = (
            Company.objects.annotate(
                job_requests_count=Count(
                    "job_requests",
                    distinct=True,
                ),
                open_job_requests_count=Count(
                    "job_requests",
                    filter=Q(
                        job_requests__status=CompanyJobRequestStatus.OPEN,
                    ),
                    distinct=True,
                ),
                applications_count=Count(
                    "job_requests__applications",
                    distinct=True,
                ),
                accepted_count=Count(
                    "job_requests__applications",
                    filter=Q(
                        job_requests__applications__status=ApplicationStatus.ACCEPTED,
                    ),
                    distinct=True,
                ),
                hired_count=Count(
                    "job_requests__applications",
                    filter=Q(
                        job_requests__applications__status=ApplicationStatus.HIRED,
                    ),
                    distinct=True,
                ),
            )
            .order_by("name")
        )
        vouchers = _apply_voucher_filters(
            Voucher.objects.filter(company_id__isnull=False),
            report_filters,
        )
        grouped = vouchers.values("company_id", "type").annotate(
            total=Coalesce(Sum("amount"), ZERO, output_field=MONEY_FIELD)
        )
        money_by_company: dict[int, dict[str, Decimal]] = {}
        for row in grouped:
            money = money_by_company.setdefault(
                row["company_id"],
                {"revenue": ZERO, "expenses": ZERO},
            )
            if row["type"] == VoucherCategoryType.RECEIPT:
                money["revenue"] += row["total"]
            else:
                money["expenses"] += row["total"]

        for company in companies:
            money = money_by_company.get(
                company.pk,
                {"revenue": ZERO, "expenses": ZERO},
            )
            writer.writerow(
                [
                    company.name,
                    company.phone,
                    company.email or "",
                    "نعم" if company.is_active else "لا",
                    company.job_requests_count,
                    company.open_job_requests_count,
                    company.applications_count,
                    company.accepted_count,
                    company.hired_count,
                    money["revenue"],
                    money["expenses"],
                    money["revenue"] - money["expenses"],
                ]
            )
        return response

    if report_name == "applicants":
        response, writer = _csv_response(
            "applicants-report.csv",
            [
                "الاسم الكامل",
                "الهاتف",
                "البريد الإلكتروني",
                "تاريخ الميلاد",
                "الجنس",
                "المؤهل",
                "عدد الطلبات",
                "المقبول",
                "تم التوظيف",
                "المرفوض",
                "آخر طلب",
            ],
        )
        applicants = Applicant.objects.annotate(
            applications_count=Count("applications", distinct=True),
            accepted_count=Count(
                "applications",
                filter=Q(
                    applications__status=ApplicationStatus.ACCEPTED,
                ),
                distinct=True,
            ),
            hired_count=Count(
                "applications",
                filter=Q(
                    applications__status=ApplicationStatus.HIRED,
                ),
                distinct=True,
            ),
            rejected_count=Count(
                "applications",
                filter=Q(
                    applications__status=ApplicationStatus.REJECTED,
                ),
                distinct=True,
            ),
            latest_application_at=Max("applications__created_at"),
        ).order_by("full_name")

        for applicant in applicants:
            writer.writerow(
                [
                    applicant.full_name,
                    applicant.phone,
                    applicant.email or "",
                    applicant.birth_date,
                    applicant.get_gender_display(),
                    applicant.get_qualification_display(),
                    applicant.applications_count,
                    applicant.accepted_count,
                    applicant.hired_count,
                    applicant.rejected_count,
                    applicant.latest_application_at or "",
                ]
            )
        return response

    if report_name == "accepted":
        response, writer = _csv_response(
            "accepted-applicants-report.csv",
            [
                "المتقدم",
                "الهاتف",
                "الشركة",
                "الوظيفة",
                "الحالة",
                "تاريخ التوظيف",
                "الرسوم",
                "العملة",
            ],
        )
        accepted = (
            Application.objects.filter(
                status__in=[
                    ApplicationStatus.ACCEPTED,
                    ApplicationStatus.HIRED,
                ]
            )
            .select_related(
                "applicant",
                "job_request__company",
                "job_request__job",
            )
            .order_by("-employment_date", "-created_at")
        )
        if report_filters["currency"]:
            accepted = accepted.filter(
                job_request__currency=report_filters["currency"]
            )
        for application in accepted:
            writer.writerow(
                [
                    application.applicant.full_name,
                    application.applicant.phone,
                    application.job_request.company.name,
                    application.job_request.job.name,
                    application.get_status_display(),
                    application.employment_date or "",
                    application.fee_per_employee_snapshot
                    or application.job_request.fee_per_employee,
                    application.job_request.currency,
                ]
            )
        return response

    if report_name == "financial":
        response, writer = _csv_response(
            "financial-report.csv",
            [
                "رقم السند",
                "التاريخ",
                "النوع",
                "التصنيف",
                "الشركة",
                "العملة",
                "المبلغ",
                "البيان",
            ],
        )
        vouchers = _apply_voucher_filters(
            Voucher.objects.select_related("company", "category"),
            report_filters,
        ).order_by("-voucher_date", "-created_at")
        for voucher in vouchers:
            writer.writerow(
                [
                    voucher.voucher_number or "",
                    voucher.voucher_date,
                    voucher.get_type_display(),
                    voucher.category.name,
                    voucher.company_name,
                    voucher.currency,
                    voucher.amount,
                    voucher.description,
                ]
            )
        return response

    response = HttpResponse(
        "نوع التقرير غير صحيح. استخدم companies أو applicants أو accepted أو financial.",
        status=400,
        content_type="text/plain; charset=utf-8",
    )
    return response