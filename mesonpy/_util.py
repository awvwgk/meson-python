# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2021 Quansight, LLC
# SPDX-FileCopyrightText: 2021 Filipe Laíns <lains@riseup.net>

import contextlib
import gzip
import os
import pathlib
import sys
import tarfile
import tempfile
import typing

from typing import IO

from mesonpy._compat import Iterable, Iterator, PathLike


@contextlib.contextmanager
def cd(path: PathLike) -> Iterator[None]:
    """Context manager helper to change the current working directory -- cd."""
    old_cwd = os.getcwd()
    os.chdir(os.fspath(path))
    try:
        yield
    finally:
        os.chdir(old_cwd)


@contextlib.contextmanager
def add_ld_path(paths: Iterable[str]) -> Iterator[None]:
    """Context manager helper to add a path to LD_LIBRARY_PATH."""
    old_value = os.environ.get('LD_LIBRARY_PATH')
    old_paths = old_value.split(os.pathsep) if old_value else []
    os.environ['LD_LIBRARY_PATH'] = os.pathsep.join([*paths, *old_paths])
    try:
        yield
    finally:
        if old_value is not None:  # pragma: no cover
            os.environ['LD_LIBRARY_PATH'] = old_value


@contextlib.contextmanager
def edit_targz(path: PathLike, new_path: PathLike) -> Iterator[pathlib.Path]:
    """Opens a .tar.gz file in the file system for edition.."""
    with tempfile.TemporaryDirectory(prefix='mesonpy-') as tmpdir:
        workdir = pathlib.Path(tmpdir)
        with tarfile.open(path, 'r:gz') as tar:
            tar.extractall(tmpdir)

        yield workdir

        # reproducibility
        source_date_epoch = os.environ.get('SOURCE_DATE_EPOCH')
        mtime = int(source_date_epoch) if source_date_epoch else None

        file = typing.cast(IO[bytes], gzip.GzipFile(
            os.path.join(path, new_path),
            mode='wb',
            mtime=mtime,
        ))
        with contextlib.closing(file), tarfile.TarFile(
            mode='w',
            fileobj=file,
            format=tarfile.PAX_FORMAT,  # changed in 3.8 to GNU
        ) as tar:
            for path in workdir.rglob('*'):
                if path.is_file():
                    tar.add(
                        name=path,
                        arcname=path.relative_to(workdir).as_posix(),
                    )


class CLICounter:
    def __init__(self, total: int) -> None:
        self._total = total - 1
        self._count = -1
        self._current_line = ''

    def update(self, description: str) -> None:
        self._count += 1
        new_line = f'[{self._count}/{self._total}] {description}'
        if sys.stdout.isatty():
            pad_size = abs(len(self._current_line) - len(new_line))
            print(' ' + new_line + ' ' * pad_size, end='\r', flush=True)
        else:
            print(new_line)
        self._current_line = new_line

    def finish(self) -> None:
        if sys.stdout.isatty():
            print(f'\r{self._current_line}')


@contextlib.contextmanager
def cli_counter(total: int) -> Iterator[CLICounter]:
    counter = CLICounter(total)
    yield counter
    counter.finish()
