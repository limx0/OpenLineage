import os
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
@patch("openlineage.prefect.adapter.OpenLineageAdapter")
@patch("openlineage.client.client.OpenLineageClient")
def mock_open_lineage_client(client, client2):
    # client.session = MagicMock()
    # client2.session = MagicMock()
    os.environ['PREFECT_ORION_DATABASE_CONNECTION_URL'] = "sqlite+memory:////"
    return client
