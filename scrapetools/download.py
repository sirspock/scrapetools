from typing import (
    Union, Iterable, Awaitable, Any,
    Iterable, Dict, Tuple,
)
import os
import asyncio

import aiohttp  # type: ignore
from tqdm import tqdm  # type: ignore

from .fetch import bar_options
from .util import run, sensible_download_path


___all__ = [
    'download', 'download_sync'
]

CHUNK_SIZE = 2048


def download(urls           : Union[str, Iterable[str], Dict[str, str]],
             path           : str = None,
             session        : aiohttp.ClientSession = None,
             show_progress  : bool = False,
             max_concurrent : int  = 5,
             ) -> Awaitable[None]:
    if isinstance(urls, str):
        return download_one(url=urls,
                            path=path,
                            session=session,
                            show_progress=show_progress)
    return download_all(**locals())


def download_sync(*args    : Any,
                  **kwargs : Any,
                  ) -> None:
    return run(download(*args, **kwargs))


def download_one(url           : str,
                 path          : str = None,
                 session       : aiohttp.ClientSession = None,
                 show_progress : bool = False,
                 ) -> Awaitable[None]:
    return _download_one(**locals())


async def _download_one(url           : str,
                        path          : str = None,
                        session       : aiohttp.ClientSession = None,
                        response      : aiohttp.client.ClientResponse = None,
                        show_progress : bool = False,
                        pbar          : tqdm = None,
                        ) -> None:
    arguments = locals()

    if not session:
        async with aiohttp.ClientSession() as session:
            arguments.update(session=session)
            return await _download_one(**arguments)

    if not response:
        async with session.get(url) as response:
            arguments.update(response=response)
            return await _download_one(**arguments)

    if show_progress and not pbar:
        try:
            total = int(response.headers['Content-Length'])
        except KeyError:
            total = None

        with tqdm(**bar_options,
                  total=total,
                  unit='b',
                  ) as pbar:
            arguments.update(pbar=pbar)
            return await _download_one(**arguments)

    path = sensible_download_path(url, path)
    with open(path, 'wb') as fd:
        while True:
            chunk = await response.content.read(CHUNK_SIZE)
            if not chunk:
                break
            if show_progress:
                pbar.update(len(chunk))
            fd.write(chunk)


def download_all(urls           : Union[Iterable[str], Dict[str, str]],
                 path           : str = None,
                 session        : aiohttp.ClientSession = None,
                 show_progress  : bool = False,
                 max_concurrent : int = 5,
                 ) -> Awaitable[None]:
    if not isinstance(urls, dict):
        assert not path or os.path.isdir(path), \
            f'path must be a directory for multiple downloads, got: {path}'

        urls = {url: path for url in urls}

    return _download_all(**locals())


async def _download_all(urls              : Dict[str, str],
                        path              : str = None,
                        session           : aiohttp.ClientSession = None,
                        show_progress     : bool = False,
                        max_concurrent    : int  = 5,
                        pbar              : tqdm = None,
                        show_sub_progress : bool = None,
                        ) -> None:
    arguments = locals()

    if show_progress and not pbar:
        total = len(urls)

        # If there is no url, leave early
        # Both for perfomance and for a bug with tqdm
        if total == 0:
            return

        # Show at most 5 bars at the same screen by default
        # 1 for the Overall, 4 for individual
        if total > 4:
            show_sub_progress = show_sub_progress or False
        else:
            show_sub_progress = True if show_progress is None else show_progress

        with tqdm(**bar_options,
                  total=total,
                  unit='files',
                  desc='Overall',
                  ) as pbar:
            arguments.update(pbar=pbar,
                             show_sub_progress=show_sub_progress)
            return await _download_all(**arguments)

    if not session:
        async with aiohttp.ClientSession() as session:
            arguments.update(session=session)
            return await _download_all(**arguments)

    semaphore = asyncio.Semaphore(max_concurrent)

    async def bound_download_one(url_path : Tuple[str, str]) -> None:
        async with semaphore:
            await download_one(url=url_path[0],
                               path=url_path[1],
                               session=session,
                               show_progress=show_sub_progress)

        if show_progress:
            pbar.update(1)

    await asyncio.gather(
        *map(bound_download_one, urls.items()),
        return_exceptions=True,
    )
