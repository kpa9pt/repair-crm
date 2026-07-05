from shared.enums import Urgency, RequestStatus


class TestEnums:
    """Тесты enum классов"""

    def test_urgency_enum(self):
        """Проверка enum Urgency"""
        # Проверка значений
        assert Urgency.LOW.value == "low"
        assert Urgency.NORMAL.value == "normal"
        assert Urgency.HIGH.value == "high"
        assert Urgency.CRITICAL.value == "critical"

        # Проверка строкового представления
        assert str(Urgency.LOW) == "low"
        assert str(Urgency.NORMAL) == "normal"
        assert str(Urgency.HIGH) == "high"
        assert str(Urgency.CRITICAL) == "critical"

        # Проверка что все значения уникальны
        values = [e.value for e in Urgency]
        assert len(values) == len(set(values))

    def test_request_status_enum(self):
        """Проверка enum RequestStatus"""
        # Проверка значений
        assert RequestStatus.NEW.value == "new"
        assert RequestStatus.IN_PROGRESS.value == "in_progress"
        assert RequestStatus.WAITING_PARTS.value == "waiting_parts"
        assert RequestStatus.DIAGNOSTICS.value == "diagnostics"
        assert RequestStatus.WAITING_APPROVAL.value == "waiting_approval"
        assert RequestStatus.DONE.value == "done"

        # Проверка строкового представления
        assert str(RequestStatus.NEW) == "new"
        assert str(RequestStatus.IN_PROGRESS) == "in_progress"
        assert str(RequestStatus.WAITING_PARTS) == "waiting_parts"
        assert str(RequestStatus.DIAGNOSTICS) == "diagnostics"
        assert str(RequestStatus.WAITING_APPROVAL) == "waiting_approval"
        assert str(RequestStatus.DONE) == "done"

        # Проверка что все значения уникальны
        values = [e.value for e in RequestStatus]
        assert len(values) == len(set(values))
