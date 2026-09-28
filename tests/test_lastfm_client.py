import requests

import lastfm_client
from retry import run_with_retries as real_run_with_retries


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        data: dict,
    ):
        self.status_code = status_code
        self._data = data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP {self.status_code}",
                response=self,
            )

    def json(self):
        return self._data


def disable_retry_waiting(monkeypatch):
    def run_without_waiting(*args, **kwargs):
        kwargs["sleep_func"] = lambda delay: None
        return real_run_with_retries(*args, **kwargs)

    monkeypatch.setattr(
        lastfm_client,
        "run_with_retries",
        run_without_waiting,
    )


def test_request_lastfm_retries_temporary_api_error(
    monkeypatch,
):
    disable_retry_waiting(monkeypatch)

    responses = iter(
        [
            FakeResponse(
                200,
                {
                    "error": 16,
                    "message": "Temporary error",
                },
            ),
            FakeResponse(
                200,
                {
                    "toptags": {
                        "tag": [],
                    },
                },
            ),
        ]
    )
    request_count = 0

    def fake_get(*args, **kwargs):
        nonlocal request_count
        request_count += 1
        return next(responses)

    monkeypatch.setattr(
        lastfm_client.requests,
        "get",
        fake_get,
    )

    result = lastfm_client._request_lastfm(
        {
            "method": "artist.gettoptags",
        }
    )

    assert result == {
        "toptags": {
            "tag": [],
        },
    }
    assert request_count == 2


def test_request_lastfm_retries_server_error(
    monkeypatch,
):
    disable_retry_waiting(monkeypatch)

    responses = iter(
        [
            FakeResponse(503, {}),
            FakeResponse(
                200,
                {
                    "similarartists": {
                        "artist": [],
                    },
                },
            ),
        ]
    )
    request_count = 0

    def fake_get(*args, **kwargs):
        nonlocal request_count
        request_count += 1
        return next(responses)

    monkeypatch.setattr(
        lastfm_client.requests,
        "get",
        fake_get,
    )

    result = lastfm_client._request_lastfm(
        {
            "method": "artist.getsimilar",
        }
    )

    assert result == {
        "similarartists": {
            "artist": [],
        },
    }
    assert request_count == 2


def test_request_lastfm_does_not_retry_bad_request(
    monkeypatch,
):
    disable_retry_waiting(monkeypatch)

    request_count = 0

    def fake_get(*args, **kwargs):
        nonlocal request_count
        request_count += 1
        return FakeResponse(400, {})

    monkeypatch.setattr(
        lastfm_client.requests,
        "get",
        fake_get,
    )

    try:
        lastfm_client._request_lastfm(
            {
                "method": "invalid.method",
            }
        )
    except requests.HTTPError:
        pass
    else:
        raise AssertionError("Expected requests.HTTPError")

    assert request_count == 1


def test_request_lastfm_does_not_retry_permanent_api_error(
    monkeypatch,
):
    disable_retry_waiting(monkeypatch)

    request_count = 0

    def fake_get(*args, **kwargs):
        nonlocal request_count
        request_count += 1
        return FakeResponse(
            200,
            {
                "error": 6,
                "message": "Invalid parameters",
            },
        )

    monkeypatch.setattr(
        lastfm_client.requests,
        "get",
        fake_get,
    )

    try:
        lastfm_client._request_lastfm(
            {
                "method": "artist.getsimilar",
            }
        )
    except RuntimeError as error:
        assert "Invalid parameters" in str(error)
    else:
        raise AssertionError("Expected RuntimeError")

    assert request_count == 1


def test_get_artist_tags_uses_retryable_request_helper(
    monkeypatch,
):
    captured_params = {}

    monkeypatch.setattr(
        lastfm_client,
        "load_dotenv",
        lambda: None,
    )
    monkeypatch.setattr(
        lastfm_client.os,
        "getenv",
        lambda name: "test-api-key",
    )

    def fake_request(params):
        captured_params.update(params)

        return {
            "toptags": {
                "tag": [
                    {"name": " Techno "},
                    {"name": "HOUSE"},
                    {"name": ""},
                    {},
                ],
            },
        }

    monkeypatch.setattr(
        lastfm_client,
        "_request_lastfm",
        fake_request,
    )

    result = lastfm_client.get_artist_tags(
        "Test Artist",
        limit=10,
    )

    assert result == [
        "techno",
        "house",
    ]
    assert captured_params == {
        "method": "artist.gettoptags",
        "artist": "Test Artist",
        "api_key": "test-api-key",
        "format": "json",
        "autocorrect": 1,
    }


def test_get_similar_artists_uses_retryable_request_helper(
    monkeypatch,
):
    captured_params = {}

    monkeypatch.setattr(
        lastfm_client,
        "load_dotenv",
        lambda: None,
    )
    monkeypatch.setattr(
        lastfm_client.os,
        "getenv",
        lambda name: "test-api-key",
    )

    def fake_request(params):
        captured_params.update(params)

        return {
            "similarartists": {
                "artist": [
                    {
                        "name": "Cloonee",
                        "match": "0.85",
                    },
                    {
                        "name": "",
                        "match": "0.50",
                    },
                    {},
                ],
            },
        }

    monkeypatch.setattr(
        lastfm_client,
        "_request_lastfm",
        fake_request,
    )

    result = lastfm_client.get_similar_artists(
        "PAWSA",
        limit=20,
    )

    assert result == [
        {
            "name": "Cloonee",
            "similarity": 0.85,
        },
    ]
    assert captured_params == {
        "method": "artist.getsimilar",
        "artist": "PAWSA",
        "api_key": "test-api-key",
        "format": "json",
        "autocorrect": 1,
        "limit": 20,
    }
