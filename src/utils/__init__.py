import math
import asyncio
from concurrent.futures import ThreadPoolExecutor
# import transformers

class KahunaException(Exception):
    def __init__(self, message):
        super(KahunaException, self).__init__(message)
        self.message = message

def roundup(x, base):
    return base * math.ceil(x / base)

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

class PluginMeta(type):  # 定义元类
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        # 每次类被创建时，自动运行 init
        cls.init()

async def run_func_delay_min(start_delay, func, *args, **kwargs):
    await asyncio.sleep(start_delay * 60)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        while not future.done():
            await asyncio.sleep(1)

async def refresh_per_min(start_delay, interval, func):
    await asyncio.sleep(start_delay * 60)
    with ThreadPoolExecutor(max_workers=1) as executor:
        while True:
            future = executor.submit(func)
            while not future.done():
                await asyncio.sleep(5)
            await asyncio.sleep(interval * 60)

# from .deepseek_tokenizer import tokenizer
# def get_chat_token_count(input: str):
#     result = tokenizer.encode(input)
#     return result
#
# def check_context_token_count(input: str, context_token_limit: int):
#     result = get_chat_token_count(input)
#     return result <= context_token_limit