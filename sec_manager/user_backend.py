"""Auth backend that uses current user value set by authentication proxy."""
from functools import wraps
from typing import Callable, Optional, Tuple, TypeVar, Union, cast

from flask import Response
from flask_login import current_user
from requests.auth import AuthBase

CLIENT_AUTH: Optional[Union[Tuple[str, str], AuthBase]] = None


def init_app(_):
    """Initializes authentication backend"""


T = TypeVar("T", bound=Callable)


def requires_authentication(func: T):
    """Decorator for functions that require authentication"""

    @wraps(func)
    def decorated(*args, **kwargs):
        if not current_user.is_anonymous:
            return func(*args, **kwargs)

        return Response("Unauthorized", 401, {"WWW-Authenticate": "Basic"})

    return cast(T, decorated)
