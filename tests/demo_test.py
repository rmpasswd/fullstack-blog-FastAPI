from fastapi import FastAPI
from fastapi.testclient import TestClient

qq = FastAPI()

@qq.get("/")
def home_qq():
    return {"message": "Mike is testing the mike"}

# Test Section
clientt = TestClient(qq)
def test_home():
    response = clientt.get("/")
    assert response.status_code == 200

