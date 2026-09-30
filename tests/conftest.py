import pytest


def pytest_addoption(parser):
    parser.addoption("--run-network", action="store_true", default=False,
                     help="also run tests that call the live Handschriftenportal API")


def pytest_configure(config):
    config.addinivalue_line("markers", "network: test calls the live HSP API (needs --run-network)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-network"):
        return
    skip = pytest.mark.skip(reason="needs --run-network")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)
