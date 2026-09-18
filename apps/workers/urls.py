from django.urls import path

from apps.workers import views

app_name = "workers"

urlpatterns = [
    path("", views.WorkerDashboardView.as_view(), name="dashboard"),
]
