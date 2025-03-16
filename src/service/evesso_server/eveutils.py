import functools
import json
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSONEncoder subclass to handle datetime objects."""

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()  # Convert datetime objects to ISO 8601 strings

        return super().default(o)  # Default serialization for other types

# Find the max page using binary search
def find_max_page_binary_search(esi_func, start, end, *args, **kwargs):
    if end - start <= 1:
        return start

    mid = (start + end) // 2
    if esi_func(mid, *args, **kwargs):
        # If the mid page exists, search the upper half
        return find_max_page_binary_search(esi_func, mid, end, *args, **kwargs)
    else:
        # Otherwise, search the lower half
        return find_max_page_binary_search(esi_func, start, mid, *args, **kwargs)


def find_max_page(esi_func, *args, begin_page: int = 500, interval: int = 500, **kwargs):
    initial_page = 0
    page = initial_page

    # Check pages in the specified interval
    page += begin_page
    while esi_func(page, *args, **kwargs):
        page += interval

    # Once we find a page that doesn't exist, we know that the max page must be between `page - interval` and `page`.
    # So we use binary search within this range to find the exact max page.
    return find_max_page_binary_search(esi_func, max(0, page - interval), max(page - interval + 1, page), *args, **kwargs)

def get_multipages_result(esi_func, max_page, *args, **kwargs):
    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(esi_func, page, *args, **kwargs) for
                   page in range(1, max_page + 1)]
        results = []
        count = 1
        for future in tqdm(futures, desc="请求数据", unit="page"):
            result = future.result()
            if result:
                results.append(result)
            count += 1
    return results