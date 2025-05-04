import typing
from abc import ABC, abstractmethod

from prometheus_client.metrics import Collector, CollectorRegistry
from starlette.requests import HTTPConnection
from starlette.responses import Response
from starlette.types import Scope

from fastapi_prometheus_lite.utils import extract_path_template_from_scope


class MetricsContext(HTTPConnection):
    """
    A structured context object for accessing metric-related information
    from the ASGI request scope.

    This class extends `starlette.requests.HTTPConnection` and provides
    convenient, typed access to Prometheus-relevant request and response data,
    such as request duration, status code, HTTP method, and matched route template.
    """

    def __init__(self, scope: Scope, response: typing.Optional[Response] = None):
        """
        Initialize the MetricsContext with an ASGI scope.

        :param scope: The ASGI scope object passed by the framework.
        :type scope: Scope

        :param response: The response object from the framework.
        :type scope: Optional[Response]
        """
        super().__init__(scope)
        self._matched_path_template: tuple[bool, str] = extract_path_template_from_scope(self.scope)
        self._response: Response = response or Response(status_code=500)

    @property
    def response(self) -> typing.Optional[Response]:
        return self._response

    @property
    def global_active_requests(self) -> int:
        """
        The number of active requests globally, extracted from the metrics context.

        This is lazily evaluated and cached after first access.

        :return: The current number of active requests.
        :rtype: int
        """
        return self.scope["metrics_context"]["global_active_requests"]

    @property
    def matched_path_template(self) -> tuple[bool, str]:
        """
        The path template matched by the router, if available.

        This helps group metrics by route template (e.g., `/users/{id}`).

        :return: A tuple containing a boolean indicating if the match succeeded,
            and the matched path template string. If unmatched, raw_path will be returned instead of the template one.
        :rtype: tuple[bool, str]
        """
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
        return self.scope["metrics_context"]["request_duration"]


class RegistrableCollector(ABC):
    """
    Mixin that gives you:

    - a `.metric: Collector` attribute (default None)
    - a `.register(registry)` method to hook that collector into any registry
    """

    _metric: Collector | None = None

    def register(self, registry: CollectorRegistry) -> bool:
        """
        Register `self._metric` into the given registry.
        Safe to call multiple times.
        """
        if self._metric is None:
            raise ValueError(f"{self.__class__.__name__}.metric is not initialized")
        try:
            registry.register(self._metric)
        except ValueError:
            # already registered; ignore
            return False
        return True


class CollectorBase(ABC):
    """
    Abstract base class for post-request metric collectors.

    Classes that inherit from CollectorBase are called after the response is complete,
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


class LiveCollectorBase(ABC):
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
    def __enter__(self) -> "LiveCollectorBase":
        """
        Enter the collector lifecycle context.

        Called at the beginning of the request. Should be implemented
        to start timers, increment counters, or allocate resources.

        :return: The collector instance itself.
        :rtype: LiveCollectorBase
        """
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the collector lifecycle context.

        Called at the end of the request. Should be implemented
        to stop timers, decrement counters, or clean up state.

        :param exc_type: Exception type (if any)
        :param exc_val: Exception value (if any)
        :param exc_tb: Exception traceback (if any)
        """
        pass
