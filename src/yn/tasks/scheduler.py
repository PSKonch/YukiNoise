from taskiq import TaskiqScheduler
from taskiq.schedule_sources.label_based import LabelScheduleSource

import yn.tasks  # noqa: F401
from yn.tasks.broker import broker

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
