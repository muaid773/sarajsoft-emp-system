from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# ──────────────────────────────────────────────
# Base & Validators
# ──────────────────────────────────────────────

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("تاريخ الإنشاء", auto_now_add=True)
    updated_at = models.DateTimeField("تاريخ التحديث", auto_now=True)

    class Meta:
        abstract = True


phone_validator = RegexValidator(
    regex=r'^[0-9+\-\s()]{7,30}$',
    message="أدخل رقم هاتف صالحًا."
)


# ──────────────────────────────────────────────
# Choices
# ──────────────────────────────────────────────

class GenderChoices(models.TextChoices):
    MALE   = "MALE",   "ذكر"
    FEMALE = "FEMALE", "أنثى"


class QualificationChoices(models.TextChoices):
    SECONDARY = "SECONDARY", "ثانوي"
    DIPLOMA   = "DIPLOMA",   "دبلوم"
    BACHELOR  = "BACHELOR",  "بكالوريوس"
    MASTER    = "MASTER",    "ماجستير"
    PHD       = "PHD",       "دكتوراة"
    OTHER     = "OTHER",     "أخرى"


class ApplicationStatus(models.TextChoices):
    NEW          = "NEW",          "جديد"
    UNDER_REVIEW = "UNDER_REVIEW", "قيد المراجعة"
    WAITING      = "WAITING",      "قائمة انتظار"
    WITHDRAWN    = "WITHDRAWN",    "انسحب"
    ACCEPTED     = "ACCEPTED",     "مقبول"
    REJECTED     = "REJECTED",     "مرفوض"
    HIRED        = "HIRED",        "تم التوظيف"


class CompanyJobRequestStatus(models.TextChoices):
    OPEN      = "OPEN",      "مفتوح"
    COMPLETED = "COMPLETED", "مكتمل"
    CANCELLED = "CANCELLED", "ملغي"


class CurrencyChoices(models.TextChoices):
    YER = "YER", "ريال يمني"
    USD = "USD", "دولار أمريكي"
    SAR = "SAR", "ريال سعودي"


class VoucherCategoryType(models.TextChoices):
    RECEIPT = "RECEIPT", "سند قبض"
    PAYMENT = "PAYMENT", "سند صرف"



class FollowUpStatus(models.TextChoices):
    PENDING   = "PENDING",   "معلقة"
    COMPLETED = "COMPLETED", "مكتملة"



# ──────────────────────────────────────────────
# Core Models
# ──────────────────────────────────────────────

class Company(TimeStampedModel):
    name      = models.CharField("اسم الشركة", max_length=255, db_index=True)
    phone     = models.CharField("رقم الهاتف", max_length=30, unique=True, db_index=True, validators=[phone_validator])
    email     = models.EmailField("البريد الإلكتروني", blank=True, unique=True, null=True)
    address   = models.TextField("العنوان")
    notes     = models.TextField("ملاحظات", blank=True, null=True)
    is_active = models.BooleanField("نشطة", default=True)

    class Meta:
        verbose_name        = "شركة"
        verbose_name_plural = "الشركات"
        ordering            = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self):
        return self.name


class Job(TimeStampedModel):
    name        = models.CharField("اسم الوظيفة", max_length=255, unique=True, db_index=True)
    description = models.TextField("الوصف", blank=True, null=True)

    class Meta:
        verbose_name        = "وظيفة"
        verbose_name_plural = "الوظائف"
        ordering            = ["name"]

    def __str__(self):
        return self.name


class CompanyJobRequest(TimeStampedModel):
    company = models.ForeignKey(
        Company,
        verbose_name="الشركة",
        on_delete=models.PROTECT,
        related_name="job_requests",
    )
    job = models.ForeignKey(
        Job,
        verbose_name="الوظيفة",
        on_delete=models.PROTECT,
        related_name="company_requests",
    )
    required_count = models.PositiveIntegerField(
        "عدد المطلوبين",
        validators=[MinValueValidator(1)],
    )
    fee_per_employee = models.DecimalField(
        "الرسوم لكل موظف",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    currency = models.CharField(
        "العملة",
        max_length=3,
        choices=CurrencyChoices.choices,
        default=CurrencyChoices.YER,
    )
    status = models.CharField(
        "الحالة",
        max_length=20,
        choices=CompanyJobRequestStatus.choices,
        default=CompanyJobRequestStatus.OPEN,
        db_index=True,
    )
    notes = models.TextField("ملاحظات", blank=True, null=True)

    class Meta:
        verbose_name        = "طلب شركة"
        verbose_name_plural = "طلبات الشركات"
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["company", "job"]),
        ]
        # لا يوجد UniqueConstraint على (company, job) هنا —
        # المنطق في clean(): شركة لا تملك إلا طلبًا مفتوحًا واحدًا لكل وظيفة.
        # يُسمح بطلب جديد بعد إكمال أو إلغاء الطلب السابق.

    def clean(self):
        super().clean()

        # منع وجود أكثر من طلب مفتوح لنفس الشركة ونفس الوظيفة
        if self.company_id and self.job_id:
            open_exists = (
                CompanyJobRequest.objects
                .filter(
                    company=self.company_id,
                    job=self.job_id,
                    status=CompanyJobRequestStatus.OPEN,
                )
                .exclude(pk=self.pk)
                .exists()
            )
            if open_exists:
                raise ValidationError(
                    "يوجد طلب مفتوح بالفعل لهذه الشركة وهذه الوظيفة. "
                    "أكمل الطلب الحالي أو ألغِه قبل إنشاء طلب جديد."
                )

        if self.status == CompanyJobRequestStatus.COMPLETED:
            accepted_count = self.applications.filter(
                status=ApplicationStatus.ACCEPTED
            ).count()



            under_review_count = self.applications.filter(
                status=ApplicationStatus.UNDER_REVIEW
            ).count()

            if under_review_count > 0:
                raise ValidationError({
                    "status": "لا يمكن إكمال الطلب. يوجد متقدمون قيد المراجعة."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def total_amount(self):
        return self.required_count * self.fee_per_employee

    def __str__(self):
        return f"{self.company.name} - {self.job.name}"


# ──────────────────────────────────────────────
# Applicant & Applications
# ──────────────────────────────────────────────

class Applicant(TimeStampedModel):
    full_name     = models.CharField("الاسم الكامل", max_length=255, db_index=True)
    phone         = models.CharField(
        "رقم الهاتف",
        max_length=30,
        unique=True,        # ✔ كل متقدم له رقم هاتف فريد
        db_index=True,
        validators=[phone_validator],
    )
    email         = models.EmailField("البريد الإلكتروني", blank=True, null=True)
    birth_date    = models.DateField("تاريخ الميلاد")
    gender        = models.CharField("الجنس", max_length=10, choices=GenderChoices.choices)
    qualification = models.CharField("المؤهل", max_length=20, choices=QualificationChoices.choices)
    experience    = models.TextField("الخبرات")
    cv_file       = models.FileField("السيرة الذاتية", upload_to="cvs/", blank=True, null=True)
    notes         = models.TextField("ملاحظات", blank=True, null=True)

    class Meta:
        verbose_name        = "متقدم"
        verbose_name_plural = "متقدمون"
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["phone"]),
        ]

    def clean(self):
        super().clean()
        if self.birth_date and self.birth_date > timezone.localdate():
            raise ValidationError({"birth_date": "لا يمكن أن يكون تاريخ الميلاد في المستقبل."})

    def __str__(self):
        return self.full_name


class Application(TimeStampedModel):
    job_request = models.ForeignKey(
        CompanyJobRequest,
        verbose_name="طلب الشركة",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    applicant = models.ForeignKey(
        Applicant,
        verbose_name="المتقدم",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    status = models.CharField(
        "الحالة",
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.NEW,
        db_index=True,
    )
    fee_per_employee_snapshot = models.DecimalField(
        "رسوم الموظف وقت القبول",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        editable=False,
    )
    employment_date = models.DateField("تاريخ التوظيف", blank=True, null=True, db_index=True)
    notes           = models.TextField("ملاحظات", blank=True, null=True)

    class Meta:
        verbose_name        = "طلب توظيف"
        verbose_name_plural = "طلبات التوظيف"
        ordering            = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["job_request", "applicant"],
                name="unique_applicant_per_job_request",
            )
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["job_request", "applicant"]),
        ]

    def clean(self):
        super().clean()

        if self.job_request_id:
            if self.job_request.status != CompanyJobRequestStatus.OPEN:
                raise ValidationError({
                    "job_request": "لا يمكن إضافة ترشيح لهذا الطلب لأنه ليس مفتوحاً."
                })

        if self.status == ApplicationStatus.ACCEPTED and self.job_request_id:
            is_new_acceptance = True

            if self.pk:
                old_status        = Application.objects.get(pk=self.pk).status
                is_new_acceptance = old_status != ApplicationStatus.ACCEPTED

            if is_new_acceptance:
                accepted_count = Application.objects.filter(
                    job_request=self.job_request,
                    status=ApplicationStatus.ACCEPTED,
                ).exclude(pk=self.pk).count()

                if accepted_count >= self.job_request.required_count:
                    raise ValidationError({
                        "status": "تم الوصول إلى العدد المطلوب لهذه الوظيفة."
                    })

    def save(self, *args, **kwargs):
        if (
            self.status == ApplicationStatus.ACCEPTED
            and self.fee_per_employee_snapshot is None
            and self.job_request_id
        ):
            self.fee_per_employee_snapshot = self.job_request.fee_per_employee
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.applicant.full_name} → {self.job_request}"



# ──────────────────────────────────────────────
# Follow-ups
# ──────────────────────────────────────────────

class FollowUp(TimeStampedModel):
    company = models.ForeignKey(
        Company,
        verbose_name="الشركة",
        on_delete=models.CASCADE,
        related_name="follow_ups",
        blank=True,
        null=True,
    )
    applicant = models.ForeignKey(
        Applicant,
        verbose_name="المتقدم",
        on_delete=models.CASCADE,
        related_name="follow_ups",
        blank=True,
        null=True,
    )
    follow_up_date = models.DateField("تاريخ المتابعة", db_index=True)
    note           = models.TextField("الملاحظة")
    status         = models.CharField(
        "الحالة",
        max_length=20,
        choices=FollowUpStatus.choices,
        default=FollowUpStatus.PENDING,
        db_index=True,
    )

    class Meta:
        verbose_name        = "متابعة"
        verbose_name_plural = "المتابعات"
        ordering            = ["-follow_up_date", "-created_at"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def clean(self):
        super().clean()
        if not self.company and not self.applicant:
            raise ValidationError("يجب تحديد الشركة أو المتقدم.")
        if self.company and self.applicant:
            raise ValidationError("لا يمكن اختيار الشركة والمتقدم معاً.")

    def __str__(self):
        target = self.company or self.applicant
        return f"{target} - {self.follow_up_date}"


# ──────────────────────────────────────────────
# Vouchers
# ──────────────────────────────────────────────



class VoucherCategory(TimeStampedModel):
    name = models.CharField(
        "اسم التصنيف",
        max_length=255,
        db_index=True,
    )

    type = models.CharField(
        "نوع السند",
        max_length=10,
        choices=VoucherCategoryType.choices,
        db_index=True,
    )

    class Meta:
        verbose_name = "تصنيف سند"
        verbose_name_plural = "تصنيفات السندات"
        ordering = ["type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "type"],
                name="unique_voucher_category_name_type",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Voucher(TimeStampedModel):
    voucher_number = models.CharField(
        "رقم السند",
        max_length=30,
        unique=True,
        db_index=True,
        blank=True,
        null=True,
        default=None,
        editable=False,
    )

    # --------------------------------------------------
    # الشركة المرتبط بها السند
    # تبقى العلاقة إن كانت الشركة موجودة
    # وتصبح NULL إذا تم حذف الشركة
    # --------------------------------------------------
    company = models.ForeignKey(
        Company,
        verbose_name="الشركة",
        on_delete=models.SET_NULL,
        related_name="vouchers",
        blank=True,
        null=True,
    )

    # --------------------------------------------------
    # Snapshot لبيانات الشركة وقت إنشاء السند
    # هذه البيانات لا تتأثر بحذف أو تعديل الشركة لاحقًا
    # --------------------------------------------------
    company_name = models.CharField(
        "اسم الشركة وقت إنشاء السند",
        max_length=255,
        blank=True,
        default="",
    )

    company_phone = models.CharField(
        "رقم هاتف الشركة وقت إنشاء السند",
        max_length=30,
        blank=True,
        null=True,
    )

    company_email = models.EmailField(
        "بريد الشركة وقت إنشاء السند",
        blank=True,
        null=True,
    )

    # --------------------------------------------------
    # طلب الشركة - اختياري
    # يستخدم فقط إذا كان السند مرتبطًا بطلب توظيف محدد
    # --------------------------------------------------
    job_request = models.ForeignKey(
        CompanyJobRequest,
        verbose_name="طلب الشركة",
        on_delete=models.SET_NULL,
        related_name="vouchers",
        blank=True,
        null=True,
    )

    # --------------------------------------------------
    # نوع السند
    # قبض / صرف
    # --------------------------------------------------
    type = models.CharField(
        "نوع السند",
        max_length=10,
        choices=VoucherCategoryType.choices,
        db_index=True,
    )

    # --------------------------------------------------
    # تصنيف السند
    # يجب أن يتطابق نوع التصنيف مع نوع السند
    # --------------------------------------------------
    category = models.ForeignKey(
        VoucherCategory,
        verbose_name="التصنيف",
        on_delete=models.PROTECT,
        related_name="vouchers",
    )

    currency = models.CharField(
        "العملة",
        max_length=3,
        choices=CurrencyChoices.choices,
        default=CurrencyChoices.YER,
    )

    amount = models.DecimalField(
        "المبلغ",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    voucher_date = models.DateField(
        "تاريخ السند",
        db_index=True,
    )

    description = models.TextField(
        "البيان",
    )

    class Meta:
        verbose_name = "سند"
        verbose_name_plural = "سندات"

        ordering = [
            "-voucher_date",
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=["voucher_date"],
            ),
            models.Index(
                fields=["company", "voucher_date"],
            ),
            models.Index(
                fields=["job_request", "voucher_date"],
            ),
            models.Index(
                fields=["type", "voucher_date"],
            ),
        ]

    def clean(self):
        super().clean()

        # ==================================================
        # 0. سند القبض يجب أن يرتبط بشركة
        # ==================================================
        if self.type == VoucherCategoryType.RECEIPT and not self.company_id:
            raise ValidationError({
                "company": "يجب اختيار الشركة في سند القبض."
            })

        # لا يمكن ربط طلب شركة بسند لا يحتوي على شركة.
        if self.job_request_id and not self.company_id:
            raise ValidationError({
                "job_request": (
                    "لا يمكن اختيار طلب شركة بدون اختيار الشركة المرتبطة به."
                )
            })

        # المصروف العام لا يحتفظ ببيانات snapshot لشركة سابقة.
        if self.type == VoucherCategoryType.PAYMENT and not self.company_id:
            self.company_name = ""
            self.company_phone = None
            self.company_email = None

        # ==================================================
        # 1. التحقق من توافق نوع السند مع تصنيف السند
        # ==================================================
        if self.type and self.category_id:
            if self.category.type != self.type:
                raise ValidationError({
                    "category": (
                        "تصنيف السند لا يتوافق مع نوع السند المحدد. "
                        "اختر تصنيفًا تابعًا لنفس نوع السند."
                    )
                })

        # ==================================================
        # 2. التحقق من أن طلب الشركة تابع لنفس الشركة
        # ==================================================
        if self.job_request_id and self.company_id:
            if self.job_request.company_id != self.company_id:
                raise ValidationError({
                    "job_request": (
                        "طلب الشركة المحدد لا يتبع للشركة المختارة."
                    )
                })

    def save(self, *args, **kwargs):
        # --------------------------------------------------
        # عند إنشاء السند لأول مرة:
        # أخذ Snapshot من بيانات الشركة
        # --------------------------------------------------
        if self.company_id:
            self.company_name = self.company.name
            self.company_phone = self.company.phone
            self.company_email = self.company.email
        elif self.type == VoucherCategoryType.PAYMENT:
            self.company_name = ""
            self.company_phone = None
            self.company_email = None

        self.full_clean()

        # --------------------------------------------------
        # حفظ السند
        # --------------------------------------------------
        super().save(*args, **kwargs)

        # --------------------------------------------------
        # توليد رقم السند بعد الحصول على PK
        # --------------------------------------------------
        if not self.voucher_number:
            self.voucher_number = f"VCH-{self.pk:06d}"

            super().save(
                update_fields=["voucher_number"]
            )

    def __str__(self):
        return (
            f"{self.voucher_number or 'NEW'} - "
            f"{self.company_name} - "
            f"{self.amount}"
        )

# ──────────────────────────────────────────────
# Users
# ──────────────────────────────────────────────

class User(AbstractUser):
    updated_at = models.DateTimeField("تاريخ التحديث", auto_now=True)

    class Meta:
        verbose_name        = "مستخدم"
        verbose_name_plural = "المستخدمون"
        swappable           = "AUTH_USER_MODEL"
