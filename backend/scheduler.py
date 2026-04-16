"""
scheduler.py
Runs the full scrape → analyze → aggregate pipeline every 6 hours.
Uses APScheduler. Run alongside app.py or independently.

Usage: python -m backend.scheduler
"""

import logging
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCHEDULER] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/scheduler.log"),
    ]
)
log = logging.getLogger(__name__)


def run_full_pipeline():
    """Execute all pipeline stages in order."""
    start = datetime.utcnow()
    log.info("=" * 50)
    log.info(f"Pipeline START: {start.isoformat()}")
    log.info("=" * 50)

    stages = [
        ("YouTube scraper",     "scraper.youtube_scraper"),
        ("Genius scraper",      "scraper.genius_scraper"),
        ("Comment scraper",     "scraper.comment_scraper"),
        ("Emotion engine",      "analyzer.emotion_engine"),
        ("City aggregator",     "analyzer.city_aggregator"),
    ]

    for name, module_path in stages:
        log.info(f"Running: {name}...")
        try:
            mod = __import__(module_path, fromlist=["run"])
            mod.run()
            log.info(f"  ✓ {name} complete")
        except Exception as e:
            log.error(f"  ✗ {name} FAILED: {e}")
            # Continue to next stage rather than abort
            continue

    elapsed = (datetime.utcnow() - start).seconds
    log.info(f"Pipeline DONE in {elapsed}s")


def main():
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")

    # Run immediately on startup
    log.info("Running pipeline immediately on startup...")
    run_full_pipeline()

    # Then every 6 hours
    scheduler.add_job(
        run_full_pipeline,
        trigger=IntervalTrigger(hours=6),
        id="mood_pipeline",
        name="Full scrape + analyze pipeline",
        replace_existing=True,
    )

    log.info("Scheduler started. Pipeline runs every 6 hours (IST).")
    log.info("Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
