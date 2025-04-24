# Type aliases adapted from Starlette (https://github.com/encode/starlette)
# Licensed under MIT License

import typing


Scope = typing.MutableMapping[str, typing.Any]
Message = typing.MutableMapping[str, typing.Any]

Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[[Message], typing.Awaitable[None]]
