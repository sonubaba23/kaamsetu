"""Hybrid job <-> worker matching.

Combines content-based filtering (trade match, location proximity, wage
fit, and TF-IDF text similarity between a worker's bio and a job's
description/title) with a collaborative-filtering-style signal: the
worker's trust score, itself aggregated from ratings and outcomes across
many employers (see apps.ml_models.services). That crowd-aggregated
signal stands in for user-item collaborative filtering, which needs a
much denser interaction history than a new marketplace has yet.
"""

import math
from typing import Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from apps.jobs.models import Job
from apps.workers.models import Worker

# Content-based weights.
WEIGHT_LOCATION = 25
WEIGHT_WAGE_FIT = 15
WEIGHT_TEXT_SIMILARITY = 20

# Collaborative-style weights.
WEIGHT_TRUST = 30
WEIGHT_EXPERIENCE = 10

# Weights above must sum to 100.
EXPERIENCE_CAP_YEARS = 10


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * earth_radius_km * math.asin(math.sqrt(a))


def _location_score(worker: Worker, job: Job) -> tuple[Optional[float], Optional[float]]:
    """Returns (score in [0, 1], distance_km). Score is None when the pair is out of range."""
    if (
        worker.latitude is not None
        and worker.longitude is not None
        and job.latitude is not None
        and job.longitude is not None
    ):
        distance_km = _haversine_km(
            float(worker.latitude), float(worker.longitude), float(job.latitude), float(job.longitude)
        )
        if distance_km > worker.service_radius_km:
            return None, distance_km
        return max(0.0, 1 - (distance_km / max(worker.service_radius_km, 1))), distance_km

    # No coordinates on one side or the other: fall back to an exact city match.
    same_city = bool(worker.city) and worker.city.strip().lower() == job.city.strip().lower()
    return (1.0 if same_city else None), None


def _wage_fit_score(worker: Worker, job: Job) -> float:
    if job.wage_type != Job.WageType.DAILY:
        return 0.5  # Fixed-price job: no daily-rate figure to compare against.

    wage = float(worker.daily_wage)
    budget_min, budget_max = float(job.budget_min), float(job.budget_max)
    if budget_min <= wage <= budget_max:
        return 1.0
    if wage < budget_min:
        return 1.0  # Worker is cheaper than the employer's floor.
    return max(0.0, budget_max / wage)  # Worker asks more than the ceiling: decay.


def _text_similarity_score(worker: Worker, job: Job) -> float:
    worker_text = (worker.bio or "").strip()
    job_text = f"{job.title} {job.description}".strip()
    if not worker_text or not job_text:
        return 0.5  # No text to compare: neutral, not penalized.

    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        matrix = vectorizer.fit_transform([worker_text, job_text])
    except ValueError:
        return 0.5  # Both texts reduced to nothing after stopword removal.
    return float(cosine_similarity(matrix[0], matrix[1])[0][0])


def _experience_score(worker: Worker) -> float:
    return min(worker.experience_years / EXPERIENCE_CAP_YEARS, 1.0)


def score_worker_for_job(worker: Worker, job: Job) -> Optional[dict]:
    """Score one worker against one job. Returns None if the pair is ineligible."""
    if worker.skill_category_id != job.skill_category_id:
        return None
    if not (worker.is_live and worker.is_available):
        return None

    location_score, distance_km = _location_score(worker, job)
    if location_score is None:
        return None

    wage_score = _wage_fit_score(worker, job)
    text_score = _text_similarity_score(worker, job)
    trust_score = float(worker.trust_score) / 100
    experience_score = _experience_score(worker)

    components = {
        "location": round(location_score * WEIGHT_LOCATION, 2),
        "wage_fit": round(wage_score * WEIGHT_WAGE_FIT, 2),
        "text_similarity": round(text_score * WEIGHT_TEXT_SIMILARITY, 2),
        "trust": round(trust_score * WEIGHT_TRUST, 2),
        "experience": round(experience_score * WEIGHT_EXPERIENCE, 2),
    }

    return {
        "worker": worker,
        "job": job,
        "total_score": round(sum(components.values()), 2),
        "distance_km": round(distance_km, 1) if distance_km is not None else None,
        "components": components,
    }


def recommend_jobs_for_worker(worker: Worker, limit: int = 20) -> list[dict]:
    """Rank open jobs in the worker's trade for that worker, best match first."""
    candidate_jobs = Job.objects.filter(
        status=Job.Status.OPEN, skill_category_id=worker.skill_category_id
    ).select_related("employer", "skill_category")

    matches = [score_worker_for_job(worker, job) for job in candidate_jobs]
    matches = [m for m in matches if m is not None]
    matches.sort(key=lambda m: m["total_score"], reverse=True)
    return matches[:limit]


def recommend_workers_for_job(job: Job, limit: int = 20) -> list[dict]:
    """Rank eligible workers for an employer's open job, best match first."""
    candidate_workers = Worker.objects.filter(
        skill_category_id=job.skill_category_id, is_live=True, is_available=True
    ).select_related("skill_category")

    matches = [score_worker_for_job(worker, job) for worker in candidate_workers]
    matches = [m for m in matches if m is not None]
    matches.sort(key=lambda m: m["total_score"], reverse=True)
    return matches[:limit]
