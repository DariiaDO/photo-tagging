from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    response.data = {
        "status": "error",
        "message": _message_from_detail(response.data),
        "details": response.data,
    }
    return response


def error_response(message: str, details=None) -> dict:
    return {
        "status": "error",
        "message": message,
        "details": details or {},
    }


def _message_from_detail(data) -> str:
    if isinstance(data, dict):
        detail = data.get("detail")
        if detail:
            return str(detail)
        return "Request validation failed."
    return str(data or "Request failed.")
