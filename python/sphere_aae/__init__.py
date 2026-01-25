"""MLC Chat python package.

MLC Chat is the app runtime of Astro Agent Edge (AAE).
"""

from tvm import register_global_func

from . import protocol, serve
from .libinfo import __version__
from .serve import AsyncSphereAaeEngine, SphereAaeEngine


@register_global_func("runtime.disco.create_socket_session_local_workers", override=True)
def _create_socket_session_local_workers(num_workers):
    """Create the local session for each distributed node over socket session."""
    from tvm.runtime.disco import (  # pylint: disable=import-outside-toplevel
        ProcessSession,
    )

    return ProcessSession(num_workers, num_groups=1, entrypoint="sphere_aae.cli.worker")
