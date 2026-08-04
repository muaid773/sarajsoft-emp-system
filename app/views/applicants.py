from django.contrib.auth.decorators import  login_required
from django.db.models import Q
from django.contrib import messages

from django.shortcuts import render, redirect, get_object_or_404
from ..models import Applicant, Application
from ..forms import ApplicantForm
from django.db.models import Prefetch

@login_required()
def applicants(request):
    q = request.GET.get("q", "")
    applicants_qs = Applicant.objects.all()
    if q:
        applicants_qs = applicants_qs.filter(
            Q(full_name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q) |
            Q(qualification__icontains=q) |
            Q(experience__icontains=q) |
            Q(notes__icontains=q) 
        )
    applicants_qs = applicants_qs.order_by("-created_at")[:100]
    context = {
        "applicants":applicants_qs,
        "q":q
        }
    return render(request, 'app/applicants/applicants.html', context=context)

@login_required
def applicant_details(request, pk):
    applicant = get_object_or_404(
        Applicant.objects.prefetch_related(
            Prefetch(
                "applications",
                queryset=Application.objects.select_related(
                    "job_request",
                    "job_request__company",
                    "job_request__job",
                ).order_by("-created_at"),
            )
        ),
        pk=pk,
    )

    return render(
        request,
        "app/applicants/applicants_details.html",
        {
            "applicant": applicant,
        },
    )
@login_required()
def applicants_create(request):
    if request.method == "POST":
        form = ApplicantForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "تم اظافة المتقدم بنجاح")
            return redirect("app:applicants")
    else:
        form = ApplicantForm()
    context = {
        "form":form,
        "title": "اظافة متقدم",
        "button_text":"حفظ المتقدم"
    }
    return render(request, 'app/applicants/applicants_form.html', context=context)

@login_required()
def applicants_update(request, pk):
    applicant = get_object_or_404(
        Applicant,
        pk=pk
    )


    if request.method == "POST":

        form = ApplicantForm(
            request.POST, request.FILES,
            instance=applicant
        )


        if form.is_valid():

            form.save()


            messages.success(
                request,
                "تم تحديث بيانات المتقدم."
            )


            return redirect(
                "app:applicants"
            )


    else:

        form = ApplicantForm(
            instance=applicant
        )


    context = {
        "form": form,
        "title": "تعديل المتقدم",
        "button_text": "حفظ التعديلات",
    }


    return render(
        request,
        'app/applicants/applicants_form.html',
        context
    )