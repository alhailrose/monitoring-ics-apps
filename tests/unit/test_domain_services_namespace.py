from monitoring_hub.domain.services import (
    check_executor,
    customer_service,
    session_health,
)


def test_domain_services_namespace_imports():
    assert check_executor is not None
    assert customer_service is not None
    assert session_health is not None
