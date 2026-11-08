def test_resume_crud_lifecycle(client):
    # 1. Create a candidate first
    cand_res = client.post("/api/candidates/", json={
        "full_name": "Alex Johnson",
        "email": "alex.johnson@example.com",
        "candidate_type": "fresher",
    })
    assert cand_res.status_code == 201
    candidate_id = cand_res.json()["id"]

    # 2. Create resume metadata
    resume_payload = {
        "candidate_id": candidate_id,
        "original_filename": "alex_johnson_cv.pdf",
        "file_path": "/uploads/resumes/alex_johnson_cv.pdf",
        "file_type": "pdf",
        "upload_status": "pending",
    }
    create_res = client.post("/api/resumes/", json=resume_payload)
    assert create_res.status_code == 201
    resume_data = create_res.json()
    assert resume_data["candidate_id"] == candidate_id
    assert resume_data["original_filename"] == resume_payload["original_filename"]
    assert resume_data["file_type"] == "pdf"
    assert resume_data["upload_status"] == "pending"
    assert "id" in resume_data
    assert "created_at" in resume_data

    resume_id = resume_data["id"]

    # 3. List resumes
    list_res = client.get("/api/resumes/")
    assert list_res.status_code == 200
    resumes_list = list_res.json()
    assert any(r["id"] == resume_id for r in resumes_list)

    # 4. Get resume by ID
    get_res = client.get(f"/api/resumes/{resume_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == resume_id

    # 5. Delete resume
    del_res = client.delete(f"/api/resumes/{resume_id}")
    assert del_res.status_code == 204

    # 6. Verify deletion
    verify_res = client.get(f"/api/resumes/{resume_id}")
    assert verify_res.status_code == 404


def test_create_resume_nonexistent_candidate(client):
    resume_payload = {
        "candidate_id": 999999,
        "original_filename": "ghost.pdf",
        "file_path": "/uploads/ghost.pdf",
        "file_type": "pdf",
    }
    response = client.post("/api/resumes/", json=resume_payload)
    assert response.status_code == 404
    assert "Candidate with id 999999 not found" in response.json()["detail"]


def test_get_and_delete_nonexistent_resume(client):
    get_res = client.get("/api/resumes/999999")
    assert get_res.status_code == 404

    del_res = client.delete("/api/resumes/999999")
    assert del_res.status_code == 404

