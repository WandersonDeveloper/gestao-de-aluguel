class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class InvalidTransitionError(Exception):
    pass


class UnauthorizedError(Exception):
    pass


class ForbiddenError(Exception):
    pass
