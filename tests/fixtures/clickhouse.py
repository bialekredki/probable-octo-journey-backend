from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture
def mocked_clickhouse():
    with patch("clickhouse_connect.driver.client.Client", MagicMock()) as mocked:
        yield mocked
