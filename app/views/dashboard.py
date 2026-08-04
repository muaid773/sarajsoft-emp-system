from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone

from ..models import (
    Applicant,
    Application,
    ApplicationStatus,
    Company,
    CompanyJobRequest,
    CompanyJobRequestStatus,
    CurrencyChoices,
    FollowUp,
    FollowUpStatus,
    Voucher,
    VoucherCategoryType,
)


ZERO = Decimal("0.00")
MONEY_FIELD = DecimalField(max_digits=18, decimal_places=2)


def _month_boundaries():
    """إرجاع بداية الشهر الحالي وبداية الشهر التالي."""
    today = timezone.localdate()
    month_start = today.replace(day=1)

    if month_start.month == 12:
        next_month = month_start.replace(
            year=month_start.year + 1,
            month=1,
        )
    else:
        next_month = month_start.replace(month=month_start.month + 1)

    return today, month_start, next_month


def _display_map(choices):
    return dict(choices)


@login_required
def dashboard_view(request):
    """
    لوحة النظرة العامة للنظام.

    تعرض أهم مؤشرات التشغيل في شاشة واحدة:
    - الشركات وطلبات الشركات.
    - المتقدمون وطلبات التوظيف.
    - المتابعات المستحقة.
    - الإيرادات والمصروفات للشهر الحالي.
    - آخر النشاطات والاختصارات السريعة.
    """
    today, month_start, next_month = _month_boundaries()

    companies = Company.objects.all()
    applicants = Applicant.objects.all()
    job_requests = CompanyJobRequest.objects.all()
    applications = Application.objects.all()
    vouchers = Voucher.objects.all()
    followups = FollowUp.objects.all()

    current_month_created = Q(
        created_at__date__gte=month_start,
        created_at__date__lt=next_month,
    )

    application_status_counts = {
        row["status"]: row["count"]
        for row in applications.values("status").annotate(count=Count("id"))
    }

    monthly_applications = applications.filter(current_month_created).count()
    monthly_applicants = applicants.filter(current_month_created).count()
    monthly_companies = companies.filter(current_month_created).count()

    pending_followups = followups.filter(
        status=FollowUpStatus.PENDING,
        follow_up_date__lte=today,
    ).count()

    monthly_vouchers = vouchers.filter(
        voucher_date__gte=month_start,
        voucher_date__lt=next_month,
    )

    monthly_financial_rows = (
        monthly_vouchers.values("currency", "type")
        .annotate(
            total=Coalesce(
                Sum("amount"),
                ZERO,
                output_field=MONEY_FIELD,
            )
        )
        .order_by("currency", "type")
    )

    financial_by_currency = {}
    for row in monthly_financial_rows:
        currency = row["currency"]
        bucket = financial_by_currency.setdefault(
            currency,
            {
                "revenue": ZERO,
                "expenses": ZERO,
                "net": ZERO,
            },
        )

        if row["type"] == VoucherCategoryType.RECEIPT:
            bucket["revenue"] += row["total"]
        elif row["type"] == VoucherCategoryType.PAYMENT:
            bucket["expenses"] += row["total"]

        bucket["net"] = bucket["revenue"] - bucket["expenses"]

    currency_labels = _display_map(CurrencyChoices.choices)
    finance_rows = [
        {
            "currency": currency,
            "label": currency_labels.get(currency, currency),
            "revenue": values["revenue"],
            "expenses": values["expenses"],
            "net": values["net"],
        }
        for currency, values in financial_by_currency.items()
    ]

    status_labels = _display_map(ApplicationStatus.choices)
    application_chart = {
        "labels": [
            status_labels.get(status, status)
            for status, _label in ApplicationStatus.choices
        ],
        "values": [
            application_status_counts.get(status, 0)
            for status, _label in ApplicationStatus.choices
        ],
    }

    finance_chart = {
        "labels": [row["label"] for row in finance_rows],
        "revenue": [str(row["revenue"]) for row in finance_rows],
        "expenses": [str(row["expenses"]) for row in finance_rows],
    }

    recent_applications = (
        applications.select_related(
            "applicant",
            "job_request__company",
            "job_request__job",
        )
        .order_by("-created_at")[:7]
    )

    recent_vouchers = (
        vouchers.select_related("company", "category")
        .order_by("-voucher_date", "-created_at")[:7]
    )

    upcoming_followups = (
        followups.select_related("company", "applicant")
        .filter(
            status=FollowUpStatus.PENDING,
            follow_up_date__gte=today,
        )
        .order_by("follow_up_date", "-created_at")[:6]
    )

    context = {
        "today": today,
        "month_start": month_start,
        "stats": {
            "companies": companies.count(),
            "active_companies": companies.filter(is_active=True).count(),
            "monthly_companies": monthly_companies,
            "applicants": applicants.count(),
            "monthly_applicants": monthly_applicants,
            "job_requests": job_requests.count(),
            "open_job_requests": job_requests.filter(
                status=CompanyJobRequestStatus.OPEN,
            ).count(),
            "applications": applications.count(),
            "monthly_applications": monthly_applications,
            "new_applications": application_status_counts.get(
                ApplicationStatus.NEW,
                0,
            ),
            "under_review_applications": application_status_counts.get(
                ApplicationStatus.UNDER_REVIEW,
                0,
            ),
            "accepted_applicants": application_status_counts.get(
                ApplicationStatus.ACCEPTED,
                0,
            ),
            "hired_applicants": application_status_counts.get(
                ApplicationStatus.HIRED,
                0,
            ),
            "pending_followups": pending_followups,
            "monthly_vouchers": monthly_vouchers.count(),
        },
        "finance_rows": finance_rows,
        "application_chart": application_chart,
        "finance_chart": finance_chart,
        "recent_applications": recent_applications,
        "recent_vouchers": recent_vouchers,
        "upcoming_followups": upcoming_followups,
        "voucher_type_labels": _display_map(VoucherCategoryType.choices),
    }

    return render(request, "app/dashboard.html", context)

