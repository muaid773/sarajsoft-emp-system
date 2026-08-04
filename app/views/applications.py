from django.contrib.auth.decorators import  login_required
from django.db.models import Q
from django.contrib import messages

from django.shortcuts import render, redirect, get_object_or_404
from ..models import Application
from ..forms import ApplicationForm

@login_required()
def applications(request):
    q = request.GET.get("q", "")
    applications_qs = Application.objects
    if q:
        applications_qs = applications_qs.filter( 
            Q(full_name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q) |
            Q(gender__icontains=q)
        )
    applications_qs = applications_qs.all()[:100]
    context = {
            "applications":applications_qs,
            "q":q
            }

    return render(request, 'app/applications/applications.html', context=context)

@login_required()
def applications_create(request):
    if request.method == "POST":
        form = ApplicationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "تمت إضافة ترشيح المتقدم.")
            return redirect("app:applications")

    else:
        form = ApplicationForm()
    context = {
        "form":form,
        "title": "اظافة الترشيح",
        "button_text": "حفظ الترشيح",
    }
    return render(request, 'app/applications/applications_form.html', context=context)


@login_required()
def applications_update(request, pk):
    applications = get_object_or_404(Application, pk=pk)
    if request.method == "POST":
        form = ApplicationForm(request.POST, instance=applications)
        if form.is_valid():
            form.save()
            messages.success(request, "تمت تعديل ترشيح المتقدم.")
            return redirect("app:applications")

    else:
        form = ApplicationForm(instance=applications)
    context = {
        "form":form,
        "title": "تعديل الترشيح",
        "button_text": "حفظ الترشيح",
    }
    return render(request, 'app/applications/applications_form.html', context=context)
