"""Testes do contrato HTTP — um por item do Definition of Done."""

from __future__ import annotations

import re

import pytest

ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def ingest(client, counts: dict[str, int], camera_id: str = "CAM-01"):
    return client.post(
        "/ingest",
        json={
            "camera_id": camera_id,
            "captured_at": "2020-01-01T00:00:00Z",
            "regions": [
                {"region_id": region_id, "person_count": count}
                for region_id, count in counts.items()
            ],
        },
    )


def space_by_id(payload: list[dict], space_id: str) -> dict:
    return next(item for item in payload if item["id"] == space_id)


# --- health -----------------------------------------------------------------


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- structure --------------------------------------------------------------


def test_structure_matches_contract(client):
    body = client.get("/structure").json()

    assert body["campus"] == {"id": "unifei-itabira", "name": "UNIFEI — Campus Itabira"}

    building = body["buildings"][0]
    assert building["id"] == "bld-1"
    assert building["code"] == "P1"

    floor = building["floors"][0]
    assert floor["id"] == "bld-1-f2"
    assert floor["level"] == 2

    assert floor["spaces"][0] == {
        "id": "room-101",
        "name": "Sala 101",
        "code": "101",
        "type": "classroom",
    }


# --- ingest -----------------------------------------------------------------


def test_ingest_saves_snapshot(client):
    response = ingest(client, {"ROI-01": 12, "ROI-02": 3})
    assert response.status_code == 200
    assert response.json() == {"accepted": 2, "ignored": []}

    occupancy = client.get("/spaces/room-101/occupancy").json()
    assert occupancy["person_count"] == 12
    assert occupancy["occupancy_rate"] == 0.3


def test_ingest_unknown_camera_is_404(client):
    response = ingest(client, {"ROI-01": 1}, camera_id="CAM-99")
    assert response.status_code == 404
    assert response.json() == {"detail": "camera not found"}


def test_ingest_unknown_region_goes_to_ignored(client):
    response = ingest(client, {"ROI-01": 5, "ROI-99": 7})
    assert response.status_code == 200
    assert response.json() == {"accepted": 1, "ignored": ["ROI-99"]}


def test_ingest_negative_count_is_422(client):
    response = client.post(
        "/ingest",
        json={"camera_id": "CAM-01", "regions": [{"region_id": "ROI-01", "person_count": -1}]},
    )
    assert response.status_code == 422


def test_ingest_uses_server_time_not_client_time(client):
    """O captured_at do corpo (2020) é só log; a resposta traz o horário atual."""
    ingest(client, {"ROI-01": 4})
    captured_at = client.get("/spaces/room-101/occupancy").json()["captured_at"]
    assert ISO_Z.match(captured_at)
    assert not captured_at.startswith("2020")


# --- status -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("person_count", "expected"),
    [
        (0, "empty"),
        (24, "normal"),  # 24 < 0.7 * 35 = 24.5
        (25, "high"),  # 24.5 <= 25 <= 35
        (35, "high"),  # no limite ainda é high
        (36, "over_limit"),  # acima de operational_limit
    ],
)
def test_status_thresholds(client, person_count, expected):
    ingest(client, {"ROI-01": person_count})
    assert client.get("/spaces/room-101/occupancy").json()["status"] == expected


def test_space_without_snapshot_is_no_data(client):
    space = space_by_id(client.get("/spaces").json(), "room-102")
    assert space["status"] == "no_data"
    assert space["person_count"] is None
    assert space["occupancy_rate"] is None
    assert space["captured_at"] is None


def test_silence_over_30s_turns_into_no_data(client, age_camera):
    ingest(client, {"ROI-01": 20})

    before = space_by_id(client.get("/spaces").json(), "room-101")
    assert before["status"] == "normal"
    assert before["person_count"] == 20

    age_camera("CAM-01", seconds=31)

    after = space_by_id(client.get("/spaces").json(), "room-101")
    assert after["status"] == "no_data"
    assert after["person_count"] is None
    assert after["occupancy_rate"] is None
    # O horário do último snapshot continua visível: o dado sumiu, o silêncio é datado.
    assert ISO_Z.match(after["captured_at"])


def test_disabled_roi_stops_reporting_even_with_the_camera_online(client):
    """A câmera segue online pelas outras ROIs; o space parado não pode fingir atual."""
    from app.database import SessionLocal
    from app.models import CameraRegion

    ingest(client, {"ROI-01": 20, "ROI-02": 5})
    assert space_by_id(client.get("/spaces").json(), "room-101")["status"] == "normal"

    with SessionLocal() as session:
        session.get(CameraRegion, "ROI-01").enabled = False
        session.commit()

    ingest(client, {"ROI-01": 20, "ROI-02": 5})

    body = client.get("/spaces").json()
    stopped = space_by_id(body, "room-101")
    assert stopped["status"] == "no_data"
    assert stopped["person_count"] is None
    # A ROI que continua habilitada não é afetada.
    assert space_by_id(body, "room-102")["status"] == "normal"


def test_status_is_not_frozen_at_ingest(client, age_camera):
    """Se o status fosse gravado no ingest, nunca viraria no_data."""
    ingest(client, {"ROI-01": 40})
    assert client.get("/spaces/room-101/occupancy").json()["status"] == "over_limit"
    age_camera("CAM-01", seconds=45)
    assert client.get("/spaces/room-101/occupancy").json()["status"] == "no_data"


# --- spaces -----------------------------------------------------------------


def test_spaces_payload_matches_contract(client):
    ingest(client, {"ROI-02": 36})
    space = space_by_id(client.get("/spaces").json(), "room-102")

    assert space["id"] == "room-102"
    assert space["name"] == "Sala 102"
    assert space["code"] == "102"
    assert space["type"] == "classroom"
    assert space["building"] == {"id": "bld-1", "name": "Prédio 1"}
    assert space["floor"] == {"id": "bld-1-f2", "name": "2º andar", "level": 2}
    assert space["capacity"] == 40
    assert space["operational_limit"] == 35
    assert space["person_count"] == 36
    assert space["occupancy_rate"] == 0.9
    assert space["status"] == "over_limit"
    assert ISO_Z.match(space["captured_at"])
    assert set(space) == {
        "id", "name", "code", "type", "building", "floor", "capacity",
        "operational_limit", "person_count", "occupancy_rate", "status", "captured_at",
    }


def test_space_detail_includes_source(client):
    ingest(client, {"ROI-01": 10})
    body = client.get("/spaces/room-101").json()

    assert body["source"] == {
        "camera_id": "CAM-01",
        "camera_name": "Câmera 1",
        "region_id": "ROI-01",
        "online": True,
        "last_seen_at": body["source"]["last_seen_at"],
    }
    assert ISO_Z.match(body["source"]["last_seen_at"])


def test_space_source_goes_offline_with_the_camera(client, age_camera):
    ingest(client, {"ROI-01": 10})
    age_camera("CAM-01", seconds=31)
    assert client.get("/spaces/room-101").json()["source"]["online"] is False


def test_unknown_space_is_404(client):
    for path in ("/spaces/room-999", "/spaces/room-999/occupancy", "/spaces/room-999/history"):
        response = client.get(path)
        assert response.status_code == 404, path
        assert response.json() == {"detail": "space not found"}


# --- history ----------------------------------------------------------------


def test_history_is_chronological(client):
    for count in (10, 20, 30):
        ingest(client, {"ROI-01": count})

    body = client.get("/spaces/room-101/history?minutes=30").json()
    assert body["space_id"] == "room-101"
    assert [point["person_count"] for point in body["points"]] == [10, 20, 30]

    timestamps = [point["captured_at"] for point in body["points"]]
    assert timestamps == sorted(timestamps)
    assert all(ISO_Z.match(value) for value in timestamps)


def test_history_defaults_to_30_minutes(client):
    ingest(client, {"ROI-01": 7})
    assert client.get("/spaces/room-101/history").json()["points"][0]["person_count"] == 7


def test_history_is_empty_without_snapshots(client):
    assert client.get("/spaces/room-101/history").json() == {
        "space_id": "room-101",
        "points": [],
    }


def test_history_caps_at_500_most_recent_points(client):
    from app.database import SessionLocal
    from app.models import OccupancySnapshot
    from app.timeutil import utcnow

    with SessionLocal() as session:
        now = utcnow()
        session.add_all(
            OccupancySnapshot(
                space_id="room-101",
                camera_region_id="ROI-01",
                person_count=index,
                occupancy_rate=index / 40,
                captured_at=now,
            )
            for index in range(520)
        )
        session.commit()

    points = client.get("/spaces/room-101/history?minutes=30").json()["points"]
    assert len(points) == 500
    # Os mais recentes, não os primeiros.
    assert [point["person_count"] for point in points] == list(range(20, 520))


# --- summary ----------------------------------------------------------------


def test_summary(client):
    ingest(client, {"ROI-01": 10, "ROI-02": 0})
    body = client.get("/summary").json()

    assert body["spaces_total"] == 2
    assert body["normal"] == 1
    assert body["empty"] == 1
    assert body["high"] == 0
    assert body["over_limit"] == 0
    assert body["no_data"] == 0
    assert body["total_people"] == 10
    assert body["cameras_online"] == 1
    assert body["cameras_total"] == 1
    assert ISO_Z.match(body["generated_at"])


def test_summary_ignores_no_data_in_total_people(client, age_camera):
    ingest(client, {"ROI-01": 10, "ROI-02": 5})
    age_camera("CAM-01", seconds=31)

    body = client.get("/summary").json()
    assert body["no_data"] == 2
    assert body["total_people"] == 0
    assert body["cameras_online"] == 0


def test_summary_counts_add_up_to_spaces_total(client):
    ingest(client, {"ROI-01": 36})
    body = client.get("/summary").json()
    counted = sum(body[status] for status in ("empty", "normal", "high", "over_limit", "no_data"))
    assert counted == body["spaces_total"]


# --- CORS -------------------------------------------------------------------


def test_cors_allows_the_frontend(client):
    response = client.options(
        "/spaces",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
