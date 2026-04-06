from flask import jsonify
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    def __init__(self, status_code, code, message, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self):
        payload = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            payload["error"]["details"] = self.details
        return payload


def raise_bad_request(code, message, details=None):
    raise APIError(400, code, message, details)


def raise_not_found(code, message, details=None):
    raise APIError(404, code, message, details)


def raise_internal_error(message="An unexpected server error occurred.", details=None):
    raise APIError(500, "INTERNAL_SERVER_ERROR", message, details)


def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(error):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        # 兜底处理 Flask / Werkzeug 自带异常
        payload = {
            "error": {
                "code": error.name.upper().replace(" ", "_"),
                "message": error.description,
            }
        }
        return jsonify(payload), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        # 只记录日志，不把内部异常暴露给客户端
        app.logger.exception("Unhandled server error", exc_info=error)
        payload = {
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred.",
            }
        }
        return jsonify(payload), 500
