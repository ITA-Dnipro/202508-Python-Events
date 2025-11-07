from celery import Celery
from datetime import timedelta
import os

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/2") 
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/3")
celery_app = Celery(
    'event_scheduler',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['events_app.tasks'] 
)

celery_app.conf.update(
    beat_schedule={
        'generate-recurring-events-daily': {
            'task': 'tasks.generate_recurring_events', 
            'schedule': timedelta(days=1), 
            'args': (),
        },
    },
    timezone='Europe/Kyiv', 
)