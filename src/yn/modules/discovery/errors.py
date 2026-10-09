from yn.shared.errors import AppError


class DiscoveryInvalidModelOutputError(AppError):
    status_code = 502
    code = "discovery_invalid_model_output"
    detail = "The model output was invalid or could not be processed"


class DiscoveryProviderUnavailableError(AppError):
    status_code = 503
    code = "discovery_provider_unavailable"
    detail = "The discovery provider is currently unavailable"


class DiscoveryDisabledError(AppError):
    status_code = 503
    code = "discovery_disabled"
    detail = "The discovery service is currently disabled"


class DiscoveryIndexUnavailableError(AppError):
    status_code = 503
    code = "discovery_index_unavailable"
    detail = "The discovery index is currently unavailable"
