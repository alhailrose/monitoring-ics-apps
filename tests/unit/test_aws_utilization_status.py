from backend.checks.generic.aws_utilization_status import classify_instance_status


def test_classify_instance_status_critical_cpu():
    status = classify_instance_status(
        cpu_peak=90.0, memory_peak=20.0, disk_free_min=70.0
    )
    assert status == "CRITICAL"


def test_classify_instance_status_warning_disk_free():
    status = classify_instance_status(
        cpu_peak=40.0, memory_peak=50.0, disk_free_min=18.0
    )
    assert status == "WARNING"


def test_classify_instance_status_partial_data_when_memory_missing():
    status = classify_instance_status(
        cpu_peak=30.0, memory_peak=None, disk_free_min=50.0
    )
    assert status == "PARTIAL_DATA"


def test_classify_instance_status_normal_when_all_safe():
    status = classify_instance_status(
        cpu_peak=35.0, memory_peak=45.0, disk_free_min=55.0
    )
    assert status == "NORMAL"
