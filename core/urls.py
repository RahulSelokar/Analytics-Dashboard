from django.contrib import admin
from django.urls import path
from core.views import dashboard, dashboard_data_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", dashboard, name="dashboard"),
    path("api/dashboard-data/", dashboard_data_api, name="dashboard_data_api"),
]
