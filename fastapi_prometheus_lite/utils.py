from typing import Tuple

from starlette.types import Scope


def extract_path_template_from_scope(scope: Scope) -> Tuple[bool, str]:
    """
    Extract the matched route path template from the ASGI scope.

    This function attempts to retrieve the path template (e.g., "/users/{id}")
    that was matched during routing. It expects the 'matched_path_template'
    key to be present in the scope, which can be injected via a patched
    Route.matches() method.

    This is useful for logging, tracing, or metrics that depend on route templates
    rather than raw paths.

    :param scope: The ASGI scope dictionary containing metadata about the request.
    :return: A tuple:
             - (True, path_template) if a matched path template is found.
             - (False, raw_path) if no template is available.
    """
    path_template = scope.get("matched_path_template")
    if path_template is None:
        # Fall back to raw path if no template was injected
        return False, scope.get("path", "")
    return True, path_template
