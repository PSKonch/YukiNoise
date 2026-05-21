from taskiq_aio_pika import AioPikaBroker

from yn.shared.settings import settings

broker = AioPikaBroker(settings.rabbitmq_url)
