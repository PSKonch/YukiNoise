import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from yn.modules.auth.auth import get_current_user
from yn.modules.tracks.deps import get_track_service
from yn.modules.tracks.dto import TrackUploadQueuedDTO
from yn.modules.tracks.route import router
from yn.modules.users.dto import UserDTO


@pytest.mark.parametrize("clear", [False, True])
def test_patch_accepts_features_without_other_fields(clear: bool) -> None:
    async def run() -> None:
        guest_id = uuid4()
        ids = [] if clear else [guest_id]
        track = SimpleNamespace(
            id=uuid4(),
            release_id=uuid4(),
            title="Snow",
            track_number_in_release=1,
            genres=[],
            duration_seconds=120,
            path="snow.mp3",
            featured_artists=[]
            if clear
            else [SimpleNamespace(id=guest_id, displayed_name="Guest")],
        )
        service = SimpleNamespace(update_track=AsyncMock(return_value=track))
        user = UserDTO(
            id=uuid4(),
            email="owner@test.example",
            role="user",
            is_active=True,
            artist_id=uuid4(),
        )
        app = FastAPI()
        app.include_router(router)

        async def current_user() -> UserDTO:
            return user

        async def track_service() -> SimpleNamespace:
            return service

        app.dependency_overrides[get_current_user] = current_user
        app.dependency_overrides[get_track_service] = track_service
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/tracks/{track.id}",
                json={"featured_artist_ids": [str(artist_id) for artist_id in ids]},
            )

        assert response.status_code == 200
        assert service.update_track.await_args.kwargs["featured_artist_ids"] == ids
        assert [artist["id"] for artist in response.json()["featured_artists"]] == [
            str(artist_id) for artist_id in ids
        ]

    asyncio.run(run())


def test_upload_accepts_repeated_featured_artist_form_fields() -> None:
    async def run() -> None:
        ids = [uuid4(), uuid4()]
        release_id = uuid4()
        service = SimpleNamespace(
            upload_track=AsyncMock(
                return_value=TrackUploadQueuedDTO(
                    track_id=uuid4(),
                    release_id=release_id,
                    title="Snow",
                    track_number_in_release=1,
                    featured_artist_ids=ids,
                )
            )
        )
        user = UserDTO(
            id=uuid4(),
            email="owner@test.example",
            role="user",
            is_active=True,
            artist_id=uuid4(),
        )
        app = FastAPI()
        app.include_router(router)

        async def current_user() -> UserDTO:
            return user

        async def track_service() -> SimpleNamespace:
            return service

        app.dependency_overrides[get_current_user] = current_user
        app.dependency_overrides[get_track_service] = track_service
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/tracks/",
                data={
                    "release_id": str(release_id),
                    "title": "Snow",
                    "track_number_in_release": "1",
                    "featured_artist_ids": [str(artist_id) for artist_id in ids],
                },
                files={"file": ("snow.mp3", b"audio", "audio/mpeg")},
            )

        assert response.status_code == 200
        assert service.upload_track.await_args.kwargs["featured_artist_ids"] == ids
        assert response.json()["featured_artist_ids"] == [
            str(artist_id) for artist_id in ids
        ]

    asyncio.run(run())
