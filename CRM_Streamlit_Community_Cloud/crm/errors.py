class ConfigurationError(ValueError):
    """Configuração inválida; nunca permite fallback silencioso para demo."""


class ContractError(ValueError):
    """Resultado semântico inválido, inconsistente ou não homologado."""


class AccessDenied(PermissionError):
    """Identidade ou autorização insuficiente."""
