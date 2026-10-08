import time


def test_health_and_schema(client):
    assert client.get("/health").json()["database"] == "sqlite"
    assert "/api/runs" in client.get("/openapi.json").json()["paths"]
    assert len(client.get("/api/evaluations/dataset").json()) == 30
    assert len(client.get("/api/tools").json()) == 5


def test_real_submission_stream_and_review(client):
    response = client.post(
        "/api/runs", json={"task": "Review refund for order NS-1042.", "top_k": 8}
    )
    assert response.status_code == 202
    rid = response.json()["id"]
    with client.stream("GET", f"/api/runs/{rid}/events") as stream:
        content = "".join(stream.iter_text())
    assert "event: trace" in content and "event: complete" in content
    run = client.get(f"/api/runs/{rid}").json()
    assert run["state"]["draft_answer"]["amount"] == 899
    assert (
        client.post(
            f"/api/runs/{rid}/review", json={"decision": "approve", "expected_revision": 0}
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/runs/{rid}/review", json={"decision": "approve", "expected_revision": 0}
        ).status_code
        == 409
    )
    detail = client.get(f"/api/runs/{rid}").json()
    assert len(detail["actions"]) == 1 and len(detail["reviews"]) == 1


def test_live_requires_auth_and_key(client, monkeypatch):
    assert (
        client.post(
            "/api/runs", json={"task": "Review refund for order NS-1042.", "mode": "live"}
        ).status_code
        == 403
    )
    monkeypatch.setenv("OPSPILOT_ADMIN_TOKEN", "test-admin-token")
    assert (
        client.post(
            "/api/runs",
            headers={"Authorization": "Bearer test-admin-token"},
            json={"task": "Review refund for order NS-1042.", "mode": "live"},
        ).status_code
        == 503
    )


def test_upload_requires_admin_and_is_untrusted(client, monkeypatch):
    data = {
        "file": (
            "api-upload.txt",
            b"An uploaded article about velociraptor customer service processes.",
            "text/plain",
        )
    }
    assert client.post("/api/documents", files=data).status_code == 403
    monkeypatch.setenv("OPSPILOT_ADMIN_TOKEN", "test-admin-token")
    response = client.post(
        "/api/documents", files=data, headers={"Authorization": "Bearer test-admin-token"}
    )
    assert response.status_code == 200
    docs = client.get("/api/documents").json()
    assert next(d for d in docs if d["id"] == response.json()["id"])["trusted"] == 0


def test_invalid_inputs_and_missing_resources(client):
    assert client.get("/api/runs/not-found").status_code == 404
    assert client.get("/api/documents/not-found").status_code == 404
    assert client.get("/api/search?q=x&top_k=10000").status_code == 422
    assert client.post("/api/runs", json={"task": "x"}).status_code == 422


def test_benchmark_api(client):
    response = client.post("/api/evaluations")
    assert response.status_code == 202
    bid = response.json()["id"]
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        result = client.get(f"/api/evaluations/{bid}").json()
        if result["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)
    assert result["status"] == "completed"
    assert result["metrics"]["cases"] == 30
    assert result["metrics"]["passed"] == 30
