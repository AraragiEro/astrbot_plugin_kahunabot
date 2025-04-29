import functools
import json
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

from ..log_server import logger

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSONEncoder subclass to handle datetime objects."""

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()  # Convert datetime objects to ISO 8601 strings

        return super().default(o)  # Default serialization for other types

# Find the max page using binary search
async def find_max_page_binary_search(esi_func, start, end, *args, **kwargs):
    if end - start <= 1:
        return start

    mid = (start + end) // 2
    if await esi_func(mid, *args, **kwargs):
        # If the mid page exists, search the upper half
        return await find_max_page_binary_search(esi_func, mid, end, *args, **kwargs)
    else:
        # Otherwise, search the lower half
        return await find_max_page_binary_search(esi_func, start, mid, *args, **kwargs)


async def find_max_page(esi_func, *args, begin_page: int = 500, interval: int = 500, **kwargs):
    initial_page = 0
    page = initial_page

    # Check pages in the specified interval
    page += begin_page
    while await esi_func(page, *args, log=False):
        page += interval

    # Once we find a page that doesn't exist, we know that the max page must be between `page - interval` and `page`.
    # So we use binary search within this range to find the exact max page.
    return await find_max_page_binary_search(esi_func, max(0, page - interval), max(page - interval + 1, page), *args, **kwargs)

async def get_multipages_result(esi_func, max_page, *args):
    logger.info(f'{esi_func.__name__} 开始批量任务， page: {max_page}')
    max_concurent = 30
    semaphore = asyncio.Semaphore(max_concurent)

    async def process_with_limit(*a, **ka):
        async with semaphore:
            try:
                return await esi_func(*a, **ka)
            except Exception as e:
                logger.error(f'运行 {esi_func.__anme} 时失败')
                return None

    results = []
    with tqdm(total=max_page, desc=f"请求{esi_func.__name__}数据", unit="page", ascii='=-') as pbar:
        task = [process_with_limit(page, *args) for page in range(1, max_page + 1)]
        for future in asyncio.as_completed(task):
            result = await future
            if result:
                results.append(result)
        pbar.update(1)

    return results