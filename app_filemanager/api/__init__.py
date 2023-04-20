from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from aiofiles import open
from datetime import datetime, timezone
import mimetypes
import re


from app_filemanager.utils.file import list_directory
from app_filemanager.config import *

api = APIRouter()


def time_utc_8(time):
    utc_time = datetime.utcfromtimestamp(time).replace(tzinfo=timezone.utc)
    utc_time_str = utc_time.strftime('%Y-%m-%d %H:%M:%S UTC')
    return utc_time_str


def parse_range_header(range_header: str, size: int) -> tuple[int, int]:
    """
    解析range标头
    :param range_header: 标头
    :param size:
    :return:
    """
    m = re.match(r"bytes=(\d*)-(\d*)", range_header)
    if not m:
        raise HTTPException(status_code=400, detail="Invalid range header")

    start = int(m.group(1)) if m.group(1) else None
    end = int(m.group(2)) if m.group(2) else None

    if start is None and end is None:
        raise HTTPException(status_code=400, detail="Invalid range header")

    if start is None:
        start = size - end
        end = size - 1
    elif end is None:
        end = size - 1

    if start < 0 or end >= size or start > end:
        raise HTTPException(status_code=416, detail="Invalid range")

    return start, end


async def iter_chunks(file_object, chunk_size=10*1024*1024):
    """
    :param file_object:
    :param chunk_size:  决定了每次读取的数据块大小，过小的 chunk_size 可能导致频繁的 IO 操作和网络传输开销。
    建议根据具体情况合理设置 chunk_size。如果文件较小，可以将 chunk_size 设置为文件大小以避免过多的 IO 操作。
    如果文件很大，可以尝试适当增加 chunk_size 来提高传输速度，但同时也要注意避免内存占用过大。
    :return:

    """
    while True:
        data = await file_object.read(chunk_size)
        if not data:
            break
        yield data

    # make sure to close the file when done reading
    await file_object.close()


@api.get('/')
@api.get('/{path:path}', response_class=HTMLResponse)
async def _home(path: str, request_range: str | None = Header(default=None, alias="Range")):
    """
    使用 StreamingResponse 返回文件内容具有以下优点：
    更快地发送内容 - StreamingResponse 使用 chunked transfer encoding，这意味着它可以在服务器读取数据时就开始发送数据。
    减少内存使用量 - 当我们使用 read() 方法一次性读取整个文件时，它会将文件的全部内容读入内存中。如果文件很大，
    这可能会导致内存不足或性能问题。使用 StreamingResponse 可以避免这个问题，因为它只会一次返回一小块数据。
    更好的用户体验 - 对于较大的文件，使用 StreamingResponse 可以更快地启动下载，并让用户更快地查看部分内容，而不必等待整个文件下载完成。
    因此，如果您的应用程序需要处理大型文件或需要提供更快的响应时间，则使用 StreamingResponse 是一个不错的选择。
    如果您的应用程序只需要处理较小的文件，则直接读取文件并返回其内容可能是更好的选择。
    :param path:
    :return:
    """

    path = Path('/') / path.removeprefix('/')

    if not path.exists():
        raise HTTPException(404, 'notfound')

    if path.is_file():
        mimetype, _ = mimetypes.guess_type(path)
        size = path.stat().st_size
        modified_time = path.stat().st_mtime

        if not request_range:
            file_iter = await open(path, mode='rb')
            return StreamingResponse(
                iter_chunks(file_iter),
                media_type=mimetype,
                headers={
                    "Content-Type": mimetype,
                    "Content-Length": str(size),
                    'accept-ranges': 'bytes',
                    'etag': '642ab489-617bbcf8',
                    'last-modified': f'Mon, 03 Apr 2023 11:12:09 GMT',
                }
            )

        start, end = parse_range_header(request_range, size)
        content_length = end - start + 1
        headers = {
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
        }

        async def stream_file(_path, chunk_size=10*1024*1024):
            file_object = await open(_path, mode='rb')
            await file_object.seek(start)
            while True:
                data = await file_object.read(chunk_size)
                if not data:
                    break
                yield data
            await file_object.close()

        return StreamingResponse(stream_file(path), media_type=mimetype, headers=headers, status_code=206)

    path_list: list[Path] = await list_directory(path)
    # li = ''.join(
    #     f'<li><a href="/filemanager{p}">{p.name}<a/> {p.stat().st_size} </li>' for p in li
    # )
    parent = f"""
    <tr>
        <td> <a href="/filemanager{path.parent}">上级目录/<a/> </td>
    </tr>
    """
    li = ''.join(
        f"""
        <tr>
            <td>
                <a href="/filemanager{p}">{p.name if p.is_file() else p.name + '/' }<a/> 
            <td>
                {time_utc_8(p.stat().st_mtime)}
            </td>
            <td style="text-align:right">
                {p.stat().st_size}
            </td> 
        </tr>
        """
        for p in path_list
    )

    html = html_template.replace('{path}', f'{path}')
    html = html.replace('{list}', li)
    html = html.replace('{parent}', parent)
    return html


