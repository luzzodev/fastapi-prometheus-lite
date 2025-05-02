import typing
from abc import ABC, abstractmethod

from starlette.requests import HTTPConnection
from starlette.types import Scope

from ..utils import extract_path_template_from_scope


class MetricsContext(HTTPConnection):
    """
    A structured context object for accessing metric-related information
    from the ASGI request scope.

    This class extends `starlette.requests.HTTPConnection` and provides
    convenient, typed access to Prometheus-relevant request and response data,
    such as request duration, status code, HTTP method, and matched route template.
    """

    def __init__(self, scope: Scope):
        """
        Initialize the MetricsContext with an ASGI scope.

        :param scope: The ASGI scope object passed by the framework.
        :type scope: Scope
        """
        super().__init__(scope)

    @property
    def global_active_requests(self) -> int:
        """
        The number of active requests globally, extracted from the metrics context.

        This is lazily evaluated and cached after first access.

        :return: The current number of active requests.
        :rtype: int
        """
        if not hasattr(self, "_global_active_requests"):
            self._global_active_requests = self.scope["metrics_context"]["global_active_requests"]
        return self._global_active_requests

    @property
    def matched_path_template(self) -> tuple[bool, str]:
        """
        The path template matched by the router, if available.

        This helps group metrics by route template (e.g., `/users/{id}`).

        :return: A tuple containing a boolean indicating if the match succeeded,
            and the matched path template string.
        :rtype: tuple[bool, str]
        """
        if not hasattr(self, "_matched_path_template"):
            self._matched_path_template = extract_path_template_from_scope(self.scope)
        return self._matched_path_template

    @property
    def request_method(self) -> str:
        """
        The HTTP method used for the request (e.g., GET, POST).

        :return: The HTTP method as a string.
        :rtype: str
        """
        return typing.cast(str, self.scope["method"])

    @property
    def request_duration(self):
        """
        The duration of the request in seconds.

        Extracted from the scope, where middleware stores it after response.

        :return: The request duration.
        :rtype: float
        """
        if not hasattr(self, "_request_duration"):
            self._request_duration = self.scope["metrics_context"]["request_duration"]
        return self._request_duration

    @property
    def response_status_code(self) -> int:
        """
        The HTTP response status code for the request.

        :return: The status code as an integer (e.g., 200, 404).
        :rtype: int
        """
        if not hasattr(self, "_response_status_code"):
            self._response_status_code = self.scope["metrics_context"]["status_code"]
        return self._response_status_code


class MetricBase(ABC):
    """
    Abstract base class for post-request metric collectors.

    Classes that inherit from MetricBase are called after the response is complete,
    and receive a `MetricsContext` containing request and response metadata.
    """

    @abstractmethod
    def __call__(self, metrics_context: MetricsContext):
        """
        Collect metrics using the provided metrics context.

        :param metrics_context: A fully populated MetricsContext object.
        :type metrics_context: MetricsContext
        """
        pass


class LiveMetricBase(ABC):
    """
    Abstract base class for live (in-request) metric collectors.

    These classes are used during the lifecycle of a request, typically to manage
    active counters, timers, or other live metrics. They are expected to be used
    as context managers and receive only the raw ASGI scope.
    """

    def __init__(self):
        """
        Initialize the live metric base with an empty ASGI scope.
        """
        self._scope: Scope = {}

    def update_scope(self, scope: Scope):
        """
        Update the ASGI scope for this metric collector.

        :param scope: The current request's ASGI scope.
        :type scope: Scope
        """
        self._scope = scope

    @abstractmethod
    def __enter__(self) -> "LiveMetricBase":
        """
        Enter the metric lifecycle context.

        Called at the beginning of the request. Should be implemented
        to start timers, increment counters, or allocate resources.

        :return: The metric instance itself.
        :rtype: LiveMetricBase
        """
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the metric lifecycle context.

        Called at the end of the request. Should be implemented
        to stop timers, decrement counters, or clean up state.

        :param exc_type: Exception type (if any)
        :param exc_val: Exception value (if any)
        :param exc_tb: Exception traceback (if any)
        """
        pass
