import os
import sys
import shutil

print("=== Medix AI Migration Verification ===")

# 1. Remove SQLite / SQLAlchemy legacy files
legacy_files = [
    os.path.join("backend", "database.py"),
    os.path.join("backend", "models.py"),
    "medix_ai.db",
    os.path.join("backend", "medix_ai.db")
]

for filepath in legacy_files:
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"[REMOVED] Legacy file: {filepath}")
        except Exception as e:
            print(f"[ERROR] Could not remove {filepath}: {e}")
    else:
        print(f"[OK] Legacy file already removed or absent: {filepath}")

# 2. Add backend to sys.path and import FastAPI app
sys.path.insert(0, os.path.abspath("backend"))

try:
    # pyrefly: ignore [missing-import]
    from main import app
    print("[OK] Successfully imported backend app without SQLAlchemy dependencies.")
except Exception as e:
    print(f"[FAIL] Error importing main app: {e}")
    sys.exit(1)

# 3. Test endpoints using FastAPI TestClient
try:
    from fastapi.testclient import TestClient
    client = TestClient(app)

    # Test Public Health Endpoint
    res = client.get("/health")
    assert res.status_code == 200, f"Expected 200 on /health, got {res.status_code}"
    print("[OK] GET /health (Public) -> Passed")

    # Test Public Symptoms Endpoint
    res = client.get("/api/symptoms")
    assert res.status_code == 200, f"Expected 200 on /api/symptoms, got {res.status_code}"
    print("[OK] GET /api/symptoms (Public) -> Passed")

    # Test Public Diseases Endpoint
    res = client.get("/api/diseases")
    assert res.status_code == 200, f"Expected 200 on /api/diseases, got {res.status_code}"
    print("[OK] GET /api/diseases (Public) -> Passed")

    # Test Protected Endpoint without Authorization header
    res = client.post("/api/analyze-case", json={
        "name": "Test Patient", "age": 35, "location": "Delhi",
        "symptoms": ["fever", "cough"], "medical_history": [],
        "allergies": [], "previous_antibiotics": []
    })
    assert res.status_code in [401, 403], f"Expected 401/403 on protected /api/analyze-case without auth, got {res.status_code}"
    print(f"[OK] POST /api/analyze-case without Auth -> Correctly blocked ({res.status_code})")

    # Test Public Login Endpoint
    res = client.post("/api/auth/login", json={"email": "dr.ai@hospital.org", "password": "password123"})
    assert res.status_code == 200, f"Expected 200 on /api/auth/login, got {res.status_code}"
    data = res.json()
    token = data.get("access_token")
    assert token, "No access_token returned from login"
    print("[OK] POST /api/auth/login (Public) -> Passed, received JWT token")

    # Test Protected Endpoint WITH Authorization header
    res = client.post("/api/analyze-case", headers={"Authorization": f"Bearer {token}"}, json={
        "name": "Test Patient", "age": 35, "location": "Delhi",
        "symptoms": ["fever", "cough"], "medical_history": [],
        "allergies": [], "previous_antibiotics": []
    })
    assert res.status_code == 200, f"Expected 200 on /api/analyze-case with auth, got {res.status_code}: {res.text}"
    print("[OK] POST /api/analyze-case with Bearer Token -> Passed")

    print("\n=== ALL MIGRATION AND AUTHENTICATION TESTS PASSED SUCCESSFULLY! ===")

except Exception as e:
    print(f"[FAIL] Verification test error: {e}")
    sys.exit(1)
