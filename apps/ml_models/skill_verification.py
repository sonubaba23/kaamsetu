"""CNN-based skill verification for worker portfolio images.

Two independent signals are written back onto each PortfolioImage:

- predicted_trade / prediction_confidence: which trade the photo looks
  like (mason work, plumbing, etc.), from a CNN. Training a CNN needs a
  labeled dataset this marketplace doesn't have on day one, so
  build_skill_classifier() defines a real, trainable architecture
  (MobileNetV2 transfer learning), and inference only runs once a
  trained weights file actually exists at settings.ML_MODELS_DIR. Until
  then, predicted_trade stays None rather than guessing.

- quality_grade: a deterministic image-quality heuristic (resolution +
  a Laplacian-style sharpness estimate), which needs no training data
  and so works from day one, independent of whether the CNN is trained.

is_flagged fires only when the CNN confidently (see
MISMATCH_CONFIDENCE_THRESHOLD) predicts a trade that doesn't match the
worker's own declared skill_category — never on the quality heuristic
alone, and never when the CNN is unavailable (no evidence, no flag).
"""

import json
import logging
from typing import Optional

import numpy as np
from django.conf import settings
from PIL import Image

from apps.core.models import SkillCategory
from apps.workers.models import PortfolioImage

logger = logging.getLogger(__name__)

IMAGE_SIZE = (224, 224)
MODEL_PATH = settings.ML_MODELS_DIR / "skill_classifier.keras"
CLASS_INDEX_PATH = settings.ML_MODELS_DIR / "skill_classifier_classes.json"

MISMATCH_CONFIDENCE_THRESHOLD = 0.6

# Quality heuristic thresholds.
LOW_RES_PIXELS = 300 * 300
HIGH_RES_PIXELS = 1000 * 1000
SHARPNESS_LOW = 2.0
SHARPNESS_HIGH = 10.0

_model_cache = None
_class_slugs_cache = None


def build_skill_classifier(num_classes: int):
    """Define the trainable CNN: a frozen MobileNetV2 backbone + a small trade-classification head.

    This is the architecture a future training script should build, fit on a
    labeled portfolio-image dataset, and save to MODEL_PATH plus the class
    order to CLASS_INDEX_PATH. It is not invoked by inference.
    """
    from tensorflow.keras import layers, models
    from tensorflow.keras.applications import MobileNetV2

    base = MobileNetV2(input_shape=(*IMAGE_SIZE, 3), include_top=False, weights="imagenet")
    base.trainable = False

    model = models.Sequential(
        [
            base,
            layers.GlobalAveragePooling2D(),
            layers.Dropout(0.2),
            layers.Dense(128, activation="relu"),
            layers.Dropout(0.2),
            layers.Dense(num_classes, activation="softmax"),
        ]
    )
    model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
    return model


def _load_model():
    """Lazily load the trained model and its class order, if they exist on disk."""
    global _model_cache, _class_slugs_cache
    if _model_cache is not None:
        return _model_cache, _class_slugs_cache

    if not MODEL_PATH.exists() or not CLASS_INDEX_PATH.exists():
        logger.info("No trained skill classifier at %s; skipping trade prediction.", MODEL_PATH)
        return None, None

    from tensorflow.keras.models import load_model

    _model_cache = load_model(MODEL_PATH)
    _class_slugs_cache = json.loads(CLASS_INDEX_PATH.read_text())
    return _model_cache, _class_slugs_cache


def _preprocess_image(pil_image: Image.Image) -> np.ndarray:
    from tensorflow.keras.applications.mobilenet_v2 import preprocess_input

    resized = pil_image.convert("RGB").resize(IMAGE_SIZE)
    array = np.asarray(resized, dtype=np.float32)
    return preprocess_input(array[np.newaxis, ...])


def _predict_trade(pil_image: Image.Image) -> tuple[Optional[SkillCategory], Optional[float]]:
    model, class_slugs = _load_model()
    if model is None:
        return None, None

    batch = _preprocess_image(pil_image)
    probabilities = model.predict(batch, verbose=0)[0]
    best_index = int(np.argmax(probabilities))
    confidence = float(probabilities[best_index])
    slug = class_slugs[best_index]

    try:
        predicted_trade = SkillCategory.objects.get(slug=slug)
    except SkillCategory.DoesNotExist:
        logger.warning("Skill classifier predicted unknown slug %r", slug)
        return None, None

    return predicted_trade, confidence


def _sharpness_score(gray: np.ndarray) -> float:
    """A cheap Laplacian-style high-frequency energy estimate: higher = sharper."""
    vertical = np.diff(gray, n=2, axis=0)
    horizontal = np.diff(gray, n=2, axis=1)
    return float(np.abs(vertical).mean() + np.abs(horizontal).mean())


def _grade_quality(pil_image: Image.Image) -> str:
    width, height = pil_image.size
    pixels = width * height

    gray = np.asarray(pil_image.convert("L"), dtype=np.float32)
    sharpness = _sharpness_score(gray)

    resolution_score = np.clip(
        (pixels - LOW_RES_PIXELS) / (HIGH_RES_PIXELS - LOW_RES_PIXELS), 0.0, 1.0
    )
    sharpness_score = np.clip(
        (sharpness - SHARPNESS_LOW) / (SHARPNESS_HIGH - SHARPNESS_LOW), 0.0, 1.0
    )
    combined = 0.5 * resolution_score + 0.5 * sharpness_score

    if combined >= 0.66:
        return PortfolioImage.QualityGrade.HIGH
    if combined >= 0.33:
        return PortfolioImage.QualityGrade.MEDIUM
    return PortfolioImage.QualityGrade.LOW


def verify_portfolio_image(portfolio_image: PortfolioImage) -> PortfolioImage:
    """Run skill verification for one portfolio image and persist the results."""
    with Image.open(portfolio_image.image) as pil_image:
        pil_image.load()
        quality_grade = _grade_quality(pil_image)
        predicted_trade, confidence = _predict_trade(pil_image)

    is_flagged = (
        predicted_trade is not None
        and confidence is not None
        and confidence >= MISMATCH_CONFIDENCE_THRESHOLD
        and predicted_trade.pk != portfolio_image.worker.skill_category_id
    )

    portfolio_image.predicted_trade = predicted_trade
    portfolio_image.prediction_confidence = round(confidence, 4) if confidence is not None else None
    portfolio_image.quality_grade = quality_grade
    portfolio_image.is_flagged = is_flagged
    portfolio_image.save(
        update_fields=["predicted_trade", "prediction_confidence", "quality_grade", "is_flagged"]
    )
    return portfolio_image


def verify_pending_images(queryset=None) -> list[PortfolioImage]:
    """Run verification over every ungraded portfolio image (default), or a given queryset."""
    images = queryset if queryset is not None else PortfolioImage.objects.filter(
        quality_grade=PortfolioImage.QualityGrade.UNGRADED
    )
    return [verify_portfolio_image(image) for image in images.select_related("worker")]
