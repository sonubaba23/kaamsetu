from django.core.management.base import BaseCommand, CommandError

from apps.jobs.models import Review
from apps.ml_models.fraud_detection import evaluate_review


class Command(BaseCommand):
    help = "Scan reviews for fraud signals, flagging suspicious ones for manual review."

    def add_arguments(self, parser):
        parser.add_argument(
            "--review-id",
            type=int,
            help="Scan only the review with this primary key, instead of all reviews.",
        )

    def handle(self, *args, **options):
        review_id = options.get("review_id")

        if review_id is not None:
            try:
                reviews = [Review.objects.get(pk=review_id)]
            except Review.DoesNotExist as exc:
                raise CommandError(f"No review with id={review_id}") from exc
        else:
            reviews = list(Review.objects.select_related("employer", "worker").order_by("id"))

        total = len(reviews)
        if total == 0:
            self.stdout.write("No reviews to scan.")
            return

        flagged = 0
        for index, review in enumerate(reviews, start=1):
            flag = evaluate_review(review)
            marker = f"FLAGGED ({flag.confidence})" if flag else "ok"
            self.stdout.write(f"[{index}/{total}] review #{review.pk} ({review.worker}) -> {marker}")
            if flag:
                flagged += 1

        self.stdout.write(self.style.SUCCESS(f"Scanned {total} review(s), flagged {flagged}."))
