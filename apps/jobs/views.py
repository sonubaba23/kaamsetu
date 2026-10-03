from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.core.models import User
from apps.jobs.forms import JobForm
from apps.jobs.models import Booking, Job


class JobListView(ListView):
    model = Job
    template_name = "jobs/job_list.html"
    context_object_name = "jobs"
    paginate_by = 12

    def get_queryset(self):
        return Job.objects.filter(status=Job.Status.OPEN).select_related(
            "employer", "skill_category"
        )


class JobDetailView(LoginRequiredMixin, DetailView):
    model = Job
    template_name = "jobs/job_detail.html"
    context_object_name = "job"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        if user.role == User.Role.WORKER and hasattr(user, "worker_profile"):
            ctx["my_booking"] = Booking.objects.filter(
                job=self.object, worker=user.worker_profile
            ).first()
        return ctx


class EmployerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.role == User.Role.EMPLOYER and hasattr(
            user, "employer_profile"
        )


class JobCreateView(LoginRequiredMixin, EmployerRequiredMixin, CreateView):
    model = Job
    form_class = JobForm
    template_name = "jobs/job_form.html"
    success_url = reverse_lazy("employers:dashboard")
    login_url = "core:login"

    def form_valid(self, form):
        form.instance.employer = self.request.user.employer_profile
        response = super().form_valid(form)
        messages.success(self.request, "Job posted — it's now live for workers to apply.")
        return response


class JobApplyView(LoginRequiredMixin, View):
    """A worker applies to an open job, creating a booking request."""

    login_url = "core:login"

    def post(self, request, pk, *args, **kwargs):
        job = get_object_or_404(Job, pk=pk)
        worker = getattr(request.user, "worker_profile", None)

        if worker is None:
            messages.error(request, "Only worker accounts can apply to jobs.")
            return redirect("jobs:job_detail", pk=pk)

        if job.status != Job.Status.OPEN:
            messages.error(request, "This job is no longer accepting applications.")
            return redirect("jobs:job_detail", pk=pk)

        agreed_wage = worker.daily_wage if job.wage_type == Job.WageType.DAILY else job.budget_max

        try:
            Booking.objects.create(job=job, worker=worker, agreed_wage=agreed_wage)
            messages.success(request, "Application sent! The employer will review your request.")
        except IntegrityError:
            messages.info(request, "You've already applied to this job.")

        return redirect("jobs:job_detail", pk=pk)


class BookingActionView(LoginRequiredMixin, View):
    """An employer accepts, rejects, or completes one of their job's bookings."""

    login_url = "core:login"
    allowed_actions = {
        "accept": Booking.Status.ACCEPTED,
        "reject": Booking.Status.REJECTED,
        "complete": Booking.Status.COMPLETED,
    }

    def post(self, request, pk, action, *args, **kwargs):
        employer = getattr(request.user, "employer_profile", None)
        booking = get_object_or_404(Booking, pk=pk, job__employer=employer)

        new_status = self.allowed_actions.get(action)
        if new_status is None:
            messages.error(request, "Unknown action.")
            return redirect("employers:dashboard")

        booking.status = new_status
        if new_status == Booking.Status.ACCEPTED:
            booking.accepted_at = timezone.now()
        elif new_status == Booking.Status.COMPLETED:
            booking.completed_at = timezone.now()
        booking.save(update_fields=["status", "accepted_at", "completed_at"])

        messages.success(request, f"Booking marked as {booking.get_status_display().lower()}.")
        return redirect("employers:dashboard")
