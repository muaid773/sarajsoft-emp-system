# ──────────────────────────────────────────────
# Views: FollowUp
# ──────────────────────────────────────────────
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ..forms import FollowUpFilterForm, FollowUpForm
from ..models import FollowUp, FollowUpStatus


# ──────────────────────────────────────────────
# 1) لوحة المتابعات: نظرة عامة + متابعات اليوم
# ──────────────────────────────────────────────
@permission_required("app.view_followup", raise_exception=True)
def followups(request):
    """
    الصفحة الرئيسية لقسم المتابعات.
    تعرض: عدد متابعات اليوم، عدد المتابعات المعلّقة، عدد المتابعات المتأخرة،
    وقائمة مختصرة بمتابعات اليوم نفسه.
    """
    today = timezone.localdate()

    today_followups_qs = (
        FollowUp.objects.filter(follow_up_date=today)
        .select_related("company", "applicant")
        .order_by("status", "-created_at")
    )

    # حد أقصى صريح للقائمة حتى لا تُحمّل مئات السجلات دفعة واحدة
    today_followups = today_followups_qs[:100]

    pending_count = FollowUp.objects.filter(status=FollowUpStatus.PENDING).count()

    overdue_count = FollowUp.objects.filter(
        follow_up_date__lt=today,
        status=FollowUpStatus.PENDING,
    ).count()

    context = {
        "today": today,
        "today_followups": today_followups,
        "today_count": today_followups_qs.count(),
        "pending_count": pending_count,
        "overdue_count": overdue_count,
    }
    return render(request, "app/followups/followups.html", context)


# ──────────────────────────────────────────────
# 2) قائمة المتابعات: جدول كامل + تصفية + بحث
# ──────────────────────────────────────────────
@permission_required("app.view_followup", raise_exception=True)
def followup_list(request):
    """عرض جميع المتابعات في جدول، مع دعم التصفية بالحالة والتاريخ والبحث."""
    today = timezone.localdate()
    filter_form = FollowUpFilterForm(request.GET or None)

    followups_qs = FollowUp.objects.select_related("company", "applicant").all()

    if filter_form.is_valid():
        status = filter_form.cleaned_data.get("status")
        date_filter = filter_form.cleaned_data.get("date_filter")
        search = filter_form.cleaned_data.get("search")

        if status:
            followups_qs = followups_qs.filter(status=status)

        if date_filter == "today":
            followups_qs = followups_qs.filter(follow_up_date=today)
        elif date_filter == "overdue":
            followups_qs = followups_qs.filter(
                follow_up_date__lt=today, status=FollowUpStatus.PENDING
            )
        elif date_filter == "upcoming":
            followups_qs = followups_qs.filter(follow_up_date__gt=today)
        elif date_filter == "week":
            week_end = today + timezone.timedelta(days=7)
            followups_qs = followups_qs.filter(follow_up_date__range=[today, week_end])

        if search:
            # ملاحظة: عدّل أسماء الحقول (name / full_name) لتطابق موديلات
            # Company و Applicant لديك إن اختلفت.
            followups_qs = followups_qs.filter(
                Q(note__icontains=search)
                | Q(company__name__icontains=search)
                | Q(applicant__full_name__icontains=search)
            )

    followups_qs = followups_qs.order_by("-follow_up_date", "-created_at")

    paginator = Paginator(followups_qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    # نحافظ على باقي الفلاتر عند التنقل بين صفحات الترقيم
    querydict = request.GET.copy()
    querydict.pop("page", None)

    context = {
        "filter_form": filter_form,
        "page_obj": page_obj,
        "followups": page_obj.object_list,
        "today": today,
        "querystring": querydict.urlencode(),
    }
    return render(request, "app/followups/follow_up_list.html", context)


# ──────────────────────────────────────────────
# 3) إضافة متابعة جديدة
# ──────────────────────────────────────────────
@permission_required("app.add_followup", raise_exception=True)
def followup_create(request):
    if request.method == "POST":
        form = FollowUpForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "تمت إضافة المتابعة بنجاح.")
            return redirect("app:followup_list")
    else:
        form = FollowUpForm()

    context = {"form": form, "is_edit": False}
    return render(request, "app/followups/follow_up_form.html", context)


# ──────────────────────────────────────────────
# 4) تعديل متابعة موجودة
# ──────────────────────────────────────────────
@permission_required("app.change_followup", raise_exception=True)
def followup_update(request, pk):
    followup = get_object_or_404(FollowUp, pk=pk)

    if request.method == "POST":
        form = FollowUpForm(request.POST, instance=followup)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث المتابعة بنجاح.")
            return redirect("app:followup_list")
    else:
        form = FollowUpForm(instance=followup)

    context = {"form": form, "is_edit": True, "followup": followup}
    # تم تصحيح مسار القالب ليطابق القالب الفعلي (كان سابقًا "followups/form.html" وهو غير موجود)
    return render(request, "app/followups/follow_up_form.html", context)


# ──────────────────────────────────────────────
# 5) حذف متابعة
# ──────────────────────────────────────────────
@permission_required("app.delete_followup", raise_exception=True)
@require_POST
def followup_delete(request, pk):
    """
    يحذف المتابعة. مسموح فقط بطلب POST (@require_POST يرفض أي طلب
    آخر تلقائيًا برمز 405 بدل تجاهل الحذف بصمت).
    زر الحذف بالواجهة عبارة عن <form method="post"> مع تأكيد JS.
    """
    followup = get_object_or_404(FollowUp, pk=pk)
    followup.delete()
    messages.success(request, "تم حذف المتابعة بنجاح.")
    return redirect("app:followup_list")


# ──────────────────────────────────────────────
# 6) تبديل حالة المتابعة: مكتملة ⇄ معلّقة
# ──────────────────────────────────────────────
@permission_required("app.change_followup", raise_exception=True)
@require_POST
def followup_toggle_status(request, pk):
    """
    زر سريع لتعليم المتابعة كمكتملة (COMPLETED)، وإلغاء ذلك بضغطة أخرى
    (تعيدها إلى PENDING). هاتان هما الحالتان الوحيدتان في FollowUpStatus.
    يعيد المستخدم لنفس الصفحة/الفلتر الذي جاء منه عبر حقل "next" الآمن.
    """
    followup = get_object_or_404(FollowUp, pk=pk)

    if followup.status == FollowUpStatus.COMPLETED:
        followup.status = FollowUpStatus.PENDING
        messages.success(request, "تم إعادة المتابعة إلى قيد الانتظار.")
    else:
        followup.status = FollowUpStatus.COMPLETED
        messages.success(request, "تم تعليم المتابعة كمكتملة.")

    followup.save(update_fields=["status"])

    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect("app:followup_list")