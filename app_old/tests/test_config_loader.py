import pytest
import os
from config_loader import SecureConfigLoader

@pytest.fixture
def create_test_config(tmp_path):
    config_content = """
app:
  name: TestApp
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_content)
    return str(config_file)

def test_config_loader_finds_config(create_test_config):
    """Test that the loader can find the config file."""
    original_cwd = os.getcwd()
    try:
        os.chdir(os.path.dirname(create_test_config))
        loader = SecureConfigLoader()
        config = loader.load_config()
        assert config is not None
        assert config['app']['name'] == 'TestApp'
    finally:
        os.chdir(original_cwd)
