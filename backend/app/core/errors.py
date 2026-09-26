"""Domain errors raised by services and mapped to HTTP responses in main.py."""


class DomainError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class ValidationFailedError(DomainError):
    status_code = 422
    code = "validation_failed"


class PayloadTooLargeError(DomainError):
    status_code = 413
    code = "payload_too_large"


class UnsupportedMediaError(DomainError):
    status_code = 415
    code = "unsupported_media_type"
