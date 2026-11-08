import io
import uuid
import docx
import fitz
import pytest


def create_sample_pdf(text: str = "Jane Doe\nSenior Software Engineer\nPython, FastAPI, React") -> bytes:
    """Generate valid in-memory PDF with readable text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_sample_docx(text: str = "Jane Doe\nSenior Cloud Architect") -> bytes:
    """Generate valid in-memory DOCX with paragraphs and a table."""
    doc = docx.Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)

    table = doc.add_table(rows=1, cols=2)
    row = table.rows[0]
    row.cells[0].text = "Core Competencies"
    row.cells[1].text = "AWS, Kubernetes, Terraform"

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


@pytest.fixture
def candidate_id(client):
    """Helper fixture to create a valid candidate for upload tests."""
    unique_email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/candidates/", json={
        "full_name": "Test Candidate",
        "email": unique_email,
        "candidate_type": "experienced",
    })
    assert res.status_code == 201
    return res.json()["id"]


def test_upload_pdf_success(client, candidate_id):
    pdf_content = create_sample_pdf("Sarah Connor\nCybernetics Specialist\nAutonomous Systems, Defense")
    files = {"file": ("sarah_connor_resume.pdf", pdf_content, "application/pdf")}
    data = {"candidate_id": candidate_id}

    response = client.post("/api/resumes/upload", data=data, files=files)
    assert response.status_code == 201
    body = response.json()

    assert body["candidate_id"] == candidate_id
    assert body["original_filename"] == "sarah_connor_resume.pdf"
    assert body["file_type"] == "pdf"
    assert body["upload_status"] == "completed"
    assert "Sarah Connor" in body["extracted_text"]
    assert "Cybernetics Specialist" in body["extracted_text"]
    assert "id" in body

    # Verify retrieval via GET /api/resumes/{id}/text
    resume_id = body["id"]
    text_res = client.get(f"/api/resumes/{resume_id}/text")
    assert text_res.status_code == 200
    text_body = text_res.json()
    assert text_body["id"] == resume_id
    assert text_body["candidate_id"] == candidate_id
    assert text_body["original_filename"] == "sarah_connor_resume.pdf"
    assert "Sarah Connor" in text_body["extracted_text"]
    assert "Sarah Connor" in text_body["normalized_text"]


def test_upload_docx_success(client, candidate_id):
    docx_content = create_sample_docx("Michael Scott\nRegional Manager\nLeadership, Sales Strategy")
    files = {"file": ("michael_scott_resume.docx", docx_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    data = {"candidate_id": candidate_id}

    response = client.post("/api/resumes/upload", data=data, files=files)
    assert response.status_code == 201
    body = response.json()

    assert body["candidate_id"] == candidate_id
    assert body["original_filename"] == "michael_scott_resume.docx"
    assert body["file_type"] == "docx"
    assert body["upload_status"] == "completed"
    assert "Michael Scott" in body["extracted_text"]
    assert "Core Competencies" in body["extracted_text"]

    # Verify retrieval via GET /api/resumes/{id}/text
    resume_id = body["id"]
    text_res = client.get(f"/api/resumes/{resume_id}/text")
    assert text_res.status_code == 200
    assert "Michael Scott" in text_res.json()["extracted_text"]


def test_upload_unsupported_extension(client, candidate_id):
    txt_content = b"Plain text resume content"
    files = {"file": ("resume.txt", txt_content, "text/plain")}
    data = {"candidate_id": candidate_id}

    response = client.post("/api/resumes/upload", data=data, files=files)
    assert response.status_code == 400
    assert "Only .pdf and .docx files are permitted" in response.json()["detail"]


def test_upload_mismatched_content_fake_pdf(client, candidate_id):
    # A text file disguised with a .pdf extension
    fake_pdf = b"This is not a real PDF file despite the extension"
    files = {"file": ("fake_resume.pdf", fake_pdf, "application/pdf")}
    data = {"candidate_id": candidate_id}

    response = client.post("/api/resumes/upload", data=data, files=files)
    assert response.status_code == 400
    assert "does not match a valid PDF header" in response.json()["detail"]


def test_upload_mismatched_content_fake_docx(client, candidate_id):
    # Plain text file disguised with a .docx extension
    fake_docx = b"This is not a zip/docx file"
    files = {"file": ("fake_resume.docx", fake_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    data = {"candidate_id": candidate_id}

    response = client.post("/api/resumes/upload", data=data, files=files)
    assert response.status_code == 400
    assert "does not match an OpenXML archive header" in response.json()["detail"]


def test_upload_empty_file(client, candidate_id):
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    data = {"candidate_id": candidate_id}

    response = client.post("/api/resumes/upload", data=data, files=files)
    assert response.status_code == 400
    assert "empty (0 bytes)" in response.json()["detail"]


def test_upload_pdf_without_readable_text(client, candidate_id):
    # PDF with an empty page
    doc = fitz.open()
    doc.new_page()
    empty_pdf_bytes = doc.tobytes()
    doc.close()

    files = {"file": ("blank.pdf", empty_pdf_bytes, "application/pdf")}
    data = {"candidate_id": candidate_id}

    response = client.post("/api/resumes/upload", data=data, files=files)
    assert response.status_code == 400
    assert "does not contain readable text" in response.json()["detail"]


def test_upload_oversized_file(client, candidate_id):
    # 5 MB + 100 bytes
    oversized_bytes = b"%PDF-1.4\n" + b"X" * (5 * 1024 * 1024 + 100)
    files = {"file": ("huge_resume.pdf", oversized_bytes, "application/pdf")}
    data = {"candidate_id": candidate_id}

    response = client.post("/api/resumes/upload", data=data, files=files)
    assert response.status_code == 413
    assert "exceeds maximum limit" in response.json()["detail"]


def test_upload_nonexistent_candidate(client):
    pdf_content = create_sample_pdf("Ghost Candidate")
    files = {"file": ("resume.pdf", pdf_content, "application/pdf")}
    data = {"candidate_id": 999999}

    response = client.post("/api/resumes/upload", data=data, files=files)
    assert response.status_code == 404
    assert "Candidate with id 999999 not found" in response.json()["detail"]


def test_get_nonexistent_resume_text(client):
    response = client.get("/api/resumes/999999/text")
    assert response.status_code == 404
    assert "Resume with id 999999 not found" in response.json()["detail"]


def test_normalize_text_utility():
    from app.services.document_parser import normalize_text
    sample = (
        "Jane Doe\n"
        "Results-driven soft-\nware engineer.\n\n"
        "Experience:\n"
        "• Imple-\nmented CI/CD pipelines.\n"
        "• Cross-\nfunctional collaboration."
    )
    result = normalize_text(sample)
    assert "software engineer" in result
    assert "Implemented CI/CD" in result
    assert "Cross-functional" in result
    assert "Experience:" in result
    assert "•" in result
