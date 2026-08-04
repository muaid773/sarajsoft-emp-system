from django.contrib import admin

from .models import (
    Company,
    Job,
    CompanyJobRequest,
    Applicant,
    Application,
    FollowUp,
    VoucherCategory,
    Voucher,
    User,
)

admin.site.register(Company)
admin.site.register(Job)
admin.site.register(CompanyJobRequest)
admin.site.register(Applicant)
admin.site.register(Application)
admin.site.register(FollowUp)
admin.site.register(VoucherCategory)
admin.site.register(Voucher)
admin.site.register(User)