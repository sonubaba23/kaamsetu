from django.core.management.base import BaseCommand, CommandError

from apps.ml_models.services import update_worker_trust_score
from apps.workers.models import Worker


class Command(BaseCommand):
    help = "Recompute trust scores for all workers (or a single worker) and log the results."

    def add_arguments(self, parser):
        parser.add_argument(
            "--worker-id",
            type=int,
            help="Recompute only the worker with this primary key, instead of all workers.",
        )

    def handle(self, *args, **options):
        worker_id = options.get("worker_id")

        if worker_id is not None:
            try:
                workers = [Worker.objects.get(pk=worker_id)]
            except Worker.DoesNotExist as exc:
                raise CommandError(f"No worker with id={worker_id}") from exc
        else:
            workers = list(Worker.objects.order_by("id"))

        total = len(workers)
        if total == 0:
            self.stdout.write("No workers to process.")
            return

        for index, worker in enumerate(workers, start=1):
            log = update_worker_trust_score(worker)
            self.stdout.write(f"[{index}/{total}] {worker} -> {log.score}")

        self.stdout.write(self.style.SUCCESS(f"Recomputed trust scores for {total} worker(s)."))
