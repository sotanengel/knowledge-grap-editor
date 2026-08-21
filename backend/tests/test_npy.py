"""Reading the quantised matrix without numpy.

numpy costs 68MB in the image and is used for one thing: slicing rows out of an
int8 array. The file format is simple enough to read directly, so it is -- and
these tests hold that reader to producing exactly what numpy would.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from ontoforge.semantic.npy import Int8Matrix, NpyError, parse_header


def write_npy(
    path: Path, rows: list[list[int]], *, descr: str = "|i1", fortran: bool = False
) -> None:
    shape = (len(rows), len(rows[0]))
    header = f"{{'descr': '{descr}', 'fortran_order': {fortran}, 'shape': {shape}, }}"
    padding = 64 - ((10 + len(header) + 1) % 64)
    header = header + " " * padding + "\n"
    with path.open("wb") as handle:
        handle.write(b"\x93NUMPY\x01\x00")
        handle.write(struct.pack("<H", len(header)))
        handle.write(header.encode("latin-1"))
        for row in rows:
            handle.write(bytes((value & 0xFF) for value in row))


@pytest.fixture
def matrix_file(tmp_path: Path) -> Path:
    path = tmp_path / "m.npy"
    write_npy(path, [[1, -2, 3], [0, 127, -128], [-1, -1, -1]])
    return path


def test_the_header_is_read(matrix_file: Path) -> None:
    with matrix_file.open("rb") as handle:
        header = parse_header(handle)
    assert header.shape == (3, 3)
    assert header.descr == "|i1"
    assert header.offset % 64 == 0


def test_rows_come_back_as_signed_values(matrix_file: Path) -> None:
    with Int8Matrix(matrix_file) as matrix:
        assert matrix.shape == (3, 3)
        assert list(matrix.row(0)) == [1, -2, 3]
        assert list(matrix.row(1)) == [0, 127, -128]
        assert list(matrix.row(2)) == [-1, -1, -1]


def test_a_row_out_of_range_is_refused(matrix_file: Path) -> None:
    with Int8Matrix(matrix_file) as matrix:
        with pytest.raises(IndexError):
            matrix.row(3)
        with pytest.raises(IndexError):
            matrix.row(-1)


def test_the_mean_of_several_rows_matches_doing_it_by_hand(matrix_file: Path) -> None:
    with Int8Matrix(matrix_file) as matrix:
        assert matrix.mean([0, 2]) == [0.0, -1.5, 1.0]
        assert matrix.mean([1]) == [0.0, 127.0, -128.0]


def test_the_mean_of_nothing_is_zero(matrix_file: Path) -> None:
    with Int8Matrix(matrix_file) as matrix:
        assert matrix.mean([]) == [0.0, 0.0, 0.0]


@pytest.mark.parametrize(
    ("descr", "fortran", "message"),
    [("<f4", False, "int8"), ("|i1", True, "column")],
)
def test_a_layout_the_reader_cannot_handle_is_refused(
    tmp_path: Path, descr: str, fortran: bool, message: str
) -> None:
    path = tmp_path / "bad.npy"
    write_npy(path, [[1, 2], [3, 4]], descr=descr, fortran=fortran)
    with pytest.raises(NpyError, match=message):
        Int8Matrix(path).close()


def test_something_that_is_not_an_npy_file_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "nope.npy"
    path.write_bytes(b"not a numpy file at all, not even close")
    with pytest.raises(NpyError, match="NPY"):
        Int8Matrix(path).close()


def test_a_truncated_file_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "short.npy"
    write_npy(path, [[1, 2, 3], [4, 5, 6]])
    data = path.read_bytes()
    path.write_bytes(data[:-2])
    with pytest.raises(NpyError, match="truncated"):
        Int8Matrix(path).close()


# ---------------------------------------------------------------- against numpy


numpy = pytest.importorskip("numpy", reason="numpy is only a build-time dependency")


def test_the_reader_agrees_with_numpy(tmp_path: Path) -> None:
    """The reader replaces numpy, so it has to produce what numpy produced."""
    import numpy as np

    rng = np.random.default_rng(0)
    array = rng.integers(-128, 128, size=(50, 16), dtype=np.int8)
    path = tmp_path / "random.npy"
    np.save(path, array)

    with Int8Matrix(path) as matrix:
        assert matrix.shape == array.shape
        for index in (0, 7, 49):
            assert list(matrix.row(index)) == array[index].tolist()

        ids = [3, 3, 11, 40]
        expected = array[ids].astype(np.float64).mean(axis=0).tolist()
        assert matrix.mean(ids) == pytest.approx(expected)
