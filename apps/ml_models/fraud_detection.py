"""Fraud detection for reviews.

Combines an NLP signal (NLTK VADER sentiment vs. the star rating) with
three heuristic signals: a low-effort extreme rating, near-duplicate
review text from the same employer (TF-IDF cosine), and an unusual burst
of reviews from one employer in a short window. These catch different
shapes of fake/manipulated reviews without needing a trained classifier
or a large labeled dataset, which a new marketplace doesn't have yet.

Flagged reviews are written back onto the Review row (sentiment_score,
fraud_confidence, is_flagged_fake) and logged as a FraudFlag for a human
to resolve — this module never auto-resolves or deletes a review.
"""

from datetime import timedelta
from decimal import Decimal
from typing import Optional

import nltk
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from apps.jobs.models import Review
from apps.ml_models.models import FraudFlag

# Weights must sum to 100.
WEIGHT_SENTIMENT_MISMATCH = 40
WEIGHT_LOW_EFFORT = 20
WEIGHT_DUPLICATE_TEXT = 25
WEIGHT_EMPLOYER_BURST = 15

FRAUD_THRESHOLD = 0.6
LOW_EFFORT_COMMENT_LENGTH = 10
DUPLICATE_TEXT_SAMPLE_SIZE = 50
BURST_WINDOW_HOURS = 24
BURST_THRESHOLD = 3  # 3+ other reviews from the same employer in the window

_sentiment_analyzer = None


def _get_sentiment_analyzer():
    """Lazily build the VADER analyzer, downloading its lexicon on first use if missing."""
    global _sentiment_analyzer
    if _sentiment_analyzer is not None:
        return _sentiment_analyzer

    from nltk.sentiment import SentimentIntensityAnalyzer

    try:
        _sentiment_analyzer = SentimentIntensityAnalyzer()
    except LookupError:
        nltk.download("vader_lexicon", quiet=True)
        _sentiment_analyzer = SentimentIntensityAnalyzer()
    return _sentiment_analyzer


def _sentiment_mismatch_score(review: Review) -> tuple[float, Optional[float]]:
    """Returns (mismatch in [0, 1], raw VADER compound score or None if no comment)."""
    comment = (review.comment or "").strip()
    if not comment:
        return 0.0, None

    compound = _get_sentiment_analyzer().polarity_scores(comment)["compound"]  # -1..1
    expected = (review.rating - 3) / 2  # 1 star -> -1, 5 stars -> 1
    mismatch = abs(compound - expected) / 2  # 0..1
    return mismatch, compound


def _low_effort_extreme_score(review: Review) -> float:
    comment = (review.comment or "").strip()
    if review.rating in (1, 5) and len(comment) < LOW_EFFORT_COMMENT_LENGTH:
        return 1.0
    return 0.0


def _duplicate_text_score(review: Review) -> float:
    """Max text similarity against this employer's other reviews (a review-farm signal)."""
    comment = (review.comment or "").strip()
    if not comment:
        return 0.0

    others = list(
        Review.objects.filter(employer_id=review.employer_id)
        .exclude(pk=review.pk)
        .exclude(comment="")
        .values_list("comment", flat=True)[:DUPLICATE_TEXT_SAMPLE_SIZE]
    )
    if not others:
        return 0.0

    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        matrix = vectorizer.fit_transform([comment, *others])
    except ValueError:
        return 0.0  # All texts reduced to nothing after stopword removal.
    similarities = cosine_similarity(matrix[0], matrix[1:])[0]
    return float(similarities.max())


def _employer_burst_score(review: Review) -> float:
    """How many OTHER reviews this employer posted in the window around this one."""
    reference_time = review.created_at or timezone.now()
    window_start = reference_time - timedelta(hours=BURST_WINDOW_HOURS)
    recent_count = (
        Review.objects.filter(employer_id=review.employer_id, created_at__gte=window_start, created_at__lte=reference_time)
        .exclude(pk=review.pk)
        .count()
    )
    return min(recent_count / BURST_THRESHOLD, 1.0)


def score_review_for_fraud(review: Review) -> dict:
    """Compute the fraud confidence and its components, without saving anything."""
    mismatch_score, sentiment_compound = _sentiment_mismatch_score(review)
    low_effort_score = _low_effort_extreme_score(review)
    duplicate_score = _duplicate_text_score(review)
    burst_score = _employer_burst_score(review)

    components = {
        "sentiment_mismatch": round(mismatch_score * WEIGHT_SENTIMENT_MISMATCH, 2),
        "low_effort_extreme": round(low_effort_score * WEIGHT_LOW_EFFORT, 2),
        "duplicate_text": round(duplicate_score * WEIGHT_DUPLICATE_TEXT, 2),
        "employer_burst": round(burst_score * WEIGHT_EMPLOYER_BURST, 2),
    }
    confidence = round(sum(components.values()) / 100, 4)

    reasons = []
    if mismatch_score > 0.5:
        reasons.append("rating/sentiment mismatch")
    if low_effort_score:
        reasons.append("extreme rating with no substantiating comment")
    if duplicate_score > 0.7:
        reasons.append("near-duplicate text vs. another review from the same employer")
    if burst_score > 0.5:
        reasons.append("employer posted an unusual burst of reviews")

    return {
        "confidence": confidence,
        "sentiment_compound": sentiment_compound,
        "components": components,
        "reasons": reasons,
    }


def evaluate_review(review: Review) -> Optional[FraudFlag]:
    """Score a review, persist the result onto it, and log a FraudFlag if it clears threshold."""
    result = score_review_for_fraud(review)

    review.sentiment_score = (
        Decimal(str(round(result["sentiment_compound"], 4)))
        if result["sentiment_compound"] is not None
        else None
    )
    review.fraud_confidence = Decimal(str(result["confidence"]))
    review.is_flagged_fake = result["confidence"] >= FRAUD_THRESHOLD
    review.save(update_fields=["sentiment_score", "fraud_confidence", "is_flagged_fake"])

    if not review.is_flagged_fake:
        return None

    flag, _ = FraudFlag.objects.get_or_create(
        target_type=FraudFlag.TargetType.REVIEW,
        target_id=review.pk,
        defaults={
            "reason": ("; ".join(result["reasons"]) or "Automated fraud score above threshold")[:200],
            "confidence": Decimal(str(result["confidence"])),
        },
    )
    return flag


def scan_reviews(queryset=None) -> list[FraudFlag]:
    """Evaluate every review in the queryset (default: all reviews). Returns the flags raised."""
    reviews = queryset if queryset is not None else Review.objects.all()
    flags = []
    for review in reviews.select_related("employer", "worker"):
        flag = evaluate_review(review)
        if flag:
            flags.append(flag)
    return flags
