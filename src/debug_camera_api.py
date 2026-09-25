from fastapi.testclient import TestClient
from src.api import app
import json
import time

with TestClient(app) as client:
    time.sleep(5)
    response = client.get('/cameras')
    print('STATUS:', response.status_code)
    print(json.dumps(response.json(), indent=2))
