from yn.main import app


def test_oauth2_password_flow_uses_relative_login_url() -> None:
    security_schemes = app.openapi()["components"]["securitySchemes"]
    password_flow = security_schemes["OAuth2PasswordBearer"]["flows"]["password"]

    assert password_flow["tokenUrl"] == "auth/login"


def test_protected_route_uses_oauth2_security_scheme() -> None:
    operation = app.openapi()["paths"]["/users/me"]["get"]

    assert operation["security"] == [{"OAuth2PasswordBearer": []}]
