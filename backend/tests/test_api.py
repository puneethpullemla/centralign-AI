import pytest
from app.models.task import Task
from app.models.approval import Approval
from app.models.evidence import Evidence


def test_health_check(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "app" in data


def test_create_task(client):
    payload = {
        "user_task": "Find the latest invoice from Acme, extract amount and due date, enter into billing system",
        "simulate_save_failure": False
    }
    res = client.post("/api/tasks", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert data["user_task"] == payload["user_task"]
    assert data["status"] in ("PENDING", "RUNNING", "AWAITING_APPROVAL")


def test_get_task_not_found(client):
    res = client.get("/api/tasks/non-existent-id")
    assert res.status_code == 404


def test_approve_task_flow(client, db_session):
    # Setup pending task & approval
    task = Task(id="test-task-1", user_task="Sample task", status="AWAITING_APPROVAL")
    approval = Approval(id="appr-1", task_id=task.id, status="PENDING", payload={"company": "Acme", "amount": "₹48,500"})
    db_session.add(task)
    db_session.add(approval)
    db_session.commit()

    res = client.post(f"/api/tasks/{task.id}/approve")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "APPROVED"
    assert data["task_id"] == task.id


def test_reject_task_flow(client, db_session):
    task = Task(id="test-task-2", user_task="Sample task", status="AWAITING_APPROVAL")
    approval = Approval(id="appr-2", task_id=task.id, status="PENDING", payload={"company": "Acme", "amount": "₹48,500"})
    db_session.add(task)
    db_session.add(approval)
    db_session.commit()

    res = client.post(f"/api/tasks/{task.id}/reject")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "REJECTED"


def test_get_evidence_endpoint(client, db_session):
    task = Task(id="test-task-3", user_task="Sample task", status="COMPLETED")
    ev = Evidence(id="ev-1", task_id=task.id, type="SCREENSHOT", path="/tmp/shot.png", description="Verification screenshot")
    db_session.add(task)
    db_session.add(ev)
    db_session.commit()

    res = client.get(f"/api/tasks/{task.id}/evidence")
    assert res.status_code == 200
    data = res.json()
    assert len(data["evidence_items"]) == 1
    assert data["evidence_items"][0]["type"] == "SCREENSHOT"
