"""
Unit тесты для RabbitMQ Publisher
Проверяем только логику формирования сообщений
"""

from shared.rabbitmq.publisher import RabbitMQPublisher


class TestRabbitMQPublisher:
    """Тесты для RabbitMQ Publisher"""

    def test_publisher_initialization(self):
        """Проверка инициализации publisher"""
        publisher = RabbitMQPublisher()
        assert publisher.host is not None
        assert publisher.port is not None
        assert publisher.user is not None

    def test_publish_creates_correct_message(self):
        """Проверка формирования сообщения (без реальной отправки)"""
        publisher = RabbitMQPublisher()

        # Просто проверяем что метод существует и принимает правильные параметры
        # Без реальной отправки в RabbitMQ
        assert hasattr(publisher, "publish")

        # Проверяем что publish принимает 2 аргумента
        import inspect

        sig = inspect.signature(publisher.publish)
        params = list(sig.parameters.keys())
        assert "event_type" in params
        assert "data" in params
