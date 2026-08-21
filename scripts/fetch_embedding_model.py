#!/usr/bin/env python
"""Fetch and compress the embedding model, at build time (§14 Phase 3).

The model ships *inside* the image so that search works with the network
unplugged (NFR-06). What ships is not the published file: 512MB of float32 would
blow the 400MB image target (§5.3) on its own.

So it is compressed here, twice over:

* **truncated to 128 of its 256 dimensions.** potion models are trained so that
  a prefix of the vector is still a usable vector, and measurement bears it out
  -- on a ranking task 128 dimensions scored the same as the full 256, while 64
  did not.
* **quantised to int8** with a single scale for the whole matrix.

512MB becomes 64MB, and the meaning survives: 「会社」 and 「企業」 stay close
although they share no character.

Nothing here runs at request time, and numpy is not in the runtime image: the
int8 matrix is read directly (``ontoforge.semantic.npy``), leaving ``tokenizers``
as the only inference dependency. No inference runtime, and identical behaviour
on amd64 and arm64.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO = "minishlab/potion-multilingual-128M"
REVISION = "main"
#: Only what inference needs. The published repository also carries ONNX and
#: PyTorch copies of the same weights, which would double the download.
SOURCE_FILES = ("config.json", "tokenizer.json", "model.safetensors")

#: Measured: 128 ranks as well as the full 256 on a retrieval task, 64 does not.
TARGET_DIMENSIONS = 128
INT8_MAX = 127
DOWNLOAD_TIMEOUT_SECONDS = 900


class FetchError(RuntimeError):
    """Raised when the model cannot be obtained or is not what was expected."""


def download(name: str, *, repo: str = REPO, revision: str = REVISION) -> bytes:
    url = f"https://huggingface.co/{repo}/resolve/{revision}/{name}"
    request = urllib.request.Request(url, headers={"User-Agent": "ontoforge-build"})
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            return bytes(response.read())
    except (urllib.error.URLError, TimeoutError) as error:
        raise FetchError(f"could not fetch {url}: {error}") from error


def load_matrix(payload: bytes) -> Any:
    """The embedding matrix out of a safetensors blob, as numpy."""
    import numpy as np
    from safetensors.numpy import load

    tensors = load(payload)
    for key in ("embeddings", "embedding", "weight"):
        if key in tensors:
            return np.asarray(tensors[key], dtype=np.float32)
    if len(tensors) == 1:
        return np.asarray(next(iter(tensors.values())), dtype=np.float32)
    raise FetchError(f"no embedding matrix in the model file; found {sorted(tensors)}")


def compress(matrix: Any, *, dimensions: int) -> tuple[Any, float]:
    """Truncate to ``dimensions`` and quantise to int8."""
    import numpy as np

    if matrix.ndim != 2:
        raise FetchError(f"expected a 2-D embedding matrix, got shape {matrix.shape}")
    if dimensions > matrix.shape[1]:
        raise FetchError(
            f"cannot truncate to {dimensions} dimensions; the model has {matrix.shape[1]}"
        )

    truncated = matrix[:, :dimensions]
    peak = float(np.abs(truncated).max())
    if peak == 0.0:
        raise FetchError("the embedding matrix is empty")

    scale = peak / INT8_MAX
    quantised = np.clip(np.round(truncated / scale), -INT8_MAX, INT8_MAX).astype(np.int8)
    return quantised, scale


def write(
    out: Path, *, matrix: Any, scale: float, tokenizer: bytes, config: dict[str, Any]
) -> None:
    import numpy as np

    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "embeddings.i8.npy", matrix)
    (out / "tokenizer.json").write_bytes(tokenizer)
    (out / "meta.json").write_text(
        json.dumps(
            {
                "name": REPO.rsplit("/", 1)[-1],
                "source": f"{REPO}@{REVISION}",
                "dimensions": int(matrix.shape[1]),
                "vocabulary": int(matrix.shape[0]),
                "original_dimensions": int(config.get("hidden_dim", matrix.shape[1])),
                "scale": scale,
                "quantisation": "int8",
                # Recorded so the runtime can refuse to mean-pool a model that
                # needs weighting it does not apply.
                "sif_coefficient": config.get("sif_coefficient"),
                "apply_zipf": config.get("apply_zipf"),
                "normalize": config.get("normalize", True),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def fetch(out: Path, *, dimensions: int = TARGET_DIMENSIONS) -> dict[str, Any]:
    config = json.loads(download("config.json").decode("utf-8"))
    if config.get("sif_coefficient") or config.get("apply_zipf"):
        # The runtime does a plain mean; a model wanting weighted pooling would
        # be silently mis-embedded, so refuse it rather than ship it.
        raise FetchError(
            "this model expects weighted pooling, which the runtime does not implement"
        )

    tokenizer = download("tokenizer.json")
    matrix = load_matrix(download("model.safetensors"))
    quantised, scale = compress(matrix, dimensions=dimensions)
    write(out, matrix=quantised, scale=scale, tokenizer=tokenizer, config=config)

    return {
        "vocabulary": int(quantised.shape[0]),
        "dimensions": int(quantised.shape[1]),
        "original_mb": matrix.nbytes / 1e6,
        "written_mb": sum(path.stat().st_size for path in out.iterdir()) / 1e6,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="where to write the model")
    parser.add_argument("--dimensions", type=int, default=TARGET_DIMENSIONS)
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help=(
            "carry on if the model cannot be fetched. The image then falls back "
            "to surface similarity, which is a different feature -- so this is "
            "opt-in rather than the default."
        ),
    )
    arguments = parser.parse_args(argv)

    try:
        result = fetch(arguments.out, dimensions=arguments.dimensions)
    except FetchError as error:
        if arguments.allow_missing:
            print(f"embedding model not fetched: {error}", file=sys.stderr)
            print("search will fall back to surface similarity.", file=sys.stderr)
            return 0
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(
        f"embedding model: {result['vocabulary']} × {result['dimensions']} int8, "
        f"{result['original_mb']:.0f}MB → {result['written_mb']:.0f}MB"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
