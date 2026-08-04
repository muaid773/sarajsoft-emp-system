from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from django_select2.views import AutoResponseView

from ..forms import (
    VoucherForm,
    VoucherCategoryForm,
    VoucherFilterForm,
    VoucherDependencyForm,
)

from ..models import (
    CompanyJobRequest,
    Company,
    Voucher,
    VoucherCategory,
)


# ──────────────────────────────────────────────
# Voucher
# ──────────────────────────────────────────────

class VoucherListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ListView,
):
    model = Voucher
    template_name = "app/vouchers/list.html"
    context_object_name = "vouchers"
    paginate_by = 20

    permission_required = "app.view_voucher"

    def get_queryset(self):
        queryset = (
            Voucher.objects
            .select_related(
                "company",
                "job_request",
                "category",
            )
            .order_by(
                "-voucher_date",
                "-created_at",
            )
        )

        form = VoucherFilterForm(
            self.request.GET or None
        )

        if not form.is_valid():
            return queryset

        data = form.cleaned_data

        voucher_type = data.get("type")
        category = data.get("category")
        company = data.get("company")
        date_from = data.get("date_from")
        date_to = data.get("date_to")
        search = data.get("search")

        if voucher_type:
            queryset = queryset.filter(
                type=voucher_type
            )

        if category:
            queryset = queryset.filter(
                category=category
            )

        if company:
            queryset = queryset.filter(
                company=company
            )

        if date_from:
            queryset = queryset.filter(
                voucher_date__gte=date_from
            )

        if date_to:
            queryset = queryset.filter(
                voucher_date__lte=date_to
            )

        if search:
            queryset = queryset.filter(
                Q(voucher_number__icontains=search)
                | Q(company_name__icontains=search)
                | Q(description__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["filter_form"] = VoucherFilterForm(
            self.request.GET or None
        )

        return context


class VoucherDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DetailView,
):
    model = Voucher
    template_name = "app/vouchers/detail.html"
    context_object_name = "voucher"

    permission_required = "app.view_voucher"

    def get_queryset(self):
        return (
            Voucher.objects
            .select_related(
                "company",
                "job_request",
                "category",
            )
        )


class VoucherDependencyMixin:
    """
    يعيد بناء نموذج السند اعتمادًا على قيم التحكم المرسلة عبر GET.

    نموذج GET لا يحفظ أي سجل. عند اختيار الشركة ونوع السند ونوع
    المصروف، يعاد رسم الصفحة وتظهر القوائم التابعة المناسبة.
    """

    dependency_form_class = VoucherDependencyForm

    def get_dependency_form(self):
        if hasattr(self, "_dependency_form"):
            return self._dependency_form

        if self.request.method == "GET" and self.request.GET:
            self._dependency_form = self.dependency_form_class(
                self.request.GET
            )
        elif self.request.method == "POST":
            self._dependency_form = self.dependency_form_class(
                self.request.POST
            )
        else:
            initial = {}
            if getattr(self, "object", None) is not None:
                initial = {
                    "company": self.object.company_id,
                    "type": self.object.type,
                    "expense_scope": (
                        "company"
                        if self.object.company_id
                        else "general"
                    ),
                }
            self._dependency_form = self.dependency_form_class(
                initial=initial
            )

        return self._dependency_form

    def get_dependency_values(self):
        dependency_form = self.get_dependency_form()

        if dependency_form.is_bound:
            if dependency_form.is_valid():
                company = dependency_form.cleaned_data.get("company")
                return {
                    "company_id": company.pk if company else None,
                    "voucher_type": (
                        dependency_form.cleaned_data.get("type")
                    ),
                    "expense_scope": (
                        dependency_form.cleaned_data.get(
                            "expense_scope"
                        )
                    ),
                }

            # عند وجود خطأ في نموذج GET، نحافظ على القيم الصحيحة
            # التي أدخلها المستخدم حتى يستطيع تصحيح النموذج.
            return {
                "company_id": dependency_form.data.get("company") or None,
                "voucher_type": dependency_form.data.get("type") or None,
                "expense_scope": (
                    dependency_form.data.get("expense_scope")
                    or None
                ),
            }

        initial = dependency_form.initial
        company = initial.get("company")
        return {
            "company_id": getattr(company, "pk", company) or None,
            "voucher_type": initial.get("type") or None,
            "expense_scope": initial.get("expense_scope") or None,
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        # في POST يستقبل VoucherForm الحقول الكاملة ويحفظ السند.
        if self.request.method == "POST":
            return kwargs

        values = self.get_dependency_values()
        kwargs.update(
            dependency_company_id=values["company_id"],
            dependency_type=values["voucher_type"],
            dependency_expense_scope=values["expense_scope"],
            dependency_values_supplied=True,
        )
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dependency_form = self.get_dependency_form()
        values = self.get_dependency_values()

        context["dependency_form"] = dependency_form
        context["dependency_ready"] = (
            self.request.method == "POST"
            or (
                bool(values["voucher_type"])
                and (
                    dependency_form.is_valid()
                    or not dependency_form.is_bound
                )
            )
        )
        return context


class VoucherCreateView(
    VoucherDependencyMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = Voucher
    form_class = VoucherForm
    template_name = "app/vouchers/form.html"

    permission_required = "app.add_voucher"

    success_url = reverse_lazy(
        "app:voucher_list"
    )

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            "تم إنشاء السند بنجاح.",
        )

        return response


class VoucherUpdateView(
    VoucherDependencyMixin,
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UpdateView,
):
    model = Voucher
    form_class = VoucherForm
    template_name = "app/vouchers/form.html"

    permission_required = "app.change_voucher"

    success_url = reverse_lazy(
        "app:voucher_list"
    )

    def get_queryset(self):
        return (
            Voucher.objects
            .select_related(
                "company",
                "job_request",
                "category",
            )
        )

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            "تم تعديل السند بنجاح.",
        )

        return response

class VoucherDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DeleteView,
):
    model = Voucher
    template_name = "app/vouchers/confirm_delete.html"

    permission_required = "app.delete_voucher"

    success_url = reverse_lazy(
        "app:voucher_list"
    )

    DELETE_WINDOW = timedelta(minutes=30)

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        if timezone.now() >= (
            self.object.created_at
            + self.DELETE_WINDOW
        ):
            raise PermissionDenied(
                "لا يمكن حذف السند بعد مرور نصف ساعة من إنشائه. "
                "أصبح السند وثيقة مالية تاريخية مثبتة."
            )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def delete(
        self,
        request,
        *args,
        **kwargs,
    ):
        self.object = self.get_object()

        voucher_number = (
            self.object.voucher_number
        )

        response = super().delete(
            request,
            *args,
            **kwargs,
        )

        messages.success(
            request,
            f"تم حذف السند {voucher_number} بنجاح.",
        )

        return response


# ──────────────────────────────────────────────
# VoucherCategory
# ──────────────────────────────────────────────

class VoucherCategoryListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    ListView,
):
    model = VoucherCategory
    template_name = "app/vouchers/category_list.html"
    context_object_name = "categories"

    permission_required = (
        "app.view_vouchercategory"
    )

    paginate_by = 20

    def get_queryset(self):
        return (
            VoucherCategory.objects
            .order_by(
                "type",
                "name",
            )
        )


class VoucherCategoryCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    CreateView,
):
    model = VoucherCategory
    form_class = VoucherCategoryForm
    template_name = "app/vouchers/category_form.html"

    permission_required = (
        "app.add_vouchercategory"
    )

    success_url = reverse_lazy(
        "app:vouchercategory_list"
    )

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            "تم إنشاء التصنيف بنجاح.",
        )

        return response


class VoucherCategoryUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UpdateView,
):
    model = VoucherCategory
    form_class = VoucherCategoryForm
    template_name = "app/vouchers/category_form.html"

    permission_required = (
        "app.change_vouchercategory"
    )

    success_url = reverse_lazy(
        "app:vouchercategory_list"
    )

    def form_valid(self, form):
        response = super().form_valid(form)

        messages.success(
            self.request,
            "تم تعديل التصنيف بنجاح.",
        )

        return response


class VoucherCategoryDeleteView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    DeleteView,
):
    model = VoucherCategory
    template_name = "app/vouchers/category_confirm_delete.html"

    permission_required = (
        "app.delete_vouchercategory"
    )

    success_url = reverse_lazy(
        "app:vouchercategory_list"
    )

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        name = self.object.name

        response = super().delete(request, *args, **kwargs)

        messages.success(
            request,
            f"تم حذف التصنيف {name} بنجاح.",
        )

        return response


# ──────────────────────────────────────────────
# Select2 AJAX Endpoints
# ──────────────────────────────────────────────

class CompanySelect2View(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AutoResponseView,
):
    model = Company
    permission_required = "app.view_voucher"
    search_fields = [
        "name__icontains",
        "phone__icontains",
        "email__icontains",
    ]


class JobRequestSelect2View(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AutoResponseView,
):
    model = CompanyJobRequest
    permission_required = "app.view_voucher"
    search_fields = [
        "company__name__icontains",
        "job__name__icontains",
    ]


class VoucherCategorySelect2View(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    AutoResponseView,
):
    model = VoucherCategory
    permission_required = "app.view_vouchercategory"
    search_fields = [
        "name__icontains",
    ]


