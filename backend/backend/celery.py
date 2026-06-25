"""
Celery config — background tasks for MT5 polling and indicator computation.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

app = Celery("backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Periodic tasks (Celery Beat)
app.conf.beat_schedule = {
    "poll-mt5-ticks": {
        "task": "market.tasks.poll_mt5_ticks",
        "schedule": 1.0,  # every 1 second — live prices
    },
    "poll-mt5-candles": {
        "task": "market.tasks.poll_mt5_candles",
        "schedule": 5.0,  # every 5 seconds — candle data
    },
    "compute-indicators": {
        "task": "market.tasks.compute_indicators",
        "schedule": 5.0,  # every 5 seconds — indicators + trade score
    },
    "scan-patterns": {
        "task": "market.tasks.scan_patterns",
        "schedule": 10.0,  # every 10 seconds — pattern overlay
    },
}
