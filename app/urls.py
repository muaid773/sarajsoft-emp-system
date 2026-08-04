from django.urls import path
from .views import dashboard, companies, follow_ups, companies_requests, applicants, applications, vouchers, financial_reports
from django.conf import settings
from django.conf.urls.static import static

app_name = "app"

urlpatterns = [
    path("", dashboard.dashboard_view, name="dashboard_view"),
    #companies
    path("companies/", companies.companies, name="companies"),
    path("companies/add/", companies.company_create, name="company_create"),
    path("companies/<int:pk>/edit/", companies.company_update, name="company_update"),
    # companies_requests
    path("companies_requests/", companies_requests.companies_requests, name="companies_requests"),
    path("companies_requests/add/", companies_requests.companies_requests_create, name="companies_requests_create"),
    path("companies_requests/<int:pk>/edit/", companies_requests.companies_requests_update, name="companies_requests_update"),
    # applicants
    path("applicants/", applicants.applicants, name="applicants"),
    path("applicants/<int:pk>/", applicants.applicant_details, name="applicants"),
    path("applicants/add/", applicants.applicants_create, name="applicants_create"),
    path("applicants/<int:pk>/edit/", applicants.applicants_update, name="applicants_update"),
    # applications
    path("applications/", applications.applications, name="applications"),
    path("applications/add/", applications.applications_create, name="applications_create"),
    path("applications/<int:pk>/edit", applications.applications_update, name="applications_update"),

    path("followups/",                 follow_ups.followups,        name="followup"),
    path("followups/list/",            follow_ups.followup_list,    name="followup_list"),
    path("followups/add/",             follow_ups.followup_create,  name="followup_create"),
    path("followups/<int:pk>/edit/",   follow_ups.followup_update,  name="followup_update"),
    path("followups/<int:pk>/delete/", follow_ups.followup_delete,  name="followup_delete"),
    path("followups/<int:pk>/toggle/",    follow_ups.followup_toggle_status,  name="followup_toggle_status"),
    # ────────────── Vouchers ──────────────
    path(
        "vouchers/",
        vouchers.VoucherListView.as_view(),
        name="voucher_list",
    ),
    path(
        "vouchers/add/",
        vouchers.VoucherCreateView.as_view(),
        name="voucher_create",
    ),
    path(
        "vouchers/<int:pk>/show",
        vouchers.VoucherDetailView.as_view(),
        name="voucher_detail",
    ),
    path(
        "vouchers/<int:pk>/edit/",
        vouchers.VoucherUpdateView.as_view(),
        name="voucher_update",
    ),
    path(
        "vouchers/<int:pk>/delete/",
        vouchers.VoucherDeleteView.as_view(),
        name="voucher_delete",
    ),
 
    # ────────────── Voucher Categories ──────────────
    path(
        "vouchers/categories/",
        vouchers.VoucherCategoryListView.as_view(),
        name="vouchercategory_list",
    ),
    path(
        "vouchers/categories/add/",
        vouchers.VoucherCategoryCreateView.as_view(),
        name="vouchercategory_create",
    ),
    path(
        "vouchers/categories/<int:pk>/edit/",
        vouchers.VoucherCategoryUpdateView.as_view(),
        name="vouchercategory_update",
    ),
    path(
        "vouchers/categories/<int:pk>/delete/",
        vouchers.VoucherCategoryDeleteView.as_view(),
        name="vouchercategory_delete",
    ),
 
    # ────────────── Select2 AJAX Endpoints ──────────────
    path(
        "vouchers/select2/company/",
        vouchers.CompanySelect2View.as_view(),
        name="voucher_company_select2",
    ),
    path(
        "vouchers/select2/job-request/",
        vouchers.JobRequestSelect2View.as_view(),
        name="voucher_jobrequest_select2",
    ),
    path(
        "vouchers/select2/category/",
        vouchers.VoucherCategorySelect2View.as_view(),
        name="voucher_category_select2",
    ),

    path("reports/", financial_reports.reports, name="reports"),

    path(
        "reports/companies/",
        financial_reports.companies_report,
        name="companies-report",
    ),

    path(
        "reports/applicants/",
        financial_reports.applicants_report,
        name="applicants-report",
    ),

    path(
        "reports/applicants/accepted/",
        financial_reports.accepted_applicants_report,
        name="accepted-applicants-report",
    ),

    path(
        "reports/financial/",
        financial_reports.financial_report,
        name="financial-report",
    ),

    path(
        "reports/export/csv/",
        financial_reports.export_report_csv,
        name="export-report-csv",
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)