import asyncio
import functools
import sys


def _drop_loop_keyword(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        kwargs.pop("loop", None)
        return func(*args, **kwargs)

    return wrapper


def patch_websockets_asyncio():
    if sys.version_info < (3, 10) or getattr(asyncio, "_wearnav_loop_patch", False):
        return

    for name in (
        "Event",
        "Lock",
        "Queue",
        "StreamReader",
        "wait",
        "wait_for",
        "sleep",
        "shield",
    ):
        setattr(asyncio, name, _drop_loop_keyword(getattr(asyncio, name)))

    asyncio._wearnav_loop_patch = True

