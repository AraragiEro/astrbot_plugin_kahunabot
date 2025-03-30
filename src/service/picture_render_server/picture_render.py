# import logger
from astrbot.api import logger
import imgkit
import os
import jinja2  # 添加Jinja2导入
import requests
import base64
from playwright.async_api import async_playwright
import math

from ..sde_service import SdeUtils
from ...utils import KahunaException

tmp_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../tmp"))
# 资源目录
resource_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../resource"))
# 模板目录
template_path = os.path.join(resource_path, "templates")
# CSS目录
css_path = os.path.join(resource_path, "css")

class PriceResRender():
    @classmethod
    def check_tmp_dir(cls):
        # 确保临时目录存在
        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path)

    @classmethod
    async def render_price_res_pic(cls, item_name: str, price_data: list):
        max_buy, mid_price, min_sell, fuzz_list = price_data

        cls.check_tmp_dir()

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
    async def render_single_cost_pic(cls, single_cost_data: dict):
        """
        single_cost.j2 模板需要填充的数据字段:

        1. 物品基本信息:
           - item_name: 物品英文名称，如 "Wyvern"
           - item_name_cn: 物品中文名称，如 "飞龙级"
           - item_id: 物品ID，如 23917
           - item_icon_url: 物品图标URL (可选)，如不提供将显示默认图标

        2. 成本和利润信息:
           - cost: 物品成本，如 132432132
           - profit: 利润值，如 21321321，正值显示绿色，负值显示红色
           - profit_rate: 利润率，如 16.1，显示为百分比，正值显示绿色，负值显示红色

        3. JITA交易数据:
           - jita_sell: JITA卖出价，如 111111111
           - jita_mid: JITA中间价，如 111111111
           - jita_buy: JITA买入价，如 111111111

        4. 饼图数据:
           - cost_components: 成本组成部分的列表，每个组件为字典，包含:
             - name: 组件名称，如 "A", "B", "C", "D"
             - value: 组件值（数值或百分比），如 25
             - color: 颜色名称（对应Tailwind的颜色），如 "red", "blue", "green", "yellow"
             - rgba_bg: 背景RGBA值 (可选)，如 "255, 99, 132, 0.8"
             - rgba_border: 边框RGBA值 (可选)，如 "255, 99, 132, 1"

        注意: 所有数值类型数据会通过format_number过滤器格式化，需要在渲染前注册此过滤器。
        """

        material_dict = single_cost_data['material']
        group_detail = single_cost_data['group_detail']
        eiv_cost = single_cost_data['eiv']

        # 1.
        item_id = single_cost_data['type_id']
        item_name = SdeUtils.get_name_by_id(item_id)
        iten_name_cn = SdeUtils.get_cn_name_by_id(item_id)
        item_icon_url = cls.get_eve_item_icon_base64(item_id)

        # 3.
        jita_buy, jita_mid, jita_sell, _ = single_cost_data["market_detail"]

        # 2.
        cost = single_cost_data['total_cost']
        profit = single_cost_data['profit'] = jita_sell - cost
        profit_rate = profit / cost

        # 4. 修改饼图数据处理，确保使用正确的值
        group_cost_list = [[group, data[0], data[1]] for group, data in group_detail.items()]
        group_cost_list.sort(key=lambda x: x[1], reverse=True)
        cost_components = [
            {
                'name': group_data[0],
                'value': group_data[1],  # 使用实际成本值而不是百分比
            }
            for group_data in group_cost_list
        ]
        cost_components.append(
            {
                'name': '系数',
                'value': eiv_cost[0]
            }
        )

        # 4.
        def format_number(value):
            """将数字格式化为带千位分隔符的字符串"""
            try:
                # 转换为浮点数
                num = float(value)
                # 如果是整数，不显示小数部分
                if num.is_integer():
                    return "{:,}".format(int(num))
                # 否则保留两位小数
                return "{:,.2f}".format(num)
            except (ValueError, TypeError):
                # 如果无法转换为数字，返回原值
                return value

        # 开始渲染图片
        # 获取Jinja2环境
        try:
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(template_path),
                autoescape=jinja2.select_autoescape(['html', 'xml'])
            )
            env.filters['format_number'] = format_number
            template = env.get_template('single_cost.j2')
            html_content = template.render(
                item_name=item_name,
                item_name_cn=iten_name_cn,
                item_id=item_id,
                item_icon_url=item_icon_url,
                jita_buy=jita_buy,
                jita_mid=jita_mid,
                jita_sell=jita_sell,
                cost=cost,
                profit=profit,
                profit_rate=profit_rate,
                cost_components=cost_components
            )
            with open(os.path.join(tmp_path, "single_cost.html"), 'w', encoding='utf-8') as f:
                f.write(html_content)
        except jinja2.exceptions.TemplateNotFound as e:
            logger.error(f"模板文件不存在: {e}")
            logger.error(f"请确保模板文件已放置在 {template_path} 目录下")
            return None

        # 生成输出路径
        output_path = os.path.abspath(os.path.join((tmp_path), "single_cost_res.jpg"))

        # 增加等待时间到5秒，确保图表有足够时间渲染
        pic_path = await cls.render_pic(output_path, html_content, width=550, height=720, wait_time=5000)

        if not pic_path:
            raise KahunaException("pic_path not exist.")
        return pic_path

    @classmethod
    async def render_pic(cls, output_path: str, html_content: str, width: int = 800, height: int = 800, wait_time: int = 1000):
        # 使用异步API生成图片
        try:
            async with async_playwright() as p:
                # 启动浏览器，添加参数以确保JavaScript正常执行
                browser = await p.chromium.launch(
                    args=['--disable-web-security', '--allow-file-access-from-files']
                )
                page = await browser.new_page(viewport={'width': width, 'height': height})

                # 设置HTML内容
                await page.set_content(html_content)

                # 等待内容渲染完成
                await page.wait_for_timeout(wait_time)
                
                # 尝试等待图表元素
                try:
                    await page.wait_for_selector('#costChart', state='attached', timeout=3000)
                    logger.info("图表元素已找到")
                    
                    # 额外等待图表渲染完成
                    await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.warning(f"等待图表元素超时: {e}")


                # 使用全页面截图而不是裁剪
                await page.screenshot(
                    path=output_path,
                    full_page=True
                )

                await browser.close()
                return output_path

        except Exception as e:
            logger.error(f"生成图片失败: {e}")
            import traceback
            logger.error(traceback.format_exc())  # 打印完整堆栈跟踪
            return None

    @classmethod
    def get_eve_item_icon_base64(cls, type_id: int):
        item_image_path = cls.download_eve_item_image(type_id)  # 这里的ID需要根据实际物品ID修改
        item_image_base64 = cls.get_image_base64(item_image_path) if item_image_path else None

        return item_image_base64

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

        # 尝试从主URL下载
        try:
            # 下载图片，禁用SSL验证
            response = requests.get(url, verify=False, timeout=10)
            response.raise_for_status()  # 检查请求是否成功

            # 保存图片
            with open(local_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"成功下载物品图片: {type_id}")
            return local_path
        except Exception as e:
            logger.error(f"从主URL下载EVE物品图片失败: {e}")
            
            # 尝试备用URL
            try:
                # 备用URL
                backup_url = f"https://imageserver.eveonline.com/Type/{type_id}_{size}.png"
                logger.info(f"尝试从备用URL下载: {backup_url}")
                
                response = requests.get(backup_url, verify=False, timeout=10)
                response.raise_for_status()
                
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"从备用URL成功下载物品图片: {type_id}")
                return local_path
            except Exception as backup_e:
                logger.error(f"从备用URL下载EVE物品图片也失败: {backup_e}")
                
                # 如果两个URL都失败，返回默认图片路径
                default_image = os.path.join(resource_path, "img", "default_item.png")
                
                # 如果默认图片不存在，创建一个简单的默认图片
                if not os.path.exists(default_image):
                    try:
                        # 创建一个简单的1x1像素透明PNG
                        with open(default_image, 'wb') as f:
                            f.write(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="))
                    except Exception:
                        logger.error("无法创建默认图片")
                        return None
                
                return default_image

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