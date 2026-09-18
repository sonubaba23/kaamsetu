from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.jobs.models import Review
from apps.ml_models.fraud_detection import evaluate_review
from apps.ml_models.skill_verification import verify_portfolio_image
from apps.workers.models import PortfolioImage


@receiver(post_save, sender=Review)
def scan_new_review_for_fraud(sender, instance, created, **kwargs):
    """Run the fraud scan the moment a review is created.

    evaluate_review() itself calls instance.save(update_fields=...), which
    re-fires this signal with created=False — the guard below is what
    stops that from recursing.
    """
    if not created:
        return
    evaluate_review(instance)


@receiver(post_save, sender=PortfolioImage)
def verify_new_portfolio_image(sender, instance, created, **kwargs):
    """Run skill verification the moment a portfolio image is uploaded.

    By post_save the FileField has already written the image to storage, so
    it's safe to open — except when a caller creates the row before
    attaching a file (a two-step create-then-upload pattern), which is why
    the `instance.image` check below is needed alongside the `created`
    guard that stops verify_portfolio_image()'s own save() from recursing.
    """
    if not created or not instance.image:
        return
    verify_portfolio_image(instance)
