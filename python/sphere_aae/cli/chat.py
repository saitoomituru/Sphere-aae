"""Command line entrypoint of chat."""

from sphere_aae.interface.chat import ModelConfigOverride, chat
from sphere_aae.interface.help import HELP
from sphere_aae.support.argparse import ArgumentParser


def main(argv):
    """Parse command line arguments and call `sphere_aae.interface.chat`."""
    parser = ArgumentParser("Astro Agent Edge (AAE) Chat CLI")

    parser.add_argument(
        "model",
        type=str,
        help=HELP["model"] + " (required)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help=HELP["device_deploy"] + ' (default: "%(default)s")',
    )
    parser.add_argument(
        "--model-lib",
        type=str,
        default=None,
        help=HELP["model_lib"] + ' (default: "%(default)s")',
    )
    parser.add_argument(
        "--overrides",
        type=ModelConfigOverride.from_str,
        default="",
        help=HELP["modelconfig_overrides"] + ' (default: "%(default)s")',
    )
    parsed = parser.parse_args(argv)
    chat(
        model=parsed.model,
        device=parsed.device,
        model_lib=parsed.model_lib,
        overrides=parsed.overrides,
    )
