from django.urls import path

from apps.jobs import views

app_name = "jobs"

urlpatterns = [
    path("", views.JobListView.as_view(), name="job_list"),
    path("<int:pk>/", views.JobDetailView.as_view(), name="job_detail"),
]
