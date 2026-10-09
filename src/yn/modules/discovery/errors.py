from yn.shared.errors import AppError


class DiscoveryInvalidModelOutputError(AppError):
    status_code = 500
    code = "discovery_invalid_model_output"
    detail = "The model output was invalid or could not be processed"


class DiscoveryProviderUnavailableError(AppError):
    status_code = 503
    code = "discovery_provider_unavailable"
    detail = "The discovery provider is currently unavailable"
