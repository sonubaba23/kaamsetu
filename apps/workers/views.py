import json
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.utils import timezone
from django.views.generic import TemplateView

from apps.jobs.models import Booking
from apps.ml_models.models import TrustScoreLog


class WorkerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "workers/dashboard.html"
    login_url = "core:login"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        worker = self.request.user.worker_profile
        ctx["worker"] = worker

        bookings = worker.bookings.select_related("job", "job__employer").order_by("-created_at")
        ctx["job_feed"] = bookings[:8]
        ctx["portfolio"] = worker.portfolio.all()[:9]

        since = timezone.now() - timedelta(days=180)
        earnings_qs = (
            worker.bookings.filter(status=Booking.Status.COMPLETED, completed_at__gte=since)
            .values("completed_at__month")
            .annotate(total=Sum("agreed_wage"))
            .order_by("completed_at__month")
        )
        ctx["earnings_labels"] = json.dumps(
            [f"Month {row['completed_at__month']}" for row in earnings_qs]
        )
        ctx["earnings_values"] = json.dumps([float(row["total"] or 0) for row in earnings_qs])

        trust_logs = worker.trust_score_logs.order_by("computed_at")[:12]
        ctx["trust_score_labels"] = json.dumps(
            [log.computed_at.strftime("%b %d") for log in trust_logs]
        )
        ctx["trust_score_values"] = json.dumps([float(log.score) for log in trust_logs])
        ctx["trust_score"] = float(worker.trust_score)
        ctx["trust_score_remainder"] = max(0, 100 - float(worker.trust_score))

        ctx["stats"] = {
            "jobs_completed": worker.jobs_completed,
            "average_rating": worker.average_rating,
            "active_bookings": bookings.filter(
                status__in=[Booking.Status.ACCEPTED, Booking.Status.IN_PROGRESS]
            ).count(),
        }
        return ctx
