"""
Holds global celery application state and startup / shutdown handlers.
"""
from celery import Celery
from celery.app import app_or_default
from celery.signals import (
    worker_process_init,
    worker_process_shutdown,
)

from ichnaea.async.config import (
    configure_celery,
    init_worker,
    shutdown_worker,
)
from ichnaea.config import read_config


@worker_process_init.connect
def init_worker_process(signal, sender, **kw):  # pragma: no cover
    """
    Called automatically when `celery worker` is started. This is executed
    inside each forked worker process.

    Reads the app config and calls :func:`ichnaea.async.config.init_worker`.
    """
    # get the app in the current worker process
    celery_app = app_or_default()
    conf = read_config()
    init_worker(celery_app, conf)


@worker_process_shutdown.connect
def shutdown_worker_process(signal, sender, **kw):  # pragma: no cover
    """
    Called automatically when `celery worker` is stopped. This is executed
    inside each forked worker process.

    Calls :func:`ichnaea.async.config.shutdown_worker`.
    """
    celery_app = app_or_default()
    shutdown_worker(celery_app)


celery_app = Celery('ichnaea.async.app')

configure_celery(celery_app)
