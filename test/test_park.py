import pytest
from flask.testing import FlaskClient
from app import app

@pytest.fixture
def client():
    return app.test_client()

# TESTING PROJECT API (ParkAPI)

def test_park_api_sad_paths(client: FlaskClient):
    resp = client.get('/park', json={'username': 'username'}) # this should fail
    assert resp.status_code == 405 # we cannot perform a get
    resp = client.patch('/park', json={'username': 'username'}) # this should fail
    assert resp.status_code == 405 # we cannot perform a patch
    resp = client.delete('/park', json={'username': 'username'}) # this should fail
    assert resp.status_code == 405 # we cannot perform a delete
    resp = client.put('/park', json={'username': 'username'}) # this should fail
    assert resp.status_code == 405 # we cannot perform a put


