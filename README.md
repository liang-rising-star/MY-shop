<div align="center">

# MY-Shop

**基于 FastAPI + SQLAlchemy 构建的现代化电商系统**

支持多种商品类型和完整的后台管理功能

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-LGPL%203.0-orange.svg)](LICENSE)

</div>

---

## 功能特性

| 模块 | 功能 |
|:---:|:---|
| 🔐 | 用户认证与授权（JWT） |
| 📦 | 商品管理（普通商品、盲盒、限时商品） |
| 🎫 | 卡密自动发货 |
| 🎲 | 盲盒抽奖系统 |
| 🛒 | 订单管理 |
| 💰 | 优惠券系统 |
| 👥 | 用户等级系统 |
| 📊 | 管理后台 |
| 💳 | 支付集成 |
| 📱 | 响应式设计 |

### 商品类型

| 类型 | 说明 |
|:---|:---|
| 普通商品 | 标准电商商品 |
| 盲盒商品 | 随机抽取的盲盒系统 |
| 限时商品 | 限时促销商品 |

### 管理功能

- 商品管理（CRUD）
- 订单管理
- 卡密管理（导入/导出/删除）
- 优惠券管理
- 用户管理
- 系统设置
- 数据统计面板
- 操作日志

---

## 技术栈

| 层级 | 技术 |
|:---|:---|
| 后端框架 | FastAPI |
| 数据库 | SQLite + SQLAlchemy ORM |
| 认证 | JWT + bcrypt |
| 前端 | Vue 3 + 原生 CSS |
| 异步支持 | async/await |
| 其他 | Redis（可选）、aiofiles |

---

## 快速开始

### 环境要求

- Python 3.8 或更高版本
- pip 包管理器

### 安装步骤

**1. 克隆项目**

```bash
git clone <repository-url>
cd MY-Shop/python-version/v1.0.0
```

**2. 安装依赖**

```bash
pip install -r requirements.txt
```

**3. 配置环境变量（可选）**

创建 `.env` 文件：

```env
PORT=8080
DB_PATH=shop.db
JWT_SECRET=your-secret-key-change-me
UPLOAD_DIR=uploads
REDIS_URL=redis://localhost:6379/0
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASS=your-password
BCRYPT_ROUNDS=12
```

**4. 运行项目**

```bash
python main.py
```

**5. 访问应用**

| 地址 | 说明 |
|:---|:---|
| http://localhost:8080 | 前台页面 |
| http://localhost:8080/admin | 管理后台 |
| http://localhost:8080/docs | API 文档 |

> 首次访问会自动跳转到初始化页面，创建管理员账户。

---

## 项目结构

```
python-version/v1.0.0/
├── main.py                # 主入口
├── requirements.txt       # 依赖
├── Dockerfile            # Docker 配置
├── app/                  # 应用目录
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库连接
│   ├── models.py         # 数据模型
│   ├── auth.py           # 认证模块
│   ├── logger.py         # 日志模块
│   ├── data_integrity.py # 数据完整性检查
│   └── routers/          # API 路由
│       ├── setup.py      # 系统初始化
│       ├── auth.py       # 用户认证
│       ├── products.py   # 商品管理
│       ├── categories.py # 分类管理
│       ├── cardkeys.py   # 卡密管理
│       ├── orders.py     # 订单处理
│       ├── coupons.py    # 优惠券
│       ├── admin.py      # 管理员功能
│       ├── user_center.py# 用户中心
│       ├── payment.py    # 支付功能
│       ├── levels.py     # 等级系统
│       ├── address.py    # 地址管理
│       ├── dashboard.py  # 数据面板
│       ├── lottery.py    # 抽奖系统
│       ├── events.py     # 活动管理
│       ├── bills.py      # 账单管理
│       └── admin_logs.py # 管理日志
├── static/               # 静态文件
│   ├── index.html        # 前台页面
│   ├── admin.html        # 管理后台
│   ├── admin-login.html  # 管理后台登录
│   ├── css/              # 样式文件
│   └── js/               # JavaScript 文件
├── logs/                 # 日志目录
├── Data/                 # 数据目录
└── uploads/              # 上传文件目录
    ├── images/           # 图片文件
    ├── product_files/    # 商品文件
    └── zip_files/        # 压缩文件
```

---

## API 接口

### 公开接口

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| POST | /api/register | 用户注册 |
| POST | /api/login | 用户登录 |
| GET | /api/captcha | 获取验证码 |
| GET | /api/products | 获取商品列表 |
| GET | /api/products/{id} | 获取商品详情 |
| GET | /api/categories | 获取分类列表 |
| GET | /api/reviews | 获取评论列表 |
| POST | /api/coupon/validate | 验证优惠券 |

### 用户接口（需要认证）

| 方法 | 路径 | 说明 |
|:---|:---|:---|
| GET | /api/profile | 获取用户信息 |
| PUT | /api/profile | 更新用户信息 |
| POST | /api/points | 添加积分 |
| GET | /api/orders | 获取订单列表 |
| GET | /api/orders/{id} | 获取订单详情 |
| POST | /api/orders | 创建订单 |
| POST | /api/coupon/claim | 领取优惠券 |
| GET | /api/coupons/mine | 获取我的优惠券 |
| POST | /api/reviews | 创建评论 |
| GET | /api/address | 获取地址列表 |
| POST | /api/address | 创建地址 |
| PUT | /api/address/{id} | 更新地址 |
| DELETE | /api/address/{id} | 删除地址 |

### 管理接口（需要管理员权限）

| 模块 | 操作 |
|:---|:---|
| 商品管理 | CRUD 操作 |
| 分类管理 | CRUD 操作 |
| 卡密管理 | 导入、列表、删除、导出 |
| 优惠券管理 | 创建、列表、删除 |
| 订单管理 | 列表查看、状态更新 |
| 用户管理 | 列表查看、状态管理 |
| 系统设置 | 获取、保存 |
| 数据统计 | 销售数据、用户统计 |
| 操作日志 | 查看、清理、设置保留天数 |

---

## 数据库模型

| 模块 | 说明 |
|:---|:---|
| User | 用户信息（用户名、密码、邮箱、等级、积分、余额、佣金） |
| Product | 商品信息（名称、描述、价格、库存、类型、媒体文件） |
| ProductCategory | 商品分类 |
| BlindBoxPool | 盲盒奖池 |
| CardKey | 卡密信息 |
| Coupon | 优惠券 |
| UserCoupon | 用户优惠券关联 |
| Order | 订单（订单号、支付状态、发货状态） |
| OrderItem | 订单商品 |
| Review | 商品评论（评分、内容） |

---

## 部署

### Docker 部署

```bash
# 构建镜像
docker build -t my-shop-python .

# 运行容器
docker run -p 8080:8080 -v $(pwd)/data:/app/data my-shop-python
```

### 手动部署

```bash
# 1. 安装 Python 3.8+
# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main.py
```

### 生产环境建议

- 使用 Gunicorn + Uvicorn 多 worker 部署
- 配置 Nginx 反向代理
- 使用 MySQL/PostgreSQL 替代 SQLite
- 配置 Redis 缓存
- 设置 HTTPS
- 配置日志轮转

---

## 开发计划

### 正在更新

<details>
<summary><b>日志系统</b></summary>

- 用户注册记录到日志
- 日志单行显示，超出用省略号，双击查看详情
- 登录失败/注册失败记录及原因
- 日志搜索功能
- 日志美化
- 日志单独保存

</details>

<details>
<summary><b>订单管理</b></summary>

- 订单搜索功能
- 显示商品数量（非件数）
- 金额显示支付金额
- 手动发货计入已售出
- 退货功能
- 概览显示未发货订单数量

</details>

<details>
<summary><b>商品管理</b></summary>

- 评论管理
- 星星评分
- 商品编辑添加积分奖励设置与标签
- 图片换位
- 拖动调节顺序
- 最多10个媒体文件限制
- 上传文件类型改为媒体文件
- 把不打折放最前面
- 套餐功能

</details>

<details>
<summary><b>媒体文件</b></summary>

- 视频播放优化（左右切换按钮）
- 下方添加媒体预览
- 图片自动切换（3秒/张，手动操作暂停）
- 视频和缩略图匹配
- FFmpeg压缩视频

</details>

<details>
<summary><b>用户体验</b></summary>

- 弹窗添加（替代alert）
- 日期改为选项
- 验证码输入错误自动清空
- 滑动效果
- 通知功能
- 预加载
- 菜单闪现问题修复
- 拖动排序提示、限制10提示

</details>

<details>
<summary><b>系统功能</b></summary>

- 客服对话相关
- API与KEY管理
- 使用指南
- 手动发货标签提示
- 优惠码/优惠券使用修复
- 积分设置
- 系统设置功能实现
- 购物车

</details>

<details>
<summary><b>安全与优化</b></summary>

- API安全
- 防盗链
- 文件删除联动（商品/媒体删除时清理服务器文件）
- 文件结构优化
- 性能优化
- 接口优化
- 路径问题修复（相对路径）
- 丢失文件后台记录，管理员登录提示

</details>

<details>
<summary><b>其他</b></summary>

- 支付配置中文本地化
- 概览整理
- 布局优化
- 详情页布局+套餐功能
- 自定义商品详情页
- 店铺关闭时封禁前台API
- 管理员权限测试

</details>

### 后续更新

- 添加换页时间相关设置
- 所有资源全本地化
- 添加单元测试
- 添加集成测试
- 添加邮件通知
- 添加短信验证

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

## 许可证

[![LGPL 3.0](https://img.shields.io/badge/License-LGPL%203.0-orange.svg)](LICENSE)

本项目使用 [LGPL 3.0 License](LICENSE) 开源许可证。