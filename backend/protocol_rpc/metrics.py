from prometheus_client import Counter, Histogram, Gauge, generate_latest
from flask import Response

# Initialize metrics
REQUEST_COUNT = Counter(
    'rpc_server_request_count',
    'Total number of RPC requests',
    ['method']
)

ERROR_COUNT = Counter(
    'rpc_server_error_count',
    'Total number of errors encountered during RPC calls',
    ['method']
)

REQUEST_DURATION = Histogram(
    'rpc_server_duration',
    'Duration of inbound RPC requests in milliseconds',
    ['method'],
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
)

ACTIVE_CONNECTIONS = Gauge(
    'rpc_server_active_connections',
    'Number of active WebSocket connections'
)

# Clear all metrics for testing
def clear_metrics():
    from prometheus_client import REGISTRY
    for collector in list(REGISTRY._collector_to_names.keys()):
        REGISTRY.unregister(collector)
    REGISTRY.register(REQUEST_COUNT)
    REGISTRY.register(ERROR_COUNT)
    REGISTRY.register(REQUEST_DURATION)
    REGISTRY.register(ACTIVE_CONNECTIONS)

def init_metrics(app):
    @app.route('/metrics')
    def metrics():
        return Response(generate_latest(), mimetype='text/plain')
