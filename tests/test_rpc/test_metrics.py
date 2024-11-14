import os
import pytest
from backend.protocol_rpc.server import create_app

os.environ.update({
    "LOGCONFIG": "test",
    "DBUSER": "test",
    "DBPASSWORD": "test",
    "DBHOST": "localhost",
    "VSCODEDEBUG": "false",
    "RPCPORT": "8545",
    "FLASK_LOG_LEVEL": "INFO",
    "TESTING": "true"
})
from backend.protocol_rpc.metrics import REQUEST_COUNT, ERROR_COUNT, REQUEST_DURATION, ACTIVE_CONNECTIONS, clear_metrics
from backend.protocol_rpc.types import EndpointResult, EndpointResultStatus

def test_metrics_endpoint():
    # Clear any existing metrics
    clear_metrics()
    
    # Create test app
    app, _, _, msg_handler, *_ = create_app(testing=True)
    
    # Create test client
    client = app.test_client()
    
    # Test initial metrics
    response = client.get('/metrics')
    assert response.status_code == 200
    metrics_text = response.data.decode()
    
    # Verify metrics format
    assert 'rpc_server_request_count' in metrics_text
    assert 'rpc_server_error_count' in metrics_text
    assert 'rpc_server_duration' in metrics_text
    assert 'rpc_server_active_connections' in metrics_text
    
    # Test metrics recording
    test_function = "test_function"
    msg_handler.start_times[test_function] = 0  # Simulate start time
    
    # Test successful request
    msg_handler.send_message(test_function, EndpointResult(EndpointResultStatus.SUCCESS, "test"))
    
    # Test error request
    msg_handler.send_message(test_function, EndpointResult(EndpointResultStatus.ERROR, "test error"))
    
    # Get updated metrics
    response = client.get('/metrics')
    metrics_text = response.data.decode()
    
    # Verify request count
    assert 'rpc_server_request_count_total{method="test_function"} 2.0' in metrics_text
    
    # Verify error count
    assert 'rpc_server_error_count_total{method="test_function"} 1.0' in metrics_text
    
    # Verify duration metrics exist
    assert 'rpc_server_duration_bucket{le="10.0",method="test_function"}' in metrics_text
    assert 'rpc_server_duration_count{method="test_function"}' in metrics_text
    assert 'rpc_server_duration_sum{method="test_function"}' in metrics_text
