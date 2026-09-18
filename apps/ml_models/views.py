from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View

from apps.ml_models.services import update_worker_trust_score


class RecomputeTrustScoreView(LoginRequiredMixin, View):
    """Recompute the requesting user's own worker trust score on demand."""

    login_url = "core:login"

    def post(self, request, *args, **kwargs):
        worker = getattr(request.user, "worker_profile", None)
        if worker is None:
            return JsonResponse({"error": "No worker profile for this account."}, status=404)

        log = update_worker_trust_score(worker)

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"score": str(log.score), "computed_at": log.computed_at.isoformat()})

        messages.success(request, f"Trust score recomputed: {log.score}")
        return redirect("workers:dashboard")
