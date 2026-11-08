def test_create_and_get_candidate(client):
    payload = {
        "full_name": "Jane Doe",
        "email": "jane.doe@example.com",
        "candidate_type": "experienced",
    }
    response = client.post("/api/candidates/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == payload["full_name"]
    assert data["email"] == payload["email"]
    assert data["candidate_type"] == payload["candidate_type"]
    assert "id" in data
    assert "created_at" in data

    candidate_id = data["id"]

    # Retrieve candidate
    get_res = client.get(f"/api/candidates/{candidate_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["id"] == candidate_id
    assert retrieved["email"] == payload["email"]


def test_list_candidates(client):
    # Candidate list test
    res = client.get("/api/candidates/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_create_candidate_duplicate_email(client):
    payload = {
        "full_name": "Duplicate User",
        "email": "duplicate@example.com",
        "candidate_type": "student",
    }
    res1 = client.post("/api/candidates/", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/candidates/", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_get_nonexistent_candidate(client):
    response = client.get("/api/candidates/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_candidate_invalid_payload(client):
    # Invalid candidate type
    response = client.post("/api/candidates/", json={
        "full_name": "Invalid Candidate",
        "email": "invalid@example.com",
        "candidate_type": "veteran",  # Not in enum
    })
    assert response.status_code == 422
