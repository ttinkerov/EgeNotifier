from unittest.mock import MagicMock

import pytest

from egebot.config import Settings
from egebot.core.rustest import RustestClient
from egebot.domain.exam_snapshot import FetchScoresStatus


class _FakeResponse:
    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self._payload = payload

    async def json(self, content_type: str | None = None) -> object:
        return self._payload

    async def __aenter__(self) -> "_FakeResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


@pytest.mark.asyncio
async def test_fetch_scores_unauthorized_http() -> None:
    settings = Settings(
        TG_API_TOKEN="1:test",
        DB_NAME="egebot",
        DB_USER="postgres",
        DB_PASS="postgres",
    )
    client = RustestClient(settings)
    session = MagicMock()
    session.get.return_value = _FakeResponse(401, {})
    client._http = session

    result = await client.fetch_scores("token", attempts=1)
    assert result.status is FetchScoresStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_fetch_scores_null_result_is_unauthorized() -> None:
    settings = Settings(
        TG_API_TOKEN="1:test",
        DB_NAME="egebot",
        DB_USER="postgres",
        DB_PASS="postgres",
    )
    client = RustestClient(settings)
    session = MagicMock()
    session.get.return_value = _FakeResponse(200, {"Result": None})
    client._http = session

    result = await client.fetch_scores("token", attempts=1)
    assert result.status is FetchScoresStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_fetch_scores_ok() -> None:
    settings = Settings(
        TG_API_TOKEN="1:test",
        DB_NAME="egebot",
        DB_USER="postgres",
        DB_PASS="postgres",
    )
    client = RustestClient(settings)
    session = MagicMock()
    session.get.return_value = _FakeResponse(
        200,
        {
            "Result": {
                "Exams": [
                    {
                        "ExamId": 1,
                        "Subject": "Русский язык",
                        "ExamDate": "2025-05-27",
                        "IsComposition": False,
                        "IsHidden": False,
                        "HasResult": True,
                        "TestMark": 90,
                        "MinMark": 36,
                    }
                ]
            }
        },
    )
    client._http = session

    result = await client.fetch_scores("token", attempts=1)
    assert result.status is FetchScoresStatus.OK
    assert len(result.exams) == 1
    assert result.exams[0].mark == 90
