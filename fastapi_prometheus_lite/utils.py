from typing import Tuple
from starlette.types import Scope


def extract_path_template_from_scope(scope: Scope) -> Tuple[bool, str]:
    """
    Try to extract the route path template from the ASGI scope.
    Extraction will work only on APIRoute

    This function attempts to retrieve the standardized path format (e.g., "/users/{id}")
    from the 'route' object in the ASGI scope. This is typically present when the request
    has been routed through FastAPI or Starlette. If extraction fails (e.g., in 404 cases
    or middleware routes), the function falls back to returning the raw request path.

    :param scope: The ASGI scope dictionary containing metadata about the request
    :return: A tuple:
             - True and the path template if found
             - False and the raw request path otherwise
    """
    try:
        return True, scope["route"].path_format
    except (KeyError, AttributeError):
        return False, scope.get("path", "")
