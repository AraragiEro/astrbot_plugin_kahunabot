import asyncio
from pickle import BINPUT
import pulp

from .industry_analyse import IndustryAnalyser
from ..sde_service.utils import SdeUtils
from ..user_server.user_manager import UserManager
from ..user_server.user import User
from ...utils import KahunaException
from ..market_server.marker import MarketHistory
from ..market_server.market_manager import MarketManager

class IndustryAdvice:
    @classmethod
    def advice_report(cls, user: User, plan_name: str, product_list: list):
        jita_mk = MarketManager.get_market_by_type('jita')
        vale_mk = MarketManager.get_market_by_type('frt')

        input_list = product_list
        t2_ship_id_list = [SdeUtils.get_id_by_name(name) for name in input_list]
        t2_plan = [[ship, 1] for ship in input_list]

        t2_cost_data = IndustryAnalyser.get_cost_data(user, plan_name, t2_plan)
        t2_cost_data = [[name] + value for name, value in t2_cost_data.items()]
        t2ship_data = []
        for data in t2_cost_data:
            tid = SdeUtils.get_id_by_name(data[0])
            vale_mk_his_data, forge_mk_his_data = MarketHistory.get_type_history_detale(tid)
            frt_buy, frt_sell = vale_mk.get_type_order_rouge(tid)
            jita_buy, jita_sell = jita_mk.get_type_order_rouge(tid)

            market_data = [
                tid,        # id
                data[0],    # name
                SdeUtils.get_cn_name_by_id(tid), # cn_name
                frt_sell * 0.956 - data[3] * 1.01,  # 利润
                (frt_sell * 0.956 - data[3] * 1.01) / data[3],  # 利润率
                vale_mk_his_data['monthflow'] * ((frt_sell * 0.956 - data[3] * 1.01) / data[3]), # 月利润空间
                data[3],    # cost
                frt_sell,   # 4h出单
                jita_buy,   # 吉他收单
                jita_sell,  # 吉他出单
                vale_mk_his_data['monthflow'],  # 月流水
                vale_mk_his_data['month_volume'], # 月销量
                SdeUtils.get_metaname_by_typeid(tid)    # 元组信息
            ]


            t2ship_data.append(market_data)

        t2ship_data.sort(key=lambda x: x[5], reverse=True)
        return t2ship_data

    @classmethod
    async def material_ref_advice(
            cls, material_list: list,
            material_flag: str = 'buy',
            compress_flag: str = 'buy'
    ):
        """
        三钛：34
        胶水：35
        类银：36
        同位：37
        小超：38
        石英：39
        大超：40
        摩尔：11399
        """
        jita_market = MarketManager.get_market_by_type('jita')
        # 产出效率系数
        efficiency_rate = 0.906  # 90.6%

        ref_target = {34, 35, 36, 37, 38, 39, 40, 11399}
        # ref_source_dict 中的值表示每100单位材料的产出
        ref_source_dict = {
            62520: {34: 150, 35: 90},
            62528: {34: 175, 36: 70},
            62536: {36: 60, 37: 120},
            62552: {37: 800, 35: 2000, 36: 1500},
            62524: {35: 90, 36: 30},
            62516: {34: 400},
            62586: {11399: 140},
            62560: {35: 800, 36: 2000, 38: 800},
            62564: {35: 3200, 36: 1200, 39: 160},
            62568: {35: 3200, 36: 1200, 40: 120},
            34: {34: 1}, 35: {35: 1}, 36: {36: 1}, 37: {37: 1}, 38: {38: 1}, 39: {39: 1}, 40: {40: 1}, 11399: {11399: 1}
        }
        target_price_index = 0 if material_flag == 'buy' else 1
        target_price = {
            target: jita_market.get_type_order_rouge(target)[target_price_index] for target in ref_target
        }
        source_price_index = 0 if compress_flag == 'buy' else 1
        source_price = {
            source: jita_market.get_type_order_rouge(source)[source_price_index] for source in ref_source_dict.keys()
        }


        # 预先计算考虑效率系数的产出
        effective_ref_source_dict = {}
        for m, products in ref_source_dict.items():
            effective_ref_source_dict[m] = {}
            for p, amount in products.items():
                # 预先计算单位产出 * 效率系数
                effective_ref_source_dict[m][p] = amount * (efficiency_rate if m not in ref_target else 1)

        need = {data[0]: data[1] for data in material_list if data[0] in ref_target}

        # 创建问题实例
        prob = pulp.LpProblem("MinimizeWaste", pulp.LpMinimize)

        # 定义决策变量（每种生产材料使用的数量，单位为100）
        materials = list(ref_source_dict.keys())
        material_units = pulp.LpVariable.dicts("Units", materials, lowBound=0, cat='Integer')

        # 创建辅助变量来表示每种产品的冗余量
        waste_vars = pulp.LpVariable.dicts("Waste",
                                           [(m, p) for m in materials for p in need.keys()],
                                           lowBound=0)

        # 目标1：原材料总成本
        material_cost = pulp.lpSum([material_units[m] * 100 * source_price[m] for m in materials])

        # 目标2：总产出价值 - 原材料总成本
        product_value = pulp.lpSum([
            pulp.lpSum([
                material_units[m] * effective_ref_source_dict[m].get(p, 0) * target_price[p]
                for m in materials if p in ref_source_dict[m]
            ])
            for p in need.keys()
        ])

        # 设置权重
        material_weight = 0.5  # 原材料成本权重
        profit_weight = 0.5  # 利润权重 (负号表示我们要最大化这部分)

        # 多目标优化：最小化原材料成本同时最大化利润
        prob += material_weight * material_cost - profit_weight * product_value

        # 添加约束：waste_vars[m, p] 必须大于等于冗余量
        for m in materials:
            for p in need.keys():
                if p in ref_source_dict[m]:
                    # 使用预先计算的有效产出率
                    prob += waste_vars[m, p] >= material_units[m] * effective_ref_source_dict[m][p] - need[p]
                else:
                    prob += waste_vars[m, p] == 0

        # 定义约束条件：每种最终产品的实际产出量必须满足需求
        for product in need.keys():
            # 使用预先计算的有效产出率
            effective_production = pulp.lpSum([
                material_units[m] * effective_ref_source_dict[m].get(product, 0)
                for m in materials if product in ref_source_dict[m]
            ])
            prob += effective_production >= need[product]

        # 求解问题
        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        # 检查求解状态
        if pulp.LpStatus[prob.status] != 'Optimal':
            print(f"未找到最优解，状态：{pulp.LpStatus[prob.status]}")
            return []

        # 输出结果
        # print(f"优化状态: {pulp.LpStatus[prob.status]}")

        res = {
            'need': {},
            'product': {},
            'connect': {}
        }
        need_d = res['need']
        product_d = res['product']
        connect_d = res['connect']
        # 构建结果列表
        result_list = []
        for m in materials:
            m_value = int(material_units[m].value()) * (100 if m not in ref_target else 1)
            if m_value > 0:
                result_list.append((m, m_value))

        # 打印详细信息
        # print("\n需要的生产材料数量:")
        total_resource_price = 0
        for m in materials:
            if material_units[m].value() > 0:
                need_d[m] = {
                    'name': SdeUtils.get_name_by_id(m),
                    'need': int(material_units[m].value()) * (100 if m not in ref_target else 1),
                    'price': source_price[m] * int(material_units[m].value()) * (100 if m not in ref_target else 1),
                }
                total_resource_price += need_d[m]['price']
        res['total_resource_price'] = total_resource_price

        # print("\n理论产出与实际产出对比:")
        theoretical_production = {p: 0 for p in need.keys()}
        actual_production = {p: 0 for p in need.keys()}

        for m in materials:
            connect_d[m] = {'name': SdeUtils.get_name_by_id(m), 'product': {}}
            if material_units[m].value() > 0:
                for p in need.keys():
                    if p in ref_source_dict[m]:
                        # 理论产出
                        theo_output = material_units[m].value() * ref_source_dict[m][p]
                        theoretical_production[p] += theo_output

                        # 实际产出（应用效率系数并向下取整）
                        actual_output = int(theo_output * (efficiency_rate if m not in ref_target else 1))
                        actual_production[p] += actual_output
                        connect_d[m]['product'][p] = {'name': SdeUtils.get_name_by_id(p), 'product_value': actual_output}

        # print("产品\t需求\t理论产出\t实际产出\t冗余")
        total_real_waste_price = 0
        total_product_price = 0
        for p in need.keys():
            real_waste = max(0, actual_production[p] - need[p])
            total_real_waste_price += target_price[p] * real_waste
            total_product_price += target_price[p] * actual_production[p]
            product_d[p] = {
                'name': SdeUtils.get_name_by_id(p),
                'need': need[p],
                'actual_production': actual_production[p],
                'waste_unit': real_waste,
                'waste_price': target_price[p] * real_waste
            }
        res['total_real_waste_price'] = total_real_waste_price
        res['total_product_price'] = total_product_price

        return res