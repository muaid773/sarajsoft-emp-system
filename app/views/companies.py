from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages

from ..models import Company
from ..forms import CompanyForm

@login_required()
def companies(request):
    q = request.GET.get("q", "").strip()

    companies_qs = Company.objects

    if q:
        companies_qs = companies_qs.filter(
            Q(name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q)
        )
    companies_qs = companies_qs.all()[:100]

    context = {
        "companies": companies_qs,
        "q": q,
    }

    return render(request, "app/companies/companies.html", context=context)
@login_required()
def company_create(request):

    if request.method == "POST":

        form = CompanyForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "تمت إضافة الشركة بنجاح."
            )

            return redirect(
                "app:companies"
            )

    else:

        form = CompanyForm()


    context = {
        "form": form,
        "title": "إضافة شركة",
        "button_text": "حفظ الشركة",
    }


    return render(
        request,
        "app/companies/company_form.html",
        context
    )


@login_required()
def company_update(request, pk):

    company = get_object_or_404(
        Company,
        pk=pk
    )


    if request.method == "POST":

        form = CompanyForm(
            request.POST,
            instance=company
        )


        if form.is_valid():

            form.save()


            messages.success(
                request,
                "تم تحديث بيانات الشركة."
            )


            return redirect(
                "app:companies"
            )


    else:

        form = CompanyForm(
            instance=company
        )


    context = {
        "form": form,
        "title": "تعديل الشركة",
        "button_text": "حفظ التعديلات",
    }


    return render(
        request,
        "app/companies/company_form.html",
        context
    )