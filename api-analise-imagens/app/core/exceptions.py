class APIException(Exception):
    def __init__(self, status_code: int, detail: str, error_code: str = "INTERNAL_ERROR"):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
