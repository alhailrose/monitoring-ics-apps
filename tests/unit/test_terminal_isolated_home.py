from pathlib import Path

from backend.interfaces.api.routes import terminal


def test_prepare_isolated_aws_home_links_cli_cache_to_user_cache(tmp_path):
    user_dir, user_config, user_cache, isolated_home = (
        terminal._prepare_isolated_aws_home(
            "bagus_faqihuddin",
            base_home=str(tmp_path),
        )
    )

    assert user_dir == str(tmp_path / ".aws" / "users" / "bagus_faqihuddin")
    assert Path(user_cache).is_dir()

    home_aws = Path(isolated_home) / ".aws"
    config_link = home_aws / "config"
    cache_link = home_aws / "sso" / "cache"

    assert config_link.is_symlink()
    assert config_link.resolve() == Path(user_config)
    assert cache_link.is_symlink()
    assert cache_link.resolve() == Path(user_cache)
