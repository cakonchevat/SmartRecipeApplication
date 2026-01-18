# smart_recipe_app/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import PantryScan, PantryScanDetection
from .ml_scan import detect_ingredients_with_claude, match_label_to_ingredient


@shared_task(bind=True, max_retries=3)
def process_pantry_scan(self, scan_id: int):
    """
    Async task to process a pantry scan.
    """
    scan = None
    try:
        scan = PantryScan.objects.get(id=scan_id)
        scan.status = PantryScan.Status.PROCESSING
        scan.error_message = ""
        scan.save(update_fields=["status", "error_message"])

        # Run ML detection
        detections = detect_ingredients_with_claude(scan.image.path)
        scan.raw_output = detections
        scan.save(update_fields=["raw_output"])

        # Clear old detections (avoid duplicates)
        scan.detections.all().delete()

        # Create detection records
        for det in detections:
            matched_ingredient = match_label_to_ingredient(det.get("label", ""))

            PantryScanDetection.objects.create(
                scan=scan,
                label=det.get("label", ""),
                confidence=float(det.get("confidence", 0.6)),
                matched_ingredient=matched_ingredient,
                quantity_guess=float(det.get("quantity_guess", 1.0) or 1.0),
                status=PantryScanDetection.ReviewStatus.PENDING,
            )

        scan.status = PantryScan.Status.DONE
        scan.processed_at = timezone.now()
        scan.save(update_fields=["status", "processed_at"])

    except Exception as e:
        # If scan wasn't found, just raise the error
        if scan is None:
            raise

        scan.status = PantryScan.Status.FAILED
        scan.error_message = str(e)
        scan.save(update_fields=["status", "error_message"])

        # Retry on Claude API errors
        if "Claude API error" in str(e):
            raise self.retry(exc=e, countdown=60)
