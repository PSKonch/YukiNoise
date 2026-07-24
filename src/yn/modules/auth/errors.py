from yn.shared.errors import AppError


class InvalidCredentialsError(AppError):
    status_code = 401
    code = "invalid_credentials"
    detail = "Incorrect email or password"
    headers = {"WWW-Authenticate": "Bearer"}


class InvalidAccessTokenError(AppError):
    status_code = 401
    code = "invalid_access_token"
    detail = "Could not validate access token"
    headers = {"WWW-Authenticate": "Bearer"}


class AccessTokenExpiredError(AppError):
    status_code = 401
    code = "access_token_expired"
    detail = "Access token has expired"
    headers = {"WWW-Authenticate": "Bearer"}


class InvalidRefreshTokenError(AppError):
    status_code = 401
    code = "invalid_refresh_token"
    detail = "Refresh token is invalid, expired, or revoked"
    headers = {"WWW-Authenticate": "Bearer"}
