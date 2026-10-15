import sqlite3
from datetime import date, timedelta

import pytest

import app as app_module
from app import validate_crop_inputs
from services import market_forecast_service
from services.official_market_service import refresh_market_data


def _market_record(observed, modal=150):
    return {
        "commodity": "Rice",
        "market": "Test",
        "district": "Pune",
        "state": "Maharashtra",
        "variety": "Common",
        "arrival_date": observed.strftime("%d/%m/%Y"),
        "min_price": str(modal - 10),
        "modal_price": str(modal),
        "max_price": str(modal + 10),
    }


def test_crop_input_validation_rejects_missing_and_nonfinite_values():
    values = {
        "nitrogen": "70", "phosphorus": "40", "potassium": "40", "ph": "6.5",
        "temperature": "26", "humidity": "65", "rainfall": "120",
    }
    assert validate_crop_inputs(values)["nitrogen"] == 70
    with pytest.raises(ValueError):
        validate_crop_inputs({**values, "humidity": "101"})
    with pytest.raises(ValueError):
        validate_crop_inputs({**values, "temperature": "nan"})
    with pytest.raises(ValueError):
        validate_crop_inputs({key: value for key, value in values.items() if key != "rainfall"})


def test_crop_json_api_returns_validation_and_model_errors_clearly(tmp_path, monkeypatch):
    from test_extended_flows import setup_client

    _, client, _ = setup_client(tmp_path)
    assert client.post("/api/recommend-crop", json={}).status_code == 400
    valid = {
        "nitrogen": 70, "phosphorus": 40, "potassium": 40, "ph": 6.5,
        "temperature": 26, "humidity": 65, "rainfall": 120,
    }
    assert client.post("/api/recommend-crop", json={**valid, "ph": 15}).status_code == 400

    monkeypatch.setattr(app_module, "predict_crop", lambda _values: (_ for _ in ()).throw(FileNotFoundError("missing model")))
    response = client.post("/api/recommend-crop", json=valid)
    assert response.status_code == 503
    assert response.json["success"] is False
    assert "temporarily unavailable" in response.json["message"]


def test_market_history_is_distinct_market_scoped_and_accumulated(monkeypatch, tmp_path):
    from services import official_market_service as market

    monkeypatch.setattr(market, "_cache", {})
    monkeypatch.setattr(market, "_next_attempt", 0)
    monkeypatch.setattr(market, "_refresh_after", {})
    monkeypatch.setattr(market, "_inflight", False)
    monkeypatch.setattr(market, "_loaded", True)
    monkeypatch.setattr(market, "CACHE_PATH", tmp_path / "market-cache.json")
    monkeypatch.setenv("DATA_GOV_IN_API_KEY", "test-only")
    records = [_market_record(date.today() - timedelta(days=offset)) for offset in range(20)]
    records.extend([records[0], _market_record(date.today() - timedelta(days=1), 170)])
    monkeypatch.setattr(market, "request_sample", lambda *_args, **_kwargs: {"records": records[:10]})
    refresh_market_data()
    query_key = "{}"
    assert len(market._cache[query_key]["commodities"]["rice"]["history_30d"]) == 10

    monkeypatch.setattr(market, "_refresh_after", {})
    monkeypatch.setattr(market, "_next_attempt", 0)
    monkeypatch.setattr(market, "request_sample", lambda *_args, **_kwargs: {"records": records[10:]})
    refresh_market_data()
    cached = market._cache[query_key]
    assert len(cached["raw_records"]) == 20
    assert len(cached["commodities"]["rice"]["history_30d"]) == 20
    assert len({entry["date"] for entry in cached["commodities"]["rice"]["history_30d"]}) == 20

    monkeypatch.setattr(
        market_forecast_service,
        "get_market_prices_for_commodity",
        lambda _commodity: {
            "found": True,
            "history_30d": [
                {"date": (date.today() - timedelta(days=offset)).isoformat(), "modal": 150 + offset,
                 "market_name": market_name, "variety": variety}
                for market_name, variety in (
                    ("Market A", "Common"), ("Market A", "Fine"),
                    ("Market B", "Common"), ("Market B", "Fine"),
                )
                for offset in range(10)
            ],
        },
    )
    result = market_forecast_service.forecast_commodity_price("Rice")
    assert result["status"] == "INSUFFICIENT_HISTORY"
    assert "one market and variety" in result["message"]

    monkeypatch.setattr(
        market_forecast_service,
        "get_market_prices_for_commodity",
        lambda _commodity: {
            "found": True,
            "history_30d": [
                {"date": (date.today() - timedelta(days=offset)).isoformat(), "modal": 150 + offset,
                 "market_name": "Market A", "variety": "Common"}
                for offset in range(20)
            ],
        },
    )
    result = market_forecast_service.forecast_commodity_price("Rice")
    assert result["status"] == "SUCCESS"
    assert result["market_name"] == "Market A"
    assert result["variety"] == "Common"


def test_financial_routes_reject_invalid_values_without_writes(tmp_path):
    from test_extended_flows import setup_client

    _, client, database = setup_client(tmp_path)
    client.post("/activities/create", data={"title": "Check irrigation", "activity_type": "Irrigation"})
    with sqlite3.connect(database) as connection:
        activity_id = connection.execute(
            "SELECT id FROM farm_activities WHERE title = 'Check irrigation'"
        ).fetchone()[0]
    assert client.post(
        f"/activities/{activity_id}/status",
        data={"status": "COMPLETED", "amount_spent": "not-a-number"},
    ).status_code == 400
    assert client.post(
        f"/activities/{activity_id}/status",
        data={"status": "COMPLETED", "amount_spent": "-50"},
    ).status_code == 400
    assert client.post("/add-sale", data={"commodity": "Rice", "quantity_sold": "bad", "price_per_unit": "10"}).status_code == 400
    assert client.post("/add-sale", data={
        "commodity": "Rice", "quantity_sold": "5", "price_per_unit": "10", "sale_date": "not-a-date",
    }).status_code == 400
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM farm_expenses").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0


def test_lifecycle_tasks_are_generated_once_per_stage(tmp_path):
    from test_extended_flows import setup_client

    _, client, database = setup_client(tmp_path)
    client.post("/lifecycle", data={"crop_name": "Rice", "sowing_date": date.today().isoformat()})
    assert client.get("/activities").status_code == 200
    with sqlite3.connect(database) as connection:
        first_count = connection.execute("SELECT COUNT(*) FROM farm_activities").fetchone()[0]
    assert first_count > 0
    assert client.get("/activities").status_code == 200
    with sqlite3.connect(database) as connection:
        second_count = connection.execute("SELECT COUNT(*) FROM farm_activities").fetchone()[0]
    assert second_count == first_count
