import pytest
from geoip2.database import Reader


@pytest.fixture(scope="session")
def ip_reader():
    with Reader("./GeoLite2-Country.mmdb") as reader:
        yield reader
