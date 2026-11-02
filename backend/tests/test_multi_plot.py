"""Unit & Integration Tests for Parent Farm Holdings and Multi-Plot Registration (Milestone B)."""

import pytest


@pytest.fixture
def registered_farmer_client(client):
    """Register farmer and provide authenticated headers."""
    reg_payload = {
        "phone_number": "+919888777666",
        "full_name": "Balwinder Singh",
        "pin": "2468",
        "preferred_language": "hi",
        "device_id": "DEV-BALWINDER-001",
    }
    resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert resp.status_code == 201
    token = resp.json()["token"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return {"headers": headers, "device_id": "DEV-BALWINDER-001", "user": resp.json()["user"]}


@pytest.fixture
def second_farmer_client(client):
    """Register second farmer for tenant isolation testing."""
    reg_payload = {
        "phone_number": "+919777666555",
        "full_name": "Harpreet Kaur",
        "pin": "1357",
        "preferred_language": "hi",
        "device_id": "DEV-HARPREET-002",
    }
    resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert resp.status_code == 201
    token = resp.json()["token"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return {"headers": headers, "device_id": "DEV-HARPREET-002", "user": resp.json()["user"]}


def test_farm_creation_and_listing(client, registered_farmer_client):
    """Verify parent farm registration, listing, and default metrics."""
    headers = registered_farmer_client["headers"]
    farm_payload = {
        "name": "Guru Nanak Agri Estate",
        "village": "Raikot",
        "subdistrict": "Ludhiana West",
        "district": "Ludhiana",
        "state": "Punjab",
        "device_id": registered_farmer_client["device_id"],
    }
    create_resp = client.post("/api/v1/farms", json=farm_payload, headers=headers)
    assert create_resp.status_code == 201, create_resp.text
    farm = create_resp.json()

    assert farm["id"] is not None
    assert farm["name"] == "Guru Nanak Agri Estate"
    assert farm["district"] == "Ludhiana"
    assert farm["total_area_hectares"] == 0.0
    assert farm["plot_count"] == 0
    farm_id = farm["id"]

    # List farms
    list_resp = client.get("/api/v1/farms", headers=headers)
    assert list_resp.status_code == 200
    farms = list_resp.json()
    assert len(farms) == 1
    assert farms[0]["id"] == farm_id


def test_multi_plot_registration_under_same_farm(client, registered_farmer_client):
    """Verify that multiple plots can be registered under one farm and remain active concurrently."""
    headers = registered_farmer_client["headers"]
    dev_id = registered_farmer_client["device_id"]

    # 1. Create parent farm
    farm_payload = {
        "name": "Kaveri Delta Farm",
        "district": "Thanjavur",
        "state": "Tamil Nadu",
        "device_id": dev_id,
    }
    farm_resp = client.post("/api/v1/farms", json=farm_payload, headers=headers)
    assert farm_resp.status_code == 201
    farm_id = farm_resp.json()["id"]

    # 2. Register Plot 1 (North Paddy Field)
    plot1_payload = {
        "device_id": dev_id,
        "farm_id": farm_id,
        "name": "North Paddy Field",
        "survey_number": "SN-101",
        "boundary": {
            "type": "Polygon",
            "coordinates": [
                [
                    [79.1000, 10.7000],
                    [79.10094, 10.7000],
                    [79.10094, 10.7009],
                    [79.1000, 10.7009],
                    [79.1000, 10.7000],
                ]
            ],
        },
        "soil_texture": "Clay Loam",
    }
    plot1_resp = client.post("/api/v1/plots", json=plot1_payload)
    assert plot1_resp.status_code == 201, plot1_resp.text
    plot1_id = plot1_resp.json()["id"]
    plot1_ha = plot1_resp.json()["area_hectares"]
    assert plot1_resp.json()["farm_id"] == farm_id
    assert plot1_resp.json()["is_active"] is True

    # 3. Register Plot 2 (South Sugarcane Field)
    plot2_payload = {
        "device_id": dev_id,
        "farm_id": farm_id,
        "name": "South Sugarcane Field",
        "survey_number": "SN-102",
        "boundary": {
            "type": "Polygon",
            "coordinates": [
                [
                    [79.1100, 10.7100],
                    [79.11094, 10.7100],
                    [79.11094, 10.7109],
                    [79.1100, 10.7109],
                    [79.1100, 10.7100],
                ]
            ],
        },
        "soil_texture": "Alluvial",
    }
    plot2_resp = client.post("/api/v1/plots", json=plot2_payload)
    assert plot2_resp.status_code == 201, plot2_resp.text
    plot2_id = plot2_resp.json()["id"]
    plot2_ha = plot2_resp.json()["area_hectares"]
    assert plot2_resp.json()["is_active"] is True

    # 4. CRITICAL CHECK: Verify Plot 1 is STILL active (multi-plot support)
    p1_check = client.get(f"/api/v1/plots/{plot1_id}")
    assert p1_check.status_code == 200
    assert p1_check.json()["is_active"] is True

    # 5. Check Farm aggregated acreage and plot count
    farm_detail = client.get(f"/api/v1/farms/{farm_id}", headers=headers)
    assert farm_detail.status_code == 200
    farm_data = farm_detail.json()
    assert farm_data["plot_count"] == 2
    assert farm_data["total_area_hectares"] == round(plot1_ha + plot2_ha, 2)

    # 6. Retrieve MultiPlot summary
    multi_resp = client.get(f"/api/v1/farms/{farm_id}/plots", headers=headers)
    assert multi_resp.status_code == 200
    multi_data = multi_resp.json()
    assert multi_data["active_plots_count"] == 2
    assert len(multi_data["plots"]) == 2
    plot_names = [p["name"] for p in multi_data["plots"]]
    assert "North Paddy Field" in plot_names
    assert "South Sugarcane Field" in plot_names


def test_farm_tenant_isolation(client, registered_farmer_client, second_farmer_client):
    """Verify that Farm holdings belonging to Farmer 1 cannot be viewed or altered by Farmer 2."""
    headers_1 = registered_farmer_client["headers"]
    headers_2 = second_farmer_client["headers"]

    # Farmer 1 creates farm
    farm_resp = client.post(
        "/api/v1/farms",
        json={"name": "Farmer One Private Orchard", "district": "Nashik"},
        headers=headers_1,
    )
    assert farm_resp.status_code == 201
    farm_id = farm_resp.json()["id"]

    # Farmer 2 attempts to get Farm 1 details -> 403 Forbidden
    get_forbidden = client.get(f"/api/v1/farms/{farm_id}", headers=headers_2)
    assert get_forbidden.status_code == 403
    assert "permission" in get_forbidden.json()["detail"].lower()

    # Farmer 2 attempts to list plots of Farm 1 -> 403 Forbidden
    plots_forbidden = client.get(f"/api/v1/farms/{farm_id}/plots", headers=headers_2)
    assert plots_forbidden.status_code == 403

    # Farmer 2 attempts to delete Farm 1 -> 403 Forbidden
    del_forbidden = client.delete(f"/api/v1/farms/{farm_id}", headers=headers_2)
    assert del_forbidden.status_code == 403


def test_farm_deactivation_cascades_plots(client, registered_farmer_client):
    """Verify that deactivating a farm deactivates all child plots."""
    headers = registered_farmer_client["headers"]
    dev_id = registered_farmer_client["device_id"]

    farm_resp = client.post("/api/v1/farms", json={"name": "Farm To Deactivate"}, headers=headers)
    farm_id = farm_resp.json()["id"]

    # Add plot
    plot_payload = {
        "device_id": dev_id,
        "farm_id": farm_id,
        "name": "Deactivate Plot Test",
        "boundary": {
            "type": "Polygon",
            "coordinates": [[[78.0, 17.0], [78.01, 17.0], [78.01, 17.01], [78.0, 17.01], [78.0, 17.0]]],
        },
    }
    p_resp = client.post("/api/v1/plots", json=plot_payload)
    plot_id = p_resp.json()["id"]

    # Deactivate farm
    del_resp = client.delete(f"/api/v1/farms/{farm_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deactivated"

    # Farm is no longer in active listing
    farms_list = client.get("/api/v1/farms", headers=headers).json()
    assert all(f["id"] != farm_id for f in farms_list)

    # Plot is now inactive
    p_check = client.get(f"/api/v1/plots/{plot_id}")
    assert p_check.json()["is_active"] is False


def test_plot_filtering_by_farm_id(client, registered_farmer_client):
    """Verify /plots?farm_id=X retrieves only plots linked to that farm."""
    headers = registered_farmer_client["headers"]
    dev_id = registered_farmer_client["device_id"]

    farm_resp = client.post("/api/v1/farms", json={"name": "Filter Test Holding"}, headers=headers)
    farm_id = farm_resp.json()["id"]

    p_payload = {
        "device_id": dev_id,
        "farm_id": farm_id,
        "name": "Plot Under Filter Farm",
        "boundary": {
            "type": "Polygon",
            "coordinates": [[[78.1, 17.1], [78.11, 17.1], [78.11, 17.11], [78.1, 17.11], [78.1, 17.1]]],
        },
    }
    p_resp = client.post("/api/v1/plots", json=p_payload)
    plot_id = p_resp.json()["id"]

    list_resp = client.get(f"/api/v1/plots?farm_id={farm_id}")
    assert list_resp.status_code == 200
    plots = list_resp.json()
    assert len(plots) == 1
    assert plots[0]["id"] == plot_id

