"""Command line entrypoint of package."""

import os
from pathlib import Path
from typing import Union

from sphere_aae.interface.help import HELP
from sphere_aae.interface.package import package
from sphere_aae.support.argparse import ArgumentParser


def main(argv):
    """Parse command line arguments and call `sphere_aae.interface.package`."""
    parser = ArgumentParser("Astro Agent Edge (AAE) Package CLI")

    def _parse_package_config(path: Union[str, Path]) -> Path:
        path = Path(path)
        if not path.exists():
            raise ValueError(
                f"Path {str(path)} is expected to be a JSON file, but the file does not exist."
            )
        if not path.is_file():
            raise ValueError(f"Path {str(path)} is expected to be a JSON file.")
        return path

    def _parse_sphere_aae_source_dir(path: str) -> Path:
        os.environ["SPHERE_AAE_SOURCE_DIR"] = path
        return Path(path)

    def _parse_output(path: Union[str, Path]) -> Path:
        path = Path(path)
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
        return path

    parser.add_argument(
        "--package-config",
        type=_parse_package_config,
        default="sphere-aae-package-config.json",
        help=HELP["config_package"] + ' (default: "%(default)s")',
    )
    parser.add_argument(
        "--sphere-aae-source-dir",
        type=_parse_sphere_aae_source_dir,
        default=os.environ.get("SPHERE_AAE_SOURCE_DIR", None),
        help=HELP["sphere_aae_source_dir"]
        + " (default: the $SPHERE_AAE_SOURCE_DIR environment variable)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=_parse_output,
        default="dist",
        help=HELP["output_package"] + ' (default: "%(default)s")',
    )
    parsed = parser.parse_args(argv)
    if parsed.sphere_aae_source_dir is None:
        raise ValueError(
            "Astro Agent Edge (AAE) home is not specified. "
            "Please obtain a copy of Astro Agent Edge (AAE) source code by "
            "cloning https://github.com/sphere-aae/sphere-aae, and set environment variable "
            '"SPHERE_AAE_SOURCE_DIR=path/to/sphere-aae"'
        )
    package(
        package_config_path=parsed.package_config,
        sphere_aae_source_dir=parsed.sphere_aae_source_dir,
        output=parsed.output,
    )
