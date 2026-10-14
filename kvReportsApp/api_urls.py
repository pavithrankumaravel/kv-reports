from django.urls import path

from .api_views import (
    AdminTimeSheetAPI,
    EmployeeTimeSheetAPI,
    ReportAPIIndex,
    ReportDataAPI,
)

urlpatterns = [
    path("", ReportAPIIndex.as_view(), name="reportApiIndex"),
    path("timesheets/employee/", EmployeeTimeSheetAPI.as_view(), name="employeeTimeSheetApi"),
    path("timesheets/admin/", AdminTimeSheetAPI.as_view(), name="adminTimeSheetApi"),
    path("<slug:business>/<slug:report_name>/", ReportDataAPI.as_view(), name="reportDataApi"),
]
