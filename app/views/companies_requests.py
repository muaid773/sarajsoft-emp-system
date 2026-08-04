from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import (
    CompaniesRequestsFilterForm,
    CompaniesRequestsForm,
)
from ..models import CompanyJobRequest


@login_required
def companies_requests(request):
    filter_form = CompaniesRequestsFilterForm(request.GET or None)

    companies_requests_qs = (
        CompanyJobRequest.objects
        .select_related("company", "job")
        .all()
    )

    if filter_form.is_valid():
        q = filter_form.cleaned_data.get("q")
        job = filter_form.cleaned_data.get("job")
        status = filter_form.cleaned_data.get("status")
        min_fee = filter_form.cleaned_data.get("min_fee")
        max_fee = filter_form.cleaned_data.get("max_fee")
        ordering = (
            filter_form.cleaned_data.get("ordering")
            or "-created_at"
        )

        if q:
            companies_requests_qs = companies_requests_qs.filter(
                Q(company__name__icontains=q)
                | Q(job__name__icontains=q)
                | Q(notes__icontains=q)
            )

        if job:
            companies_requests_qs = companies_requests_qs.filter(
                job=job
            )

        if status:
            companies_requests_qs = companies_requests_qs.filter(
                status=status
            )

        if min_fee is not None:
            companies_requests_qs = companies_requests_qs.filter(
                fee_per_employee__gte=min_fee
            )

        if max_fee is not None:
            companies_requests_qs = companies_requests_qs.filter(
                fee_per_employee__lte=max_fee
            )

        companies_requests_qs = companies_requests_qs.order_by(
            ordering,
            "-created_at",
        )

    else:
        companies_requests_qs = companies_requests_qs.order_by(
            "-created_at"
        )

    paginator = Paginator(
        companies_requests_qs,
        25,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "filter_form": filter_form,
        "companies_requests_qs": page_obj.object_list,
        "page_obj": page_obj,
        "query_string": query_params.urlencode(),
    }

    return render(
        request,
        "app/companies_requests/companies_requests.html",
        context,
    )


@login_required
def companies_requests_create(request):
    if request.method == "POST":
        form = CompaniesRequestsForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "تمت إضافة طلب الشركة بنجاح.",
            )

            return redirect(
                "app:companies_requests"
            )

    else:
        form = CompaniesRequestsForm()

    context = {
        "form": form,
        "title": "إضافة طلب شركة",
        "button_text": "حفظ طلب الشركة",
    }

    return render(
        request,
        "app/companies_requests/companies_requests_form.html",
        context,
    )


@login_required
def companies_requests_update(request, pk):
    company_request = get_object_or_404(
        CompanyJobRequest,
        pk=pk,
    )

    if request.method == "POST":
        form = CompaniesRequestsForm(
            request.POST,
            instance=company_request,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "تم تعديل البيانات بنجاح.",
            )

            return redirect(
                "app:companies_requests"
            )

    else:
        form = CompaniesRequestsForm(
            instance=company_request
        )

    context = {
        "form": form,
        "title": "تعديل طلب الشركة",
        "button_text": "حفظ التعديلات",
    }

    return render(
        request,
        "app/companies_requests/companies_requests_form.html",
        context,
    )