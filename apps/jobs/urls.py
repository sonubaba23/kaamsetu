from django.urls import path

from apps.jobs import views

app_name = "jobs"

urlpatterns = [
    path("", views.JobListView.as_view(), name="job_list"),
    path("post/", views.JobCreateView.as_view(), name="job_create"),
    path("<int:pk>/", views.JobDetailView.as_view(), name="job_detail"),
    path("<int:pk>/apply/", views.JobApplyView.as_view(), name="job_apply"),
    path(
        "bookings/<int:pk>/<str:action>/",
        views.BookingActionView.as_view(),
        name="booking_action",
    ),
]
