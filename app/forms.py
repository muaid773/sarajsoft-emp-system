from django import forms
from django_select2 import forms as s2forms

from .models import (
    Applicant,
    Application,
    ApplicationStatus,
    Company,
    CompanyJobRequest,
    CompanyJobRequestStatus,
    FollowUp,
    FollowUpStatus,
    Job,
    Voucher,
    VoucherCategory,
    VoucherCategoryType,
)


# ──────────────────────────────────────────────
# Select2 Widgets
# ──────────────────────────────────────────────

class CompanySelect2Widget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
        "phone__icontains",
        "email__icontains",
        "address__icontains",
        "notes__icontains",
    ]


class JobSelect2Widget(s2forms.ModelSelect2Widget):
    search_fields = ["name__icontains"]


class JobRequestSelect2Widget(s2forms.ModelSelect2Widget):
    model = CompanyJobRequest

    # ملاحظة: CompanyJobRequest ليس فيه حقل job_title، البحث الصحيح
    # يكون عبر اسم الشركة أو اسم الوظيفة المرتبطين.
    search_fields = [
        "company__name__icontains",
        "job__name__icontains",
    ]

    def label_from_instance(self, obj):
        return str(obj)


class ApplicantSelect2WidgetJobRequest(s2forms.ModelSelect2Widget):
    """بحث في طلبات الشركات باسم الشركة أو الوظيفة."""
    search_fields = [
        "company__name__icontains",
        "job__name__icontains",
    ]


class ApplicantSelect2MultipleWidgetApplicant(s2forms.ModelSelect2Widget):
    """بحث في المتقدمين بالاسم أو الهاتف أو الإيميل."""
    search_fields = [
        "full_name__icontains",
        "phone__icontains",
        "email__icontains",
    ]


class ApplicantSelect2Widget(s2forms.ModelSelect2Widget):
    """بحث في المتقدمين (للمتابعات)."""
    search_fields = [
        "full_name__icontains",
        "phone__icontains",
    ]


class VoucherCategorySelect2Widget(s2forms.ModelSelect2Widget):
    model = VoucherCategory

    search_fields = [
        "name__icontains",
    ]

    def label_from_instance(self, obj):
        return f"{obj.name} - {obj.get_type_display()}"

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        queryset = super().filter_queryset(
            request,
            term,
            queryset=queryset,
            **dependent_fields,
        )

        voucher_type = dependent_fields.get("type")

        if voucher_type:
            queryset = queryset.filter(
                type=voucher_type
            )

        return queryset


# ──────────────────────────────────────────────
# Company
# ──────────────────────────────────────────────

class CompanyForm(forms.ModelForm):

    class Meta:
        model  = Company
        fields = ["name", "phone", "email", "address", "notes", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "اسم الشركة",
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "رقم الهاتف",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-input",
                "placeholder": "البريد الإلكتروني (اختياري)",
            }),
            "address": forms.Textarea(attrs={
                "class": "form-input",
                "rows": 3,
                "placeholder": "عنوان الشركة",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-input",
                "rows": 3,
                "placeholder": "ملاحظات إضافية",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "checkbox-input",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        phone = cleaned_data.get("phone")
        email = cleaned_data.get("email")

        # التحقق من تكرار رقم الهاتف
        if phone:
            if Company.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
                self.add_error("phone", "رقم الهاتف مسجل مسبقاً لشركة أخرى.")

        # التحقق من تكرار الإيميل فقط إذا أُدخل
        if email:
            if Company.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                self.add_error("email", "البريد الإلكتروني مسجل مسبقاً لشركة أخرى.")

        return cleaned_data


# ──────────────────────────────────────────────
# Job
# ──────────────────────────────────────────────

class JobForm(forms.ModelForm):

    class Meta:
        model  = Job
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "اسم الوظيفة",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-input",
                "rows": 3,
                "placeholder": "وصف الوظيفة (اختياري)",
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if name and Job.objects.filter(name=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("اسم الوظيفة مسجل مسبقاً.")
        return name


# ──────────────────────────────────────────────
# CompanyJobRequest
# ──────────────────────────────────────────────

class CompaniesRequestsForm(forms.ModelForm):

    class Meta:
        model  = CompanyJobRequest
        fields = ["company", "job", "required_count", "fee_per_employee", "currency", "status", "notes"]
        widgets = {
            "company": CompanySelect2Widget,
            "job": JobSelect2Widget,
            "required_count": forms.NumberInput(attrs={
                "class": "form-input",
                "min": 1,
            }),
            "fee_per_employee": forms.NumberInput(attrs={
                "class": "form-input",
                "min": 0,
                "step": "0.01",
            }),
            "currency": forms.Select(attrs={
                "class": "form-input",
            }),
            "status": forms.Select(attrs={
                "class": "form-input",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-input",
                "rows": 3,
                "placeholder": "الملاحظات",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        company = cleaned_data.get("company")
        job     = cleaned_data.get("job")

        if company and job:
            # يمنع فقط وجود طلب مفتوح آخر لنفس الشركة ونفس الوظيفة
            # (مسموح بطلب جديد بعد إكمال أو إلغاء الطلب السابق)
            open_exists = (
                CompanyJobRequest.objects
                .filter(company=company, job=job, status=CompanyJobRequestStatus.OPEN)
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if open_exists:
                raise forms.ValidationError(
                    "يوجد طلب مفتوح بالفعل لهذه الشركة وهذه الوظيفة. "
                    "أكمل الطلب الحالي أو ألغِه قبل إنشاء طلب جديد."
                )

        return cleaned_data

# Get the related Job model without assuming its import path.
JobModel = CompanyJobRequest._meta.get_field("job").remote_field.model


class JobFilterSelect2Widget(s2forms.ModelSelect2Widget):
    model = JobModel
    search_fields = [
        "name__icontains",
    ]

    attrs = {
        "data-placeholder": "ابحث عن الوظيفة...",
        "data-minimum-input-length": 2,
        "data-allow-clear": "true",
    }

    def get_queryset(self):
        return JobModel.objects.all().order_by("name")


class CompaniesRequestsFilterForm(forms.Form):
    ORDERING_CHOICES = [
        ("-created_at", "الأحدث أولاً"),
        ("created_at", "الأقدم أولاً"),
        ("-fee_per_employee", "الأعلى سعرًا"),
        ("fee_per_employee", "الأقل سعرًا"),
        ("-required_count", "الأكثر طلبًا"),
        ("required_count", "الأقل طلبًا"),
        ("company__name", "اسم الشركة"),
        ("job__name", "اسم الوظيفة"),
    ]

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "ابحث باسم الشركة أو الوظيفة أو الملاحظات...",
                "autocomplete": "off",
            }
        ),
    )

    job = forms.ModelChoiceField(
        required=False,
        queryset=JobModel.objects.all(),
        empty_label="كل الوظائف",
        widget=JobFilterSelect2Widget,
    )

    status = forms.ChoiceField(
        required=False,
        choices=[],
    )

    min_fee = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "أقل سعر",
                "step": "0.01",
                "min": "0",
            }
        ),
    )

    max_fee = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "أعلى سعر",
                "step": "0.01",
                "min": "0",
            }
        ),
    )

    ordering = forms.ChoiceField(
        required=False,
        choices=ORDERING_CHOICES,
        initial="-created_at",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        status_choices = CompanyJobRequest._meta.get_field(
            "status"
        ).choices

        self.fields["status"].choices = [
            ("", "كل الحالات"),
            *status_choices,
        ]

    def clean(self):
        cleaned_data = super().clean()

        min_fee = cleaned_data.get("min_fee")
        max_fee = cleaned_data.get("max_fee")

        if (
            min_fee is not None
            and max_fee is not None
            and min_fee > max_fee
        ):
            self.add_error(
                "max_fee",
                "يجب أن يكون أعلى سعر أكبر من أو يساوي أقل سعر.",
            )

        return cleaned_data

# ──────────────────────────────────────────────
# Applicant
# ──────────────────────────────────────────────

class ApplicantForm(forms.ModelForm):

    class Meta:
        model  = Applicant
        fields = [
            "full_name", "phone", "email",
            "birth_date", "gender", "qualification",
            "experience", "cv_file", "notes",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "الاسم الكامل",
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "رقم الهاتف",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-input",
                "placeholder": "البريد الإلكتروني (اختياري)",
            }),
            "birth_date": forms.DateInput(attrs={
                "class": "form-input",
                "type": "date",
            }),
            "gender": forms.Select(attrs={
                "class": "form-input",
            }),
            "qualification": forms.Select(attrs={
                "class": "form-input",
            }),
            "experience": forms.Textarea(attrs={
                "class": "form-input",
                "rows": 3,
                "placeholder": "الخبرات",
            }),
            "cv_file": forms.ClearableFileInput(attrs={
                "class": "form-input",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-input",
                "rows": 2,
                "placeholder": "الملاحظات",
            }),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone and Applicant.objects.filter(phone=phone).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("رقم الهاتف مسجل لمتقدم آخر.")
        return phone


# ──────────────────────────────────────────────
# Application
# ──────────────────────────────────────────────

class ApplicationForm(forms.ModelForm):

    class Meta:
        model  = Application
        fields = ["job_request", "applicant", "status", "employment_date", "notes"]
        widgets = {
            "job_request": ApplicantSelect2WidgetJobRequest,
            "applicant":   ApplicantSelect2MultipleWidgetApplicant,
            "status": forms.Select(attrs={
                "class": "form-input",
            }),
            "employment_date": forms.DateInput(attrs={
                "class": "form-input",
                "type": "date",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-input",
                "rows": 2,
                "placeholder": "الملاحظات",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        job_request = cleaned_data.get("job_request")
        applicant   = cleaned_data.get("applicant")
        status      = cleaned_data.get("status")

        # الطلب يجب أن يكون مفتوحاً
        if job_request and job_request.status != CompanyJobRequestStatus.OPEN:
            self.add_error("job_request", "لا يمكن إضافة ترشيح لطلب غير مفتوح.")

        # منع تكرار نفس المتقدم في نفس الطلب
        if job_request and applicant:
            duplicate = (
                Application.objects
                .filter(job_request=job_request, applicant=applicant)
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if duplicate:
                raise forms.ValidationError(
                    "هذا المتقدم مسجل مسبقاً في هذا الطلب."
                )

        # التحقق من عدم تجاوز الحد الأقصى عند القبول
        if status == ApplicationStatus.ACCEPTED and job_request:
            accepted_count = (
                Application.objects
                .filter(job_request=job_request, status=ApplicationStatus.ACCEPTED)
                .exclude(pk=self.instance.pk)
                .count()
            )
            if accepted_count >= job_request.required_count:
                self.add_error(
                    "status",
                    f"تم الوصول إلى الحد الأقصى ({job_request.required_count}) للمقبولين في هذا الطلب."
                )

        return cleaned_data


# ──────────────────────────────────────────────
# FollowUp
# ──────────────────────────────────────────────
class FollowUpForm(forms.ModelForm):
    """نموذج إضافة / تعديل متابعة"""

    class Meta:
        model = FollowUp
        fields = [
            "company",
            "applicant",
            "follow_up_date",
            "note",
            "status",
        ]

        widgets = {
            "company": CompanySelect2Widget(
                attrs={
                    "class": (
                        "w-full h-12 border border-[#dfe4e0] bg-[#fbfcfa] "
                        "text-[#29404d] text-[13px] px-3 "
                        "focus:outline-none focus:border-[#7d9b9a] "
                        "focus:ring-2 focus:ring-[#dce9e5] rounded-[4px] "
                        "transition-all duration-200"
                    ),
                    "data-placeholder": "ابحث عن الشركة...",
                }
            ),

            "applicant": ApplicantSelect2Widget(
                attrs={
                    "class": (
                        "w-full h-12 border border-[#dfe4e0] bg-[#fbfcfa] "
                        "text-[#29404d] text-[13px] px-3 "
                        "focus:outline-none focus:border-[#7d9b9a] "
                        "focus:ring-2 focus:ring-[#dce9e5] rounded-[4px] "
                        "transition-all duration-200"
                    ),
                    "data-placeholder": "ابحث عن المتقدم...",
                }
            ),

            "follow_up_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": (
                        "w-full h-12 border border-[#dfe4e0] "
                        "bg-[#fbfcfa] text-[#29404d] text-[13px] px-3 "
                        "focus:outline-none focus:border-[#7d9b9a] "
                        "focus:ring-2 focus:ring-[#dce9e5] rounded-[4px] "
                        "transition-all duration-200"
                    ),
                }
            ),

            "note": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "أدخل ملاحظات المتابعة هنا...",
                    "class": (
                        "w-full border border-[#dfe4e0] bg-[#fbfcfa] "
                        "text-[#29404d] text-[13px] px-3 py-3 "
                        "focus:outline-none focus:border-[#7d9b9a] "
                        "focus:ring-2 focus:ring-[#dce9e5] rounded-[4px] "
                        "transition-all duration-200 resize-none"
                    ),
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": (
                        "w-full h-12 border border-[#dfe4e0] "
                        "bg-[#fbfcfa] text-[#29404d] text-[13px] px-3 "
                        "focus:outline-none focus:border-[#7d9b9a] "
                        "focus:ring-2 focus:ring-[#dce9e5] rounded-[4px] "
                        "transition-all duration-200"
                    ),
                }
            ),
        }

        labels = {
            "company": "الشركة",
            "applicant": "المتقدم",
            "follow_up_date": "تاريخ المتابعة",
            "note": "الملاحظة",
            "status": "الحالة",
        }

    def clean(self):
        cleaned_data = super().clean()

        company = cleaned_data.get("company")
        applicant = cleaned_data.get("applicant")

        if not company and not applicant:
            raise forms.ValidationError(
                "يجب تحديد الشركة أو المتقدم."
            )

        if company and applicant:
            raise forms.ValidationError(
                "لا يمكن اختيار الشركة والمتقدم معاً."
            )

        return cleaned_data


class FollowUpFilterForm(forms.Form):
    """نموذج تصفية قائمة المتابعات"""

    STATUS_CHOICES = [("", "جميع الحالات")] + list(FollowUpStatus.choices)
    DATE_FILTER_CHOICES = [
        ("", "جميع التواريخ"),
        ("today", "اليوم"),
        ("overdue", "المتأخرة"),
        ("upcoming", "القادمة"),
        ("week", "هذا الأسبوع"),
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label="الحالة",
        widget=forms.Select(
            attrs={
                "class": (
                    "h-9 border border-[#dfe4e0] bg-[#fbfcfa] text-[#29404d] "
                    "text-[13px] px-3 focus:outline-none focus:border-[#7d9b9a] "
                    "rounded-[4px] transition-all duration-200"
                )
            }
        ),
    )

    date_filter = forms.ChoiceField(
        choices=DATE_FILTER_CHOICES,
        required=False,
        label="الفترة الزمنية",
        widget=forms.Select(
            attrs={
                "class": (
                    "h-9 border border-[#dfe4e0] bg-[#fbfcfa] text-[#29404d] "
                    "text-[13px] px-3 focus:outline-none focus:border-[#7d9b9a] "
                    "rounded-[4px] transition-all duration-200"
                )
            }
        ),
    )

    search = forms.CharField(
        required=False,
        label="بحث",
        widget=forms.TextInput(
            attrs={
                "placeholder": "بحث في الملاحظات...",
                "class": (
                    "h-9 border border-[#dfe4e0] bg-[#fbfcfa] text-[#29404d] "
                    "text-[13px] px-3 focus:outline-none focus:border-[#7d9b9a] "
                    "focus:ring-2 focus:ring-[#dce9e5] rounded-[4px] transition-all duration-200 w-56"
                ),
            }
        ),
    )


# ──────────────────────────────────────────────
# VoucherCategory
# ──────────────────────────────────────────────

class VoucherCategoryForm(forms.ModelForm):

    class Meta:
        model  = VoucherCategory
        fields = ["name", "type"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "اسم التصنيف",
            }),
            "type": forms.Select(attrs={
                "class": "form-input",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        voucher_type = cleaned_data.get("type")

        if name and voucher_type:
            duplicate = (
                VoucherCategory.objects
                .filter(
                    name=name,
                    type=voucher_type,
                )
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if duplicate:
                raise forms.ValidationError(
                    "يوجد تصنيف بنفس الاسم ونفس النوع مسبقاً."
                )

        return cleaned_data


# ──────────────────────────────────────────────
# Voucher dependency selector
# ──────────────────────────────────────────────

class VoucherDependencyForm(forms.Form):
    """
    الحقول التي تحدد القوائم التابعة قبل عرض بقية بيانات السند.

    هذا النموذج لا يحفظ أي بيانات. وظيفته إرسال قيم التحكم عبر GET
    حتى يعيد VoucherCreateView / VoucherUpdateView رسم الصفحة
    بالـ querysets الصحيحة.
    """

    company = forms.ModelChoiceField(
        label="الشركة",
        required=False,
        queryset=Company.objects.all(),
        widget=CompanySelect2Widget(
            attrs={
                "class": "form-input",
                "data-placeholder": "ابحث عن الشركة...",
                "data-minimum-input-length": 1,
            }
        ),
    )

    type = forms.ChoiceField(
        label="نوع السند",
        required=True,
        choices=VoucherCategoryType.choices,
        widget=forms.Select(
            attrs={
                "class": "form-input",
            }
        ),
    )

    expense_scope = forms.ChoiceField(
        label="نوع المصروف",
        required=False,
        choices=[
            ("general", "مصروف عام للمكتب"),
            ("company", "مصروف مرتبط بشركة"),
        ],
        initial="company",
        widget=forms.Select(
            attrs={
                "class": "form-input",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        voucher_type = cleaned_data.get("type")
        company = cleaned_data.get("company")
        expense_scope = cleaned_data.get("expense_scope")

        if voucher_type == VoucherCategoryType.RECEIPT:
            if not company:
                self.add_error(
                    "company",
                    "يجب اختيار الشركة في سند القبض.",
                )
            cleaned_data["expense_scope"] = "company"

        elif voucher_type == VoucherCategoryType.PAYMENT:
            if expense_scope == "company" and not company:
                self.add_error(
                    "company",
                    "اختر الشركة أو حدد نوع المصروف كمصروف عام.",
                )
            if expense_scope == "general":
                cleaned_data["company"] = None

        return cleaned_data


# ──────────────────────────────────────────────
# Voucher
# ──────────────────────────────────────────────

class VoucherForm(forms.ModelForm):
    expense_scope = forms.ChoiceField(
        label="نوع المصروف",
        required=False,
        choices=[
            ("general", "مصروف عام للمكتب"),
            ("company", "مصروف مرتبط بشركة"),
        ],
        widget=forms.Select(
            attrs={
                "class": "form-input expense-scope-select",
            }
        ),
    )

    class Meta:
        model = Voucher

        fields = [
            "company",
            "job_request",
            "type",
            "category",
            "currency",
            "amount",
            "voucher_date",
            "description",
        ]

        widgets = {
            "company": CompanySelect2Widget(
                attrs={
                    "class": "form-input",
                    "data-placeholder": "ابحث عن الشركة...",
                    "data-minimum-input-length": 1,
                }
            ),

            "job_request": JobRequestSelect2Widget(
                attrs={
                    "class": "form-input",
                    "data-placeholder": "ابحث عن طلب الشركة...",
                    "data-minimum-input-length": 1,
                }
            ),

            "category": VoucherCategorySelect2Widget(
                attrs={
                    "class": "form-input",
                    "data-placeholder": "اختر نوع السند أولاً...",
                    "data-minimum-input-length": 0,
                }
            ),

            "type": forms.Select(
                attrs={
                    "class": "form-input voucher-type-select",
                }
            ),

            "currency": forms.Select(
                attrs={
                    "class": "form-input",
                }
            ),

            "amount": forms.NumberInput(
                attrs={
                    "class": "form-input",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "أدخل المبلغ",
                }
            ),

            "voucher_date": forms.DateInput(
                attrs={
                    "class": "form-input",
                    "type": "date",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-input",
                    "rows": 4,
                    "placeholder": "اكتب بيان السند أو سبب العملية...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        dependency_company_id = kwargs.pop(
            "dependency_company_id",
            None,
        )
        dependency_type = kwargs.pop(
            "dependency_type",
            None,
        )
        dependency_expense_scope = kwargs.pop(
            "dependency_expense_scope",
            None,
        )
        dependency_values_supplied = kwargs.pop(
            "dependency_values_supplied",
            False,
        )

        super().__init__(*args, **kwargs)

        voucher_type = None
        if self.is_bound:
            voucher_type = self.data.get(self.add_prefix("type"))
        elif dependency_values_supplied:
            voucher_type = dependency_type
        elif dependency_type:
            voucher_type = dependency_type
        elif self.instance and self.instance.type:
            voucher_type = self.instance.type

        company_id = None
        if self.is_bound:
            company_id = self.data.get(self.add_prefix("company"))
        elif dependency_values_supplied:
            company_id = dependency_company_id
        elif dependency_company_id:
            company_id = dependency_company_id
        elif self.instance and self.instance.company_id:
            company_id = self.instance.company_id

        if not self.is_bound:
            if dependency_values_supplied:
                self.initial["company"] = (
                    Company.objects
                    .filter(pk=dependency_company_id)
                    .first()
                    if dependency_company_id
                    else None
                )
            elif dependency_company_id:
                self.initial["company"] = (
                    Company.objects
                    .filter(pk=dependency_company_id)
                    .first()
                )
            if dependency_values_supplied:
                self.initial["type"] = dependency_type
            elif dependency_type:
                self.initial["type"] = dependency_type
            if dependency_values_supplied:
                self.initial["expense_scope"] = (
                    dependency_expense_scope
                )
            elif dependency_expense_scope:
                self.initial["expense_scope"] = (
                    dependency_expense_scope
                )

        # ----------------------------------------------------
        # company
        # ----------------------------------------------------

        # سند القبض لا يكتمل بدون شركة، أما سند الصرف فالشركة اختيارية.
        self.fields["company"].required = (
            voucher_type == VoucherCategoryType.RECEIPT
        )
        if voucher_type == VoucherCategoryType.RECEIPT:
            self.fields["expense_scope"].initial = "company"
        elif dependency_expense_scope:
            self.fields["expense_scope"].initial = (
                dependency_expense_scope
            )
        elif company_id:
            self.fields["expense_scope"].initial = "company"
        else:
            self.fields["expense_scope"].initial = "general"

        # ----------------------------------------------------
        # job_request
        # ----------------------------------------------------

        self.fields["job_request"].required = False

        # ----------------------------------------------------
        # category
        # ----------------------------------------------------

        self.fields["category"].required = True

        # ----------------------------------------------------
        # تقييد طلبات الشركة عند وجود شركة مختارة
        # ----------------------------------------------------

        if company_id:
            self.fields["job_request"].queryset = (
                CompanyJobRequest.objects.filter(
                    company_id=company_id
                )
            )
        else:
            self.fields["job_request"].queryset = (
                CompanyJobRequest.objects.none()
            )

        # ----------------------------------------------------
        # تقييد التصنيفات حسب نوع السند
        # ----------------------------------------------------

        if voucher_type:
            category_queryset = VoucherCategory.objects.filter(
                type=voucher_type
            )
            self.fields["category"].queryset = category_queryset
        else:
            self.fields["category"].queryset = (
                VoucherCategory.objects.none()
            )

        # ----------------------------------------------------
        # Select2 dependencies
        # ----------------------------------------------------

        self.fields["category"].widget.dependent_fields = {
            "type": "type",
        }

        self.fields["job_request"].widget.dependent_fields = {
            "company": "company",
        }

    def clean(self):
        cleaned_data = super().clean()

        company = cleaned_data.get("company")
        job_request = cleaned_data.get("job_request")
        voucher_type = cleaned_data.get("type")
        category = cleaned_data.get("category")
        expense_scope = cleaned_data.get("expense_scope")

        # ----------------------------------------------------
        # التحقق من الشركة
        # ----------------------------------------------------

        if voucher_type == VoucherCategoryType.RECEIPT and not company:
            self.add_error(
                "company",
                "يجب اختيار الشركة في سند القبض."
            )

        if voucher_type == VoucherCategoryType.PAYMENT:
            expense_scope = expense_scope or (
                "company" if company else "general"
            )

            if expense_scope == "general":
                if company:
                    self.add_error(
                        "company",
                        "المصروف العام لا يرتبط بشركة."
                    )
                # ضمان عدم حفظ علاقة طلب قديمة مع مصروف عام.
                cleaned_data["company"] = None
                cleaned_data["job_request"] = None
                company = None
                job_request = None
            elif expense_scope == "company" and not company:
                self.add_error(
                    "company",
                    "اختر الشركة أو حدد نوع المصروف كمصروف عام."
                )

        if voucher_type == VoucherCategoryType.RECEIPT:
            cleaned_data["expense_scope"] = "company"

        # ----------------------------------------------------
        # التحقق من نوع السند والتصنيف
        # ----------------------------------------------------

        if voucher_type and category:

            if category.type != voucher_type:
                self.add_error(
                    "category",
                    "التصنيف المحدد لا يتبع نوع السند المختار."
                )

        # ----------------------------------------------------
        # التحقق من أن طلب الشركة تابع للشركة
        # ----------------------------------------------------

        if job_request and company:

            if job_request.company_id != company.id:
                self.add_error(
                    "job_request",
                    "طلب الشركة المحدد لا يتبع للشركة المختارة."
                )
        elif job_request and not company:
            self.add_error(
                "job_request",
                "لا يمكن اختيار طلب شركة بدون اختيار الشركة."
            )

        return cleaned_data


class VoucherFilterForm(forms.Form):

    type = forms.ChoiceField(
        label="نوع السند",
        required=False,
        choices=[
            ("", "كل الأنواع"),
            *VoucherCategoryType.choices,
        ],
        widget=forms.Select(
            attrs={
                "class": "form-input",
            }
        ),
    )

    category = forms.ModelChoiceField(
        label="التصنيف",
        required=False,
        queryset=VoucherCategory.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "form-input",
            }
        ),
    )

    company = forms.ModelChoiceField(
        label="الشركة",
        required=False,
        queryset=Company.objects.all(),
        widget=CompanySelect2Widget(
            attrs={
                "class": "form-input",
                "data-placeholder": "ابحث عن شركة...",
            }
        ),
    )

    date_from = forms.DateField(
        label="من تاريخ",
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-input",
                "type": "date",
            }
        ),
    )

    date_to = forms.DateField(
        label="إلى تاريخ",
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-input",
                "type": "date",
            }
        ),
    )

    search = forms.CharField(
        label="بحث",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": "رقم السند أو اسم الشركة أو البيان...",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        voucher_type = self.data.get("type")

        if voucher_type:
            self.fields["category"].queryset = (
                VoucherCategory.objects.filter(
                    type=voucher_type
                )
            )
