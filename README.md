
<p align="center">

![9213766CB158786A6C4C0291F715FE5F](https://github.com/user-attachments/assets/98d13492-7e5d-43bd-b3c3-b583699b23f0)

</p>

<dev align="center">

_笨笨的kahuna不停的计算自己离买牛角包还有多远_

_一座新的*山拔地而起！_

</dev>

本插件处于早期开发阶段，还有好多好多的bug~

欢迎提issue~

---
# ⭐功能展示

#### 吉他和联盟市场价格查询
![吉他和联盟市场价格查询](https://github.com/user-attachments/assets/3ba07ddf-a136-407c-95bd-5850b0b55657)

#### 成本查询
![成本查询](https://github.com/user-attachments/assets/63ecbd0c-2f91-491a-9ead-693646a81e5a)

#### 工业规划与报表输出
![工业规划](https://github.com/user-attachments/assets/f23b7873-dbb3-48df-9ee9-4d07ed4dba21)

![报表输出1](https://github.com/user-attachments/assets/9d2f4b57-04a4-4f31-909e-fbb72e86e4fb)

![报表输出2](https://github.com/user-attachments/assets/235c724e-f465-4966-98b8-0dc4cf7acc50)

#### 利润分析
![利润分析](https://github.com/user-attachments/assets/8b835d57-e093-42c0-896d-bb93579c9935)

👉报表内容丰富，包括任务分解，材料采购，物流清单，工作任务等，一站式解放工业制造的脑力消耗，🫡公司级别提供智能计算服务。


# 😇如何部署？
## 部署AstrBot
本项目是astrbot框架面向QQ的机器人插件，你需要先部署基于astrbot的qq机器人。

这里前往 [AstrBot](https://github.com/AstrBotDevs/AstrBot.git) 仓库。

---
## 下载插件
插件暂时没有上架插件商场，需要手动部署。

首先前往plugin目录：
```
AstrBot/
├── [其他文件]/
├── data/
│   ├── [其他文件]/
│   ├── plugins/              # 插件目录
```

将项目clone到plugin文件夹下
```bash
git clone https://github.com/AraragiEro/astrbot_plugin_kahunabot.git
```

kahunabot的目录结构如下：

```
kahunabot/
├── src/                    # 源代码目录
│   ├── event/              # 事件处理模块
│   ├── permission_checker/ # 权限检查模块
│   ├── resource/           # 资源文件目录
│   │   ├── css/           # 样式文件
│   │   ├── img/           # 图片资源
│   │   └── templates/     # 模板文件
│   ├── rule_checker/      # 规则检查模块
│   ├── service/           # 服务模块
│   │   ├── asset_server/  # 资产服务
│   │   ├── chat_server/   # 聊天服务
│   │   ├── market_server/ # 市场服务
│   │   └── sde_service/   # SDE数据服务
│   └── utils/             # 工具模块
├── data/                   # 数据目录
├── config.ini.example     # 配置文件
├── main.py                # 插件入口
├── filter.py              # 权限过滤器
└── requirements.txt       # 依赖包列表
```

---
## 配置插件

### 安装依赖
- 安装Playwright
```bash
# 下载速度慢可以考虑使用加速源 pip install playwright -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install playwright、
```

2. 安装浏览器依赖
```bash
python -m playwright install chromium
```

3. 如果在Linux环境下，可能需要安装额外的系统依赖
```bash
python -m playwright install-deps
```

### 准备SDE数据库
- sde数据库生成工具：**[EVE-SDE-Database-Builder](https://github.com/EVEIPH/EVE-SDE-Database-Builder.git)**
- 官方sde数据库更新地址：**[https://developers.eveonline.com/](https://developers.eveonline.com/)**

使用数据库生成工具处理ccp官方发布的sde数据库输出英文和中文的sqlite版本数据库备用。

👇参考下图👇

![image2](https://github.com/user-attachments/assets/8db7c904-dbd7-4497-a0ad-efdc6358c58b)

### 飞书api获取

前往 **[飞书开发平台](https://open.feishu.cn/app)** 注册账号，并创建一个应用获取appid和Secretid

![image3](https://github.com/user-attachments/assets/3e321503-edaa-48f8-b964-5a2d39712a73)

![image4](https://github.com/user-attachments/assets/820341a3-c37d-42af-a67b-b05c0eed8706)

添加机器人应用

![image5](https://github.com/user-attachments/assets/310e6f16-93a1-45fc-b5d4-6d65b85814ba)

开通应用权限，全选云文档权限即可

![image6](https://github.com/user-attachments/assets/e83653ed-3e72-4264-94a7-77ca751109fd)

给机器人添加云文档权限 [如何为应用开通云文档相关资源的权限](https://open.feishu.cn/document/uAjLw4CM/ugTN1YjL4UTN24CO1UjN/trouble-shooting/how-to-add-permissions-to-app)

新建一个云文档文件夹并获取链接，形式为`https://bcnzl0ndjqqq.feishu.cn/drive/folder/{folder_id}` ,将folder_id记录



### 修改配置文件
将`config.ini.example`复制一份,重命名为`config.ini`。

```ini
[APP]
DBTYPE = sqlite # 数据库类型，暂时只支持sqlite。本地数据库记得多备份哦~

[FEISHU]
APP_ID = MyApp      # 飞书表格输出相关配置
SECRET_ID = 1.0     
FOLDER_ROOT = xxx   # 填入刚才获取的folder_id

[POSTGREDB]     # 暂未启用
Host = localhost
Port = 5432
User = admin
Password = secret

[SQLITEDB] # 数据库路径，填写绝对路径
CONFIG_DB = F:\path\to\kahuna.db
CACHE_DB = F:\path\to\cache.db
SDEDB = F:\path\to\sde.db           # 刚才获取的英文sde数据库
CN_SDEDB = F:\path\to\sde_cn.db     # 刚才获取的中文sde数据库

[EVE]   # eve相关配置，在https://developers.eveonline.com/申请应用获取
CLIENT_ID =
SECRET_KEY =
MARKET_AC_CHARACTER_ID=     # 玩家建筑市场访问角色id，先置空

[ESI]   # esi权限配置，需要和申请的应用保持一致，默认全部为true，意为全部权限，需要关闭的权限改为false。
publicData = true
esi-calendar.respond_calendar_events.v1 = true
esi-calendar.read_calendar_events.v1 = true
esi-location.read_location.v1 = true
esi-location.read_ship_type.v1 = true
esi-mail.organize_mail.v1 = true
......
```

## 关于工业规划如何使用的一份粗略的说明，先凑合用
[小卡bot初级使用指南](https://conscious-cord-0d1.notion.site/bot-1920b0a9ac1b80998d71c4349b241145)

# 🌟支持一下
觉得好用的话，给孩子打点isk呗~ 

`ID: Alero AraragiEro`

