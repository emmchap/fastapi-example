"""Test the application."""

from io import BytesIO
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_get_jobs():
    """Test to get the jobs (empty list)."""
    response = client.get("/jobs")
    assert response.status_code == 200
    assert response.json() == []


def test_job_creation():
    """Test the job creation (and its workflow)."""
    with BytesIO() as tempfile:
        tempfile.write(b"FROM ubuntu:22.04\n")
        tempfile.write(b'CMD echo {\\"perf\\":0.99} > /data/perf.json')
        tempfile.seek(0)
        response = client.post("job/create", files={"dockerfile": tempfile})
    assert response.status_code == 200
    job = response.json()
    assert job["status"] == "INIT"
    assert job["result"] is None
    while job["status"] in ("INIT", "RUNNING"):
        job = client.get(f"/job/{job['id']}").json()
    assert job["status"] == "FINISHED"
    assert job["result"] == 0.99
    assert client.get("/jobs").json()[0] == job["id"]
    job["result"] = None
    response = client.post("/job/update", json=job)
    assert client.get(f"/job/{job['id']}").json()["result"] is None


def test_wrong_dockerfile():
    """Test the job creation with a wrong Dockerfile"""
    with BytesIO() as tempfile:
        tempfile.write(b"")
        tempfile.seek(0)
        job = client.post("job/create", files={"dockerfile": tempfile}).json()
    while job["status"] in ("INIT", "RUNNING"):
        job = client.get(f"/job/{job['id']}").json()
    assert job["status"] == "FAILED"
    assert job["result"] is None


def test_vulnerable_dockerfile():
    """Test the job creation with a vulnerable Dockerfile"""
    with BytesIO() as tempfile:
        tempfile.write(b"FROM ubuntu:16.04\n")
        tempfile.write(b'CMD echo {\\"perf\\":0.99} > /data/perf.json')
        tempfile.seek(0)
        job = client.post("job/create", files={"dockerfile": tempfile}).json()
    while job["status"] in ("INIT", "RUNNING"):
        job = client.get(f"/job/{job['id']}").json()
    assert job["status"] == "FAILED"
    assert job["result"] is None


def test_job_wo_result():
    """Test the job creation with any result"""
    with BytesIO() as tempfile:
        tempfile.write(b"FROM ubuntu:22.04\n")
        tempfile.write(b'CMD echo {\\"perf\\":0.99}')
        tempfile.seek(0)
        job = client.post("job/create", files={"dockerfile": tempfile}).json()
    while job["status"] in ("INIT", "RUNNING"):
        job = client.get(f"/job/{job['id']}").json()
    assert job["status"] == "FAILED"
    assert job["result"] is None
