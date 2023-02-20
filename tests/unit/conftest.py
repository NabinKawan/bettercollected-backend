from unittest import mock

import pytest
from backend.app import get_application


@pytest.fixture
def asgi_app():
    app = mock.Mock(spec=get_application(is_test_mode=True))
    yield app
    del app
