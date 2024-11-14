import traceback
import random
import string
import os
import json
from logging.config import dictConfig

from backend.protocol_rpc.message_handler.types import FormattedResponse
from backend.protocol_rpc.types import EndpointResult
from backend.protocol_rpc.metrics import REQUEST_COUNT, ERROR_COUNT, REQUEST_DURATION, ACTIVE_CONNECTIONS
import time

MAX_LOG_MESSAGE_LENGTH = 3000


def setup_logging_config():
    logging_env = os.environ.get("LOGCONFIG", "test")
    file_path = (
        f"backend/protocol_rpc/message_handler/config/logging.{logging_env}.json"
    )
    with open(file_path, "r") as file:
        logging_config = json.load(file)
        dictConfig(logging_config)


def format_response(function_name: str, result: EndpointResult) -> FormattedResponse:
    trace_id = "".join(
        random.choice(string.digits + string.ascii_lowercase) for _ in range(9)
    )
    return FormattedResponse(function_name, trace_id, result)


class MessageHandler:

    status_mappings = {
        "debug": "info",
        "info": "info",
        "success": "info",
        "error": "error",
    }

    def __init__(self, app, socketio):
        self.app = app
        self.socketio = socketio
        setup_logging_config()
        self.start_times = {}

    def socket_emit(self, message):
        self.socketio.emit("status_update", {"message": message})
        ACTIVE_CONNECTIONS.set(len(self.socketio.server.eio.sockets))

    def log_message(self, function_name, result: EndpointResult):
        logging_status = self.status_mappings[result.status.value]
        if hasattr(self.app.logger, logging_status):
            log_method = getattr(self.app.logger, logging_status)
            result_string = str(result)
            function_result = (
                (result_string[:MAX_LOG_MESSAGE_LENGTH] + "...")
                if result_string is not None
                and len(result_string) > MAX_LOG_MESSAGE_LENGTH
                else result_string
            )
            log_method(function_name + ": " + function_result)
        else:
            raise Exception(f"Logger does not have the method {result.status}")

    def send_message(
        self,
        function_name: str,
        result: EndpointResult,
    ):
        REQUEST_COUNT.labels(method=function_name).inc()
        
        if result.status.value == "error":
            ERROR_COUNT.labels(method=function_name).inc()
        
        # Record request duration if we have a start time
        if function_name in self.start_times:
            duration = (time.time() - self.start_times[function_name]) * 1000  # Convert to ms
            REQUEST_DURATION.labels(method=function_name).observe(duration)
            del self.start_times[function_name]
        
        self.log_message(function_name, result)
        formatted_response = format_response(function_name, result)
        self.socket_emit(formatted_response.to_json())
