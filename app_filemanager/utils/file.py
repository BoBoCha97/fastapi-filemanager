from aiofiles import open
from util.path import file_read
from pathlib import Path
import html
import urllib


async def list_directory(path) -> list[Path]:
    path = Path(path).resolve()

    if not path.exists() or not path.is_dir():
        raise OSError
    li = [path for path in path.glob('*')]
    li.sort()
    result = [p for p in li if p.is_dir() and p.name[:1] != '.']
    result += [p for p in li if p.is_file() and p.name[:1] != '.']

    return result


if __name__ == '__main__':
    import asyncio


    async def main():
        a = await list_directory()
        return 0

    asyncio.run(main())
