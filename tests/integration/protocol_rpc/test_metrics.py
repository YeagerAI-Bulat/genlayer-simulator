import pytest

def test_metrics_endpoint(client):
    response = client.get('/metrics')
    assert response.status_code == 200
    assert response.mimetype == 'text/plain; version=0.0.4; charset=utf-8'
    assert b'rpc_server_requests_total' in response.data
    assert b'rpc_server_active_connections' in response.data
    assert b'rpc_server_request_duration_seconds' in response.data