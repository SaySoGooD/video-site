class ApplicationError(Exception):
    """Base error for the application layer."""


class AuthenticationError(ApplicationError):
    """The request could not be tied to a valid, logged-in user (-> 401)."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message)


class InvalidCredentialsError(AuthenticationError):
    """Email/password did not match, or the account is inactive (-> 401)."""

    def __init__(self, message: str = "Invalid email or password") -> None:
        super().__init__(message)


class AuthorizationError(ApplicationError):
    """The user is known but not allowed to access the resource (-> 403)."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message)


class EntityNotFoundError(ApplicationError):
    """A requested entity does not exist (-> 404)."""


class UserNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "User not found") -> None:
        super().__init__(message)


class RoleNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "Role not found") -> None:
        super().__init__(message)


class PermissionNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "Permission not found") -> None:
        super().__init__(message)


class SessionNotFoundError(EntityNotFoundError):
    def __init__(self, message: str = "Session not found") -> None:
        super().__init__(message)


class ConflictError(ApplicationError):
    """The requested change conflicts with existing data (-> 409)."""


class EmailAlreadyExistsError(ConflictError):
    def __init__(self, message: str = "A user with this email already exists") -> None:
        super().__init__(message)


class UsernameAlreadyExistsError(ConflictError):
    def __init__(self, message: str = "This username is already taken") -> None:
        super().__init__(message)


class ValidationError(ApplicationError):
    """The input is well-formed but violates a business rule (-> 422)."""


class PasswordMismatchError(ValidationError):
    def __init__(self, message: str = "Passwords do not match") -> None:
        super().__init__(message)
