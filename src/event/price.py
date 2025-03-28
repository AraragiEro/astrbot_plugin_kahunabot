# import logger
from astrbot.api import logger
import imgkit
import os
import jinja2  # 添加Jinja2导入
import requests
import base64
from playwright.async_api import async_playwright

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Image
# kahuna model
from .utils import kahuna_debug_info
from ..service.market_server import PriceService
from ..service.sde_service import SdeUtils

# kahuna Permission
# from ..permission_checker import PermissionChecker

# import Exception
from ..utils import KahunaException

# import logger
from ..service.log_server import logger

# global value
ROUGE_PRICE_HELP = ("ojita/ofrt:\n" \
                    "   [物品]:       获得估价。\n"
                    "   [物品] * [数量]: 获得估价。\n")

class TypesPriceEvent():
    @staticmethod
    async def ojita_func(event: AstrMessageEvent, require_str: str):
        item_name = " ".join(event.get_message_str().split(" ")[1:])
        return await TypesPriceEvent.oprice(event, item_name, "jita")

    @staticmethod
    async def ofrt_func(event: AstrMessageEvent, require_str: str):
        item_name = " ".join(event.get_message_str().split(" ")[1:])
        return await TypesPriceEvent.oprice(event, item_name, "frt")

    @staticmethod
    async def oprice(event: AstrMessageEvent, require_str: str, market: str):
        message_str = event.get_message_str()
        if message_str.split(" ")[-1].isdigit():
            quantity = int(message_str.split(" ")[-1])
            item_name = " ".join(message_str.split(" ")[1:-1])
        else:
            item_name = require_str
            quantity = 1

        max_buy, mid_price, min_sell, fuzz_list = PriceService.get_price_rouge(item_name, market)
        if fuzz_list:
            fuzz_rely = (f"物品 {item_name} 不存在于数据库\n"
                         f"你是否在寻找：\n")
            fuzz_rely += '\n'.join(fuzz_list)
            return event.plain_result(fuzz_rely)
        res_path = await PriceResRender.render_res_pic(item_name, [max_buy, mid_price, min_sell, fuzz_list])
        chain = [
            Image.fromFileSystem(res_path)
        ]
        return event.chain_result(chain)

# TODO 临时目录的创建
tmp_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tmp"))
# 资源目录
resource_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../resource"))
# 模板目录
template_path = os.path.join(resource_path, "templates")
# CSS目录
css_path = os.path.join(resource_path, "css")

class PriceResRender():
    @classmethod
    async def render_res_pic(cls, item_name: str, price_data: list):
        max_buy, mid_price, min_sell, fuzz_list = price_data
        
        # 确保临时目录存在
        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)
        
        # 获取Jinja2环境
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_path),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )

        # 读取CSS内容
        try:
            with open(os.path.join(css_path, "price_style.css"), 'r', encoding='utf-8') as f:
                price_css_content = f.read()
            
            with open(os.path.join(css_path, "fuzz_style.css"), 'r', encoding='utf-8') as f:
                fuzz_css_content = f.read()
        except FileNotFoundError as e:
            logger.error(f"CSS文件不存在: {e}")
            logger.error(f"请确保CSS文件已放置在 {css_path} 目录下")
            return None

        # 根据是否有模糊匹配结果选择模板
        try:
            if fuzz_list:
                template = env.get_template('fuzz_template.j2')
                html_content = template.render(
                    fuzz_list=fuzz_list,
                    css_content=fuzz_css_content
                )
            else:
                # 下载并转换物品图片
                item_image_path = cls.download_eve_item_image(SdeUtils.get_id_by_name(item_name))  # 这里的ID需要根据实际物品ID修改
                item_image_base64 = cls.get_image_base64(item_image_path) if item_image_path else None
                
                template = env.get_template('price_template.j2')
                html_content = template.render(
                    item_name=item_name,
                    max_buy=f"{max_buy:,.2f}",
                    mid_price=f"{mid_price:,.2f}",
                    min_sell=f"{min_sell:,.2f}",
                    css_content=price_css_content,
                    item_image_base64=item_image_base64
                )
        except jinja2.exceptions.TemplateNotFound as e:
            logger.error(f"模板文件不存在: {e}")
            logger.error(f"请确保模板文件已放置在 {template_path} 目录下")
            return None
        
        # 生成输出路径
        output_path = os.path.abspath(os.path.join((tmp_path), "price_res.jpg"))
        
        # 使用异步API生成图片
        try:
            async with async_playwright() as p:
                # 启动浏览器
                browser = await p.chromium.launch()
                page = await browser.new_page(viewport={'width': 200, 'height': 600})
                
                # 设置HTML内容
                await page.set_content(html_content)
                
                # 等待内容渲染完成
                await page.wait_for_timeout(1000)
                
                # 获取实际内容高度
                body_height = await page.evaluate('document.body.scrollHeight')
                body_width = await page.evaluate('document.body.scrollWidth')
                
                # 调整视口大小以适应内容
                await page.set_viewport_size({'width': body_width, 'height': body_height})
                
                # 截图
                await page.screenshot(path=output_path, full_page=True)
                
                # 关闭浏览器
                await browser.close()
                
                return output_path
        except Exception as e:
            logger.error(f"生成图片失败: {e}")
            return None
        
        return None
    
    @classmethod
    def download_eve_item_image(cls, type_id: int, size: int = 64) -> str:
        """
        下载EVE物品图片
        :param type_id: 物品ID
        :param size: 图片尺寸，可选值：64, 1024
        :return: 图片本地路径
        """
        # 创建图片存储目录
        image_path = os.path.join(resource_path, "img")
        if not os.path.exists(image_path):
            os.makedirs(image_path)
            
        # 构建图片URL和本地保存路径
        url = f"https://images.evetech.net/types/{type_id}/icon?size={size}"
        local_path = os.path.join(image_path, f"item_{type_id}_{size}.png")
        
        # 如果图片已存在，直接返回路径
        if os.path.exists(local_path):
            return local_path
            
        try:
            # 下载图片
            response = requests.get(url)
            response.raise_for_status()  # 检查请求是否成功
            
            # 保存图片
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            return local_path
        except Exception as e:
            logger.error(f"下载EVE物品图片失败: {e}")
            return None
        
    @classmethod
    def get_image_base64(cls, image_path: str) -> str:
        """将图片转换为base64编码"""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
                return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            logger.error(f"图片转base64失败: {e}")
            return None