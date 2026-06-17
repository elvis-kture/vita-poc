class AppError(Exception):
    status_code = 500
    detail = "Internal server error"


class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found"


class SoldOutError(AppError):
    status_code = 409
    detail = "No tickets available"


class BookingExpiredError(AppError):
    status_code = 409
    detail = "Booking hold has expired"


class BookingNotPayableError(AppError):
    status_code = 409
    detail = "Booking cannot be paid"
