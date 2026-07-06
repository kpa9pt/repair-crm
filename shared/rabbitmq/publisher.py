# shared/rabbitmq.py
import pika
import json
import os


class RabbitMQPublisher:
    def __init__(self):
        self.host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.user = os.getenv("RABBITMQ_USER", "guest")
        self.password = os.getenv("RABBITMQ_PASS", "guest")
        self._connection = None
        self._channel = None

    def _connect(self):
        credentials = pika.PlainCredentials(self.user, self.password)
        parameters = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300,
        )
        self._connection = pika.BlockingConnection(parameters)
        self._channel = self._connection.channel()

        # Объявляем очередь (будет создана, если не существует)
        self._channel.queue_declare(queue="repair_events", durable=True)

    def publish(self, event_type: str, data: dict):
        """Публикует событие в RabbitMQ"""
        try:
            if not self._connection or self._connection.is_closed:
                self._connect()

            message = {"event_type": event_type, "data": data}

            self._channel.basic_publish(
                exchange="",
                routing_key="repair_events",
                body=json.dumps(message).encode(),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # persistent
                ),
            )
            print(f"✅ Published event: {event_type}")
        except Exception as e:
            print(f"❌ Failed to publish event: {e}")

    def close(self):
        if self._connection and not self._connection.is_closed:
            self._connection.close()


# Глобальный экземпляр (создается при импорте)
publisher = RabbitMQPublisher()
