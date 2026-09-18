from django.urls import path

from apps.employers import views

app_name = "employers"

urlpatterns = [
    path("", views.EmployerDashboardView.as_view(), name="dashboard"),
]
