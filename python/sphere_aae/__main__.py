"""Entrypoint of all CLI commands from Astro Agent Edge (AAE)"""

import sys

from sphere_aae.support import logging
from sphere_aae.support.argparse import ArgumentParser

logging.enable_logging()


def main():
    """Entrypoint of all CLI commands from Astro Agent Edge (AAE)"""
    parser = ArgumentParser("Astro Agent Edge (AAE) Command Line Interface.")
    parser.add_argument(
        "subcommand",
        type=str,
        choices=[
            "compile",
            "convert_weight",
            "gen_config",
            "chat",
            "serve",
            "package",
            "calibrate",
            "router",
        ],
        help="Subcommand to to run. (choices: %(choices)s)",
    )
    parsed = parser.parse_args(sys.argv[1:2])
    # pylint: disable=import-outside-toplevel
    if parsed.subcommand == "compile":
        from sphere_aae.cli import compile as cli

        cli.main(sys.argv[2:])
    elif parsed.subcommand == "convert_weight":
        from sphere_aae.cli import convert_weight as cli

        cli.main(sys.argv[2:])
    elif parsed.subcommand == "gen_config":
        from sphere_aae.cli import gen_config as cli

        cli.main(sys.argv[2:])
    elif parsed.subcommand == "chat":
        from sphere_aae.cli import chat as cli

        cli.main(sys.argv[2:])
    elif parsed.subcommand == "serve":
        from sphere_aae.cli import serve as cli

        cli.main(sys.argv[2:])
    elif parsed.subcommand == "package":
        from sphere_aae.cli import package as cli

        cli.main(sys.argv[2:])
    elif parsed.subcommand == "calibrate":
        from sphere_aae.cli import calibrate as cli

        cli.main(sys.argv[2:])
    elif parsed.subcommand == "router":
        from sphere_aae.cli import router as cli

        cli.main(sys.argv[2:])
    else:
        raise ValueError(f"Unknown subcommand {parsed.subcommand}")
    # pylint: enable=import-outside-toplevel


if __name__ == "__main__":
    main()
