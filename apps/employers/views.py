import json
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from apps.jobs.models import Booking, Job
from apps.payments.models import Escrow

# Approximate coordinates for major Indian cities, used to plot the demand heat map.
CITY_COORDS = {
    "mumbai": (19.0760, 72.8777), "delhi": (28.7041, 77.1025), "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946), "hyderabad": (17.3850, 78.4867), "ahmedabad": (23.0225, 72.5714),
    "chennai": (13.0827, 80.2707), "kolkata": (22.5726, 88.3639), "pune": (18.5204, 73.8567),
    "jaipur": (26.9124, 75.7873), "lucknow": (26.8467, 80.9462), "surat": (21.1702, 72.8311),
    "nagpur": (21.1458, 79.0882), "indore": (22.7196, 75.8577), "bhopal": (23.2599, 77.4126),
    "patna": (25.5941, 85.1376), "chandigarh": (30.7333, 76.7794), "kochi": (9.9312, 76.2673),
}


class EmployerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "employers/dashboard.html"
    login_url = "core:login"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        employer = self.request.user.employer_profile
        ctx["employer"] = employer

        jobs = employer.jobs.order_by("-created_at")
        ctx["jobs"] = jobs[:8]

        bookings = Booking.objects.filter(job__employer=employer).select_related(
            "worker__user", "worker__skill_category", "job"
        )
        ctx["crew_board"] = {
            "requested": bookings.filter(status=Booking.Status.REQUESTED)[:6],
            "active": bookings.filter(
                status__in=[Booking.Status.ACCEPTED, Booking.Status.IN_PROGRESS]
            )[:6],
            "completed": bookings.filter(status=Booking.Status.COMPLETED)[:6],
        }
        ctx["booking_timeline"] = bookings.order_by("-created_at")[:10]

        since = timezone.now() - timedelta(days=180)
        spend_qs = (
            Escrow.objects.filter(
                booking__job__employer=employer, status=Escrow.Status.RELEASED, released_at__gte=since
            )
            .values("released_at__month")
            .annotate(total=Sum("amount"))
            .order_by("released_at__month")
        )
        ctx["spend_labels"] = json.dumps([f"Month {r['released_at__month']}" for r in spend_qs])
        ctx["spend_values"] = json.dumps([float(r["total"] or 0) for r in spend_qs])

        ctx["stats"] = {
            "open_jobs": jobs.filter(status=Job.Status.OPEN).count(),
            "active_crew": bookings.filter(
                status__in=[Booking.Status.ACCEPTED, Booking.Status.IN_PROGRESS]
            ).count(),
            "total_spend": employer.total_spend,
        }

        city_demand = Job.objects.values("city").annotate(count=Count("id")).order_by("-count")
        points = []
        for row in city_demand:
            coords = CITY_COORDS.get(row["city"].strip().lower())
            if coords:
                points.append(
                    {"lat": coords[0], "lng": coords[1], "radius": 15000 + row["count"] * 4000,
                     "label": f"{row['city']}: {row['count']} open jobs"}
                )
        ctx["demand_points_json"] = json.dumps(points)
        return ctx
