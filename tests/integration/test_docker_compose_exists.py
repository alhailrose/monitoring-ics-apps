from pathlib import Path


def test_docker_compose_exists_for_single_server_stack() -> None:
    assert Path("infra/docker/docker-compose.yml").exists()
