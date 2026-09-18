"""Trust score computation for workers.

The score blends four signals into a single 0-100 value: review ratings,
completed-job volume, cancellation behavior, and punctuality. Each
computation is also persisted as a TrustScoreLog row for audit/trend charts.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Avg

from apps.jobs.models import Booking
from apps.ml_models.models import TrustScoreLog
from apps.workers.models import Worker

MODEL_VERSION = "v1"

# Weights must sum to 100.
WEIGHT_RATING = Decimal("40")
WEIGHT_COMPLETION_VOLUME = Decimal("20")
WEIGHT_CANCELLATION = Decimal("20")
WEIGHT_PUNCTUALITY = Decimal("20")

# Jobs completed at/above this count earns the full volume weight.
COMPLETED_JOBS_CAP = 50


def _completed_bookings(worker: Worker):
    return worker.bookings.filter(status=Booking.Status.COMPLETED)


def _avg_rating(worker: Worker) -> Decimal:
    agg = worker.reviews.aggregate(avg=Avg("rating"))
    return Decimal(str(agg["avg"] or 0))


def _cancellation_rate(worker: Worker) -> Decimal:
    """Share of the worker's non-pending bookings that the worker cancelled."""
    total = worker.bookings.exclude(status=Booking.Status.REQUESTED).count()
    if total == 0:
        return Decimal("0")
    cancelled_by_worker = worker.bookings.filter(
        status=Booking.Status.CANCELLED, cancelled_by="worker"
    ).count()
    return Decimal(cancelled_by_worker) / Decimal(total)


def _punctuality_rate(worker: Worker) -> Decimal:
    """Share of completed, punctuality-rated bookings the worker was on time for."""
    rated = _completed_bookings(worker).exclude(is_punctual__isnull=True)
    total = rated.count()
    if total == 0:
        return Decimal("1")  # No data yet: don't penalize.
    punctual = rated.filter(is_punctual=True).count()
    return Decimal(punctual) / Decimal(total)


def compute_trust_score(worker: Worker) -> dict:
    """Compute the current trust score and its components, without saving anything."""
    jobs_completed = _completed_bookings(worker).count()
    avg_rating = _avg_rating(worker)
    cancellation_rate = _cancellation_rate(worker)
    punctuality_rate = _punctuality_rate(worker)

    rating_component = (avg_rating / Decimal("5")) * WEIGHT_RATING
    volume_component = (
        min(Decimal(jobs_completed) / Decimal(COMPLETED_JOBS_CAP), Decimal("1"))
        * WEIGHT_COMPLETION_VOLUME
    )
    cancellation_component = (Decimal("1") - cancellation_rate) * WEIGHT_CANCELLATION
    punctuality_component = punctuality_rate * WEIGHT_PUNCTUALITY

    score = rating_component + volume_component + cancellation_component + punctuality_component
    score = max(Decimal("0"), min(score, Decimal("100")))

    return {
        "score": score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "jobs_completed": jobs_completed,
        "cancellation_rate": cancellation_rate.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        "avg_rating": avg_rating.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "punctuality_rate": punctuality_rate.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
    }


def update_worker_trust_score(worker: Worker) -> TrustScoreLog:
    """Recompute, persist to the worker profile, and log the result."""
    result = compute_trust_score(worker)

    worker.trust_score = result["score"]
    worker.save(update_fields=["trust_score", "updated_at"])

    return TrustScoreLog.objects.create(
        worker=worker,
        score=result["score"],
        jobs_completed=result["jobs_completed"],
        cancellation_rate=result["cancellation_rate"],
        avg_rating=result["avg_rating"],
        punctuality_rate=result["punctuality_rate"],
        model_version=MODEL_VERSION,
    )
