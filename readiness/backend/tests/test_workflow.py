import pytest
import pytest_asyncio
import json
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import async_session_factory, Base, engine
from app.security import init_db
from app.graph.json_store import graph_store
from app.workflow.models import User, Asset, WorkOrder, Outcome


import os
from pathlib import Path

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_test_db():
    possible_paths = [
        Path("/app/graph.json"),
        Path(__file__).resolve().parent.parent.parent / "graph.json",
        Path("graph.json")
    ]
    for p in possible_paths:
        if p.exists():
            graph_store.load_from_file(p)
            break
    await init_db()
    yield


@pytest.mark.asyncio
async def test_auth_workflow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Tech login
        res = await client.post("/api/auth/login", json={"username": "tech", "password": "tech123"})
        assert res.status_code == 200, res.text
        data = res.json()
        assert "access_token" in data
        assert data["user"]["role"] == "technician"
        tech_token = data["access_token"]

        # 2. Get /api/auth/me
        me_res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {tech_token}"})
        assert me_res.status_code == 200
        assert me_res.json()["username"] == "tech"

        # 3. Supervisor login
        sup_res = await client.post("/api/auth/login", json={"username": "supervisor", "password": "super123"})
        assert sup_res.status_code == 200
        assert sup_res.json()["user"]["role"] == "supervisor"


@pytest.mark.asyncio
async def test_assets_and_readiness_board():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/assets")
        assert res.status_code == 200
        assets = res.json()
        assert len(assets) >= 5
        
        # Verify P-102 has superseded manual warning (Trap 2)
        p102 = next((a for a in assets if a["asset_id"] == "P-102"), None)
        assert p102 is not None
        assert p102["is_superseded_manual"] is True
        assert "SUPERSEDED_MANUAL_IN_USE" in p102["flags"]


@pytest.mark.asyncio
async def test_complete_maintenance_workflow_accept():
    """
    Core ACCEPT check for Phase 4:
    Technician starts session -> records finding -> creates draft work order -> submits resolution.
    AI / Tech cannot mark asset ready or approved.
    Supervisor approves -> creates verified outcome & graph edge -> graph includes it.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login tech
        t_res = await client.post("/api/auth/login", json={"username": "tech", "password": "tech123"})
        tech_token = t_res.json()["access_token"]
        tech_headers = {"Authorization": f"Bearer {tech_token}"}

        # Login supervisor
        s_res = await client.post("/api/auth/login", json={"username": "supervisor", "password": "super123"})
        sup_token = s_res.json()["access_token"]
        sup_headers = {"Authorization": f"Bearer {sup_token}"}

        # 1. Start Session
        ses_res = await client.post(
            "/api/sessions",
            headers=tech_headers,
            json={
                "asset_id": "P-101",
                "symptom_text": "High radial vibration on pump DE bearing housing",
                "alarm_code": "ALM-VIB-101",
                "diagnosis_summary": "High likelihood of bearing inner ring spall.",
                "candidate_causes": [{"cause_id": "CAUSE-BRG-WEAR", "name": "Bearing Ball / Race Degradation"}],
                "initial_procedures": [{"procedure_id": "PROC-BRG-INSPECT"}]
            }
        )
        assert ses_res.status_code == 201
        session_id = ses_res.json()["id"]

        # 2. Record Technician Finding
        fnd_res = await client.post(
            f"/api/sessions/{session_id}/findings",
            headers=tech_headers,
            json={
                "finding_type": "measurement",
                "component_id": "COMP-P101-BRG-DE",
                "parameter": "radial_vibration_mm_s",
                "value": "7.8 mm/s",
                "notes": "Bearing temperature measured at 84 C. High acoustic emissions."
            }
        )
        assert fnd_res.status_code == 201

        # 3. Create Draft Work Order
        wo_res = await client.post(
            "/api/workorders",
            headers=tech_headers,
            json={
                "asset_id": "P-101",
                "session_id": session_id,
                "title": "Replace DE pump bearing on P-101",
                "priority": "high",
                "required_parts": ["PART-BRG-6312"],
                "findings_summary": "Confirmed radial vibration 7.8 mm/s exceeding ISO 10816 threshold."
            }
        )
        assert wo_res.status_code == 201
        wo_id = wo_res.json()["id"]
        assert wo_res.json()["status"] == "draft"

        # 4. Technician Submits Resolution
        res_sub = await client.post(
            f"/api/workorders/{wo_id}/submit-resolution",
            headers=tech_headers,
            json={
                "confirmed_cause": "CAUSE-BRG-WEAR",
                "action_taken": "Removed worn 6312 bearing, inspected shaft seat, pressed on new 6312-C3 bearing, dynamic balancing re-check.",
                "parts_used": "PART-BRG-6312",
                "result": "resolved"
            }
        )
        assert res_sub.status_code == 200
        assert res_sub.json()["status"] == "pending_approval"

        # 5. Technician attempts to approve -> MUST BE FORBIDDEN (403)
        forbidden_res = await client.post(
            f"/api/workorders/{wo_id}/approve",
            headers=tech_headers,
            json={"downtime_hours": 3.0}
        )
        assert forbidden_res.status_code == 403

        # Count verified incidents before approval
        initial_incidents_count = len(graph_store.get_verified_incidents(asset_id="P-101"))

        # 6. Supervisor Approves Work Order
        app_res = await client.post(
            f"/api/workorders/{wo_id}/approve",
            headers=sup_headers,
            json={
                "downtime_hours": 2.5,
                "notes": "Reviewed vibration log and technician work. Approved for operational restart."
            }
        )
        assert app_res.status_code == 200
        approval_data = app_res.json()
        assert approval_data["status"] == "approved"
        assert approval_data["verified_by"] == "supervisor"

        # 7. Verify Graph Store has the new verified edge & node!
        new_incidents_count = len(graph_store.get_verified_incidents(asset_id="P-101"))
        assert new_incidents_count == initial_incidents_count + 1

        # Check edge attributes
        latest_incident = graph_store.get_verified_incidents(asset_id="P-101")[-1]
        assert latest_incident["supervisor_approved"] is True
        assert latest_incident["approved_by"] == "supervisor"
        assert latest_incident["confirmed_cause_id"] == "CAUSE-BRG-WEAR"


@pytest.mark.asyncio
async def test_supervisor_rejection_adds_no_graph_edge():
    """
    If supervisor rejects a work order, status becomes rejected and NO graph edge is created.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login tech
        t_res = await client.post("/api/auth/login", json={"username": "tech", "password": "tech123"})
        tech_headers = {"Authorization": f"Bearer {t_res.json()['access_token']}"}

        # Login supervisor
        s_res = await client.post("/api/auth/login", json={"username": "supervisor", "password": "super123"})
        sup_headers = {"Authorization": f"Bearer {s_res.json()['access_token']}"}

        # Create Work Order
        wo_res = await client.post(
            "/api/workorders",
            headers=tech_headers,
            json={"asset_id": "M-104", "title": "Check motor coupling"}
        )
        wo_id = wo_res.json()["id"]

        # Submit resolution
        await client.post(
            f"/api/workorders/{wo_id}/submit-resolution",
            headers=tech_headers,
            json={
                "confirmed_cause": "CAUSE-SHAFT-MISALIGN",
                "action_taken": "Tightened bolts without laser alignment measurement.",
                "result": "resolved"
            }
        )

        initial_count = len(graph_store.get_verified_incidents(asset_id="M-104"))

        # Supervisor rejects
        rej_res = await client.post(
            f"/api/workorders/{wo_id}/reject",
            headers=sup_headers,
            json={"rejection_reason": "Inadequate action: dial indicator or laser alignment report required before clearance."}
        )
        assert rej_res.status_code == 200
        assert rej_res.json()["status"] == "rejected"

        # Verify NO edge was created
        final_count = len(graph_store.get_verified_incidents(asset_id="M-104"))
        assert final_count == initial_count


@pytest.mark.asyncio
async def test_analytics_and_subgraph_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Recurring faults
        rec_res = await client.get("/api/analytics/recurring")
        assert rec_res.status_code == 200
        assert "clusters" in rec_res.json()

        # Readiness board
        read_res = await client.get("/api/analytics/readiness")
        assert read_res.status_code == 200
        assert "assets" in read_res.json()
        assert "fleet_average_readiness" in read_res.json()

        # Subgraph for P-101
        sg_res = await client.get("/api/graph/subgraph/P-101")
        assert sg_res.status_code == 200
        sg_data = sg_res.json()
        assert "nodes" in sg_data
        assert "edges" in sg_data
        assert any(n["id"] == "P-101" for n in sg_data["nodes"])
