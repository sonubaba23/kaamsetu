from django.core.management.base import BaseCommand, CommandError

from apps.core.models import SkillCategory
from apps.jobs.models import Job
from apps.ml_models.demand_forecasting import FORECAST_PERIODS, update_all_forecasts, update_forecast


class Command(BaseCommand):
    help = "Generate demand forecasts for every skill/city pair with job history (or one pair)."

    def add_arguments(self, parser):
        parser.add_argument("--skill", help="Skill category slug. Requires --city.")
        parser.add_argument("--city", help="City name. Requires --skill.")
        parser.add_argument(
            "--periods", type=int, default=FORECAST_PERIODS, help="Weeks ahead to forecast."
        )

    def handle(self, *args, **options):
        skill_slug = options.get("skill")
        city = options.get("city")
        periods = options["periods"]

        if bool(skill_slug) != bool(city):
            raise CommandError("--skill and --city must be given together.")

        if skill_slug:
            try:
                skill_category = SkillCategory.objects.get(slug=skill_slug)
            except SkillCategory.DoesNotExist as exc:
                raise CommandError(f"No skill category with slug={skill_slug}") from exc
            forecasts = update_forecast(skill_category, city, periods)
        else:
            if not Job.objects.exists():
                self.stdout.write("No jobs posted yet — nothing to forecast from.")
                return
            forecasts = update_all_forecasts(periods)

        if not forecasts:
            self.stdout.write("No forecasts generated.")
            return

        for f in forecasts:
            self.stdout.write(
                f"{f.skill_category} @ {f.city}: {f.period_start} to {f.period_end} "
                f"-> {f.predicted_demand} ({f.confidence_lower}-{f.confidence_upper}) [{f.model_version}]"
            )

        self.stdout.write(self.style.SUCCESS(f"Generated {len(forecasts)} forecast(s)."))
