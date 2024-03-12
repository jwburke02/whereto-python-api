import pytest
from flask.testing import FlaskClient
from app import app

@pytest.fixture
def client():
    return app.test_client()

# TESTING PROJECT API (ParkAPI)

def test_detail_api_sad_paths(client: FlaskClient):
    resp = client.get('/detail', json={'username': 'username'}) # this should fail
    assert resp.status_code == 405 # we cannot perform a get
    resp = client.patch('/detail', json={'username': 'username'}) # this should fail
    assert resp.status_code == 405 # we cannot perform a patch
    resp = client.delete('/detail', json={'username': 'username'}) # this should fail
    assert resp.status_code == 405 # we cannot perform a delete
    resp = client.put('/detail', json={'username': 'username'}) # this should fail
    assert resp.status_code == 405 # we cannot perform a put


