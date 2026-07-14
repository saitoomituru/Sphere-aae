#!/usr/bin/env python3
"""Build a deterministic, FAM-free Core ML arbiter fixture with MIL."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import coremltools as ct
import numpy as np
from coremltools.converters.mil import Builder as mb
from coremltools.converters.mil.mil import types


INPUT_DIM = 16
HIDDEN_DIM = 32
OUTPUT_DIM = 4


def deterministic_tensors(batch_size: int) -> dict[str, np.ndarray]:
    """Create stable inputs and weights without a framework-specific RNG."""
    w1_index = np.arange(HIDDEN_DIM * INPUT_DIM, dtype=np.float32).reshape(
        HIDDEN_DIM, INPUT_DIM
    )
    w2_index = np.arange(OUTPUT_DIM * HIDDEN_DIM, dtype=np.float32).reshape(
        OUTPUT_DIM, HIDDEN_DIM
    )
    input_index = np.arange(batch_size * INPUT_DIM, dtype=np.float32).reshape(
        batch_size, INPUT_DIM
    )

    return {
        "features": np.sin((input_index + 1.0) * np.float32(0.13)).astype(np.float32),
        "w1": (np.sin((w1_index + 1.0) * np.float32(0.17)) * np.float32(0.18)).astype(
            np.float32
        ),
        "b1": (np.cos((np.arange(HIDDEN_DIM, dtype=np.float32) + 1.0) * 0.11) * 0.05).astype(
            np.float32
        ),
        "w2": (np.cos((w2_index + 1.0) * np.float32(0.19)) * np.float32(0.16)).astype(
            np.float32
        ),
        "b2": (np.sin((np.arange(OUTPUT_DIM, dtype=np.float32) + 1.0) * 0.23) * 0.03).astype(
            np.float32
        ),
    }


def numpy_forward(tensors: dict[str, np.ndarray]) -> np.ndarray:
    hidden = tensors["features"] @ tensors["w1"].T + tensors["b1"]
    hidden = hidden / (np.float32(1.0) + np.exp(-hidden))
    return (hidden @ tensors["w2"].T + tensors["b2"]).astype(np.float32)


def stable_topk(logits: np.ndarray, k: int = 2) -> np.ndarray:
    """Sort by score descending, then expert id ascending for ties."""
    expert_ids = np.arange(logits.shape[1])
    return np.stack(
        [np.lexsort((expert_ids, -row))[:k] for row in logits], axis=0
    ).astype(np.int32)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_model(batch_size: int, tensors: dict[str, np.ndarray]) -> ct.models.MLModel:
    @mb.program(
        input_specs=[mb.TensorSpec(shape=(batch_size, INPUT_DIM), dtype=types.fp32)]
    )
    def program(features):
        hidden = mb.linear(
            x=features,
            weight=tensors["w1"],
            bias=tensors["b1"],
            name="hidden_linear",
        )
        hidden = mb.silu(x=hidden, name="hidden_silu")
        return mb.linear(
            x=hidden,
            weight=tensors["w2"],
            bias=tensors["b2"],
            name="priority_logits",
        )

    model = ct.convert(
        program,
        convert_to="mlprogram",
        compute_precision=ct.precision.FLOAT32,
        minimum_deployment_target=ct.target.macOS13,
    )
    model.author = "Sphere-aae contributors"
    model.short_description = "FAM-free deterministic Core ML arbiter smoke fixture"
    model.input_description["features"] = "Synthetic 16-element signal vector"
    model.output_description["priority_logits"] = "Four synthetic expert priority logits"
    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()

    if args.batch_size <= 0:
        raise ValueError("--batch-size must be positive")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tensors = deterministic_tensors(args.batch_size)
    logits = numpy_forward(tensors)
    topk = stable_topk(logits)
    model_name = f"MinimalArbiterB{args.batch_size}"
    model_path = output_dir / f"{model_name}.mlpackage"
    fixture_path = output_dir / "fixture.json"
    weights_path = output_dir / "fixture.npz"

    model = build_model(args.batch_size, tensors)
    model.save(model_path)
    np.savez(
        weights_path,
        **tensors,
        expected_logits=logits,
        expected_topk=topk,
    )
    fixture = {
        "name": model_name,
        "batch_size": args.batch_size,
        "input_shape": [args.batch_size, INPUT_DIM],
        "output_shape": [args.batch_size, OUTPUT_DIM],
        "features": tensors["features"].reshape(-1).tolist(),
        "expected_logits": logits.reshape(-1).tolist(),
        "expected_topk": topk.reshape(-1).tolist(),
        "model_path": str(model_path),
        "weights_path": str(weights_path),
    }
    fixture_path.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "coremltools_version": ct.__version__,
        "numpy_version": np.__version__,
        "model_name": model_name,
        "batch_size": args.batch_size,
        "fixture_sha256": sha256(fixture_path),
        "weights_sha256": sha256(weights_path),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
