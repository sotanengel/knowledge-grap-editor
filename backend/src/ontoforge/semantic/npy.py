"""Reading the quantised embedding matrix without numpy.

numpy is 68MB in the image and was used for exactly one thing: slicing rows out
of an int8 array and averaging them. The ``.npy`` container is a short header
followed by raw C-order bytes, and int8 rows are just signed bytes, so the file
is read directly instead -- which keeps the image under the 400MB target (§5.3)
and removes a dependency that pulled in a BLAS build per architecture.

The reader is deliberately narrow. It handles the one layout this project
writes, and refuses anything else rather than guessing: a float matrix or a
Fortran-ordered one would otherwise be misread as int8 rows and produce
plausible nonsense.
"""

from __future__ import annotations

import array
import ast
import mmap
import struct
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import BinaryIO, Self

MAGIC = b"\x93NUMPY"
#: The one dtype this reader accepts: single-byte signed, so byte order is moot.
INT8_DESCR = frozenset({"|i1", "i1", "<i1", ">i1", "b"})


class NpyError(ValueError):
    """Raised when the file is not an int8 matrix this reader can use."""


@dataclass(frozen=True, slots=True)
class Header:
    """What the ``.npy`` preamble says about the data that follows."""

    descr: str
    shape: tuple[int, int]
    fortran_order: bool
    offset: int


def parse_header(handle: BinaryIO) -> Header:
    """Read the ``.npy`` preamble, or say why it cannot be used."""
    handle.seek(0)
    if handle.read(6) != MAGIC:
        raise NpyError("not an NPY file")

    major, _minor = struct.unpack("<BB", handle.read(2))
    length_format, length_size = ("<H", 2) if major == 1 else ("<I", 4)
    (header_length,) = struct.unpack(length_format, handle.read(length_size))
    raw = handle.read(header_length).decode("latin-1")

    try:
        described = ast.literal_eval(raw.strip())
    except (SyntaxError, ValueError) as error:
        raise NpyError(f"unreadable NPY header: {error}") from error
    if not isinstance(described, dict):
        raise NpyError("the NPY header is not a mapping")

    shape = described.get("shape")
    if not isinstance(shape, tuple) or len(shape) != 2:
        raise NpyError(f"expected a 2-D matrix, got shape {shape!r}")

    return Header(
        descr=str(described.get("descr", "")),
        shape=(int(shape[0]), int(shape[1])),
        fortran_order=bool(described.get("fortran_order", False)),
        offset=6 + 2 + length_size + header_length,
    )


class Int8Matrix:
    """A memory-mapped int8 matrix, read a row at a time.

    Mapping rather than loading matters: the file is 64MB and only a handful of
    rows are touched per query, so the pages that are never asked for are never
    read.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._handle = self.path.open("rb")
        try:
            header = parse_header(self._handle)
            self._validate(header)
            self.shape = header.shape
            self._offset = header.offset
            self._width = header.shape[1]
            self._map = mmap.mmap(self._handle.fileno(), 0, access=mmap.ACCESS_READ)
        except Exception:
            self._handle.close()
            raise

    def _validate(self, header: Header) -> None:
        if header.descr not in INT8_DESCR:
            raise NpyError(f"expected an int8 matrix, got dtype {header.descr!r}")
        if header.fortran_order:
            raise NpyError("column-major (Fortran-ordered) matrices are not supported")

        rows, width = header.shape
        expected = header.offset + rows * width
        actual = self.path.stat().st_size
        if actual < expected:
            raise NpyError(f"the file is truncated: expected {expected} bytes, found {actual}")

    # ------------------------------------------------------------------ reads

    def row(self, index: int) -> array.array[int]:
        """One row, as signed values."""
        rows = self.shape[0]
        if not 0 <= index < rows:
            raise IndexError(f"row {index} is outside 0..{rows - 1}")
        start = self._offset + index * self._width
        values = array.array("b")
        values.frombytes(self._map[start : start + self._width])
        return values

    def mean(self, indices: list[int]) -> list[float]:
        """The element-wise mean of the given rows, as floats."""
        if not indices:
            return [0.0] * self._width

        totals = [0] * self._width
        for index in indices:
            for position, value in enumerate(self.row(index)):
                totals[position] += value

        count = float(len(indices))
        return [total / count for total in totals]

    # ------------------------------------------------------------------ lifecycle

    def close(self) -> None:
        mapped = getattr(self, "_map", None)
        if mapped is not None:
            mapped.close()
        self._handle.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
