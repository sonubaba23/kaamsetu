from django.core.management.base import BaseCommand, CommandError

from apps.workers.models import PortfolioImage
from apps.ml_models.skill_verification import verify_portfolio_image


class Command(BaseCommand):
    help = "Run CNN skill verification + quality grading over ungraded portfolio images."

    def add_arguments(self, parser):
        parser.add_argument(
            "--image-id",
            type=int,
            help="Verify only the portfolio image with this primary key.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Re-verify every portfolio image, not just ungraded ones.",
        )

    def handle(self, *args, **options):
        image_id = options.get("image_id")

        if image_id is not None:
            try:
                images = [PortfolioImage.objects.select_related("worker").get(pk=image_id)]
            except PortfolioImage.DoesNotExist as exc:
                raise CommandError(f"No portfolio image with id={image_id}") from exc
        elif options["all"]:
            images = list(PortfolioImage.objects.select_related("worker").order_by("id"))
        else:
            images = list(
                PortfolioImage.objects.filter(quality_grade=PortfolioImage.QualityGrade.UNGRADED)
                .select_related("worker")
                .order_by("id")
            )

        total = len(images)
        if total == 0:
            self.stdout.write("No portfolio images to verify.")
            return

        flagged = 0
        for index, image in enumerate(images, start=1):
            verify_portfolio_image(image)
            marker = "FLAGGED" if image.is_flagged else "ok"
            self.stdout.write(
                f"[{index}/{total}] image #{image.pk} ({image.worker}) -> "
                f"quality={image.quality_grade}, trade={image.predicted_trade or 'n/a'} ({marker})"
            )
            if image.is_flagged:
                flagged += 1

        self.stdout.write(self.style.SUCCESS(f"Verified {total} image(s), flagged {flagged}."))
