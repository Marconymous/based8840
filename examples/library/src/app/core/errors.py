"""Domain exception hierarchy. api/errors.py maps each class to one AIP status."""


class LibraryError(Exception):
    """Base class for every error the application raises on purpose."""


class NotFoundError(LibraryError):
    """The requested resource does not exist."""


class AlreadyExistsError(LibraryError):
    """A resource with the requested ID already exists."""


class AbortedError(LibraryError):
    """Concurrency conflict, e.g. the client sent a stale etag."""


class FailedPreconditionError(LibraryError):
    """The resource is not in a state that allows the operation."""


class InvalidArgumentError(LibraryError):
    """The client sent a malformed request (bad filter, page token, field mask, ...)."""
