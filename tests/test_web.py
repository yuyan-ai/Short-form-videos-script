import threading
import time
import httpx
import pytest
from http.server import ThreadingHTTPServer
from short_video_agent.web import Jobs, handler_for
from test_graph_mock import request


@pytest.fixture
def server(tmp_path):
    jobs = Jobs(output=tmp_path)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(jobs))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    with httpx.Client(base_url=f"http://127.0.0.1:{httpd.server_port}", trust_env=False) as client:
        yield client
    httpd.shutdown()
    httpd.server_close()
    jobs.pool.shutdown(wait=True)


def test_static_and_no_secret_files(server):
    assert server.get("/").status_code == 200
    assert "default-src" in server.get("/").headers["Content-Security-Policy"]
    assert server.get("/app.js").status_code == 200
    assert server.get("/.env").status_code == 404
    assert server.get("/api/jobs/unknown").status_code == 404


def test_cross_origin_rejected(server):
    response = server.post("/api/jobs", headers={"Origin":"https://evil.test"}, json={})
    assert response.status_code == 403
    assert server.get("/", headers={"Host":"evil.test"}).status_code == 403


def test_validation(server):
    assert server.post("/api/jobs", json={"request":{},"mode":"live-wrong"}).status_code == 400
    assert server.post("/api/jobs", json={"request":{},"max_steps":True}).status_code == 400


def test_job_result_and_exports(server):
    response = server.post("/api/jobs",json={"request":request("overlong"),"mode":"mock","max_steps":12})
    assert response.status_code == 202
    job_id = response.json()["id"]
    for _ in range(50):
        job = server.get(f"/api/jobs/{job_id}").json()
        if job["status"] != "running":
            break
        time.sleep(.02)
    assert job["status"] == "completed"
    assert job["result"]["checks"]["passed"]
    assert len([e for e in job["trace"] if e["action"] == "save_draft"]) == 2
    assert "API_KEY" not in str(job)
    assert "字幕" in job["markdown"]
