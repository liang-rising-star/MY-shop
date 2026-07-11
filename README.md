# MY-Shop

基于 FastAPI + SQLAlchemy 构建的现代化电商系统，支持多种商品类型和完整的后台管理功能。

## 功能特性

### 核心功能
- 用户认证与授权（JWT）
- 商品管理（普通商品、盲盒、限时商品）
- 卡密自动发货
- 盲盒抽奖系统
- 订单管理
- 优惠券系统
- 用户等级系统
- 管理后台
- 支付集成
- 响应式设计

### 商品类型
- **普通商品**: 标准电商商品
- **盲盒商品**: 随机抽取的盲盒系统
- **限时商品**: 限时促销商品

### 管理功能
- 商品管理（CRUD）
- 订单管理
- 卡密管理（导入/导出/删除）
- 优惠券管理
- 用户管理
- 系统设置

## 技术栈

- **后端框架**: FastAPI
- **数据库**: SQLite + SQLAlchemy ORM
- **认证**: JWT + bcrypt
- **前端**: Vue 3 + 原生 CSS
- **异步支持**: async/await
- **其他**: Redis（可选）、aiofiles（异步文件操作）

## 快速开始

### 环境要求

- Python 3.8 或更高版本
- pip 包管理器

### 安装步骤

1. 克隆项目
   ```bash
   git clone <repository-url>
   cd MY-Shop/python-version/v1.0.0
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境变量（可选）
   
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

4. 运行项目
   ```bash
   python main.py
   ```

5. 访问应用
   - 前台: http://localhost:8080
   - 管理后台: http://localhost:8080/admin

首次访问会自动跳转到初始化页面，创建管理员账户。

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
│       ├── dashboard.py  # 数据面板
│       └── lottery.py    # 抽奖系统
└── static/               # 静态文件
    ├── index.html        # 前台页面
    ├── admin.html        # 管理后台
    ├── css/              # 样式文件
    └── js/               # JavaScript 文件
```

## API 接口

### 公开接口
- `POST /api/register` - 用户注册
- `POST /api/login` - 用户登录
- `GET /api/products` - 获取商品列表
- `GET /api/products/:id` - 获取商品详情
- `GET /api/categories` - 获取分类列表
- `POST /api/coupon/validate` - 验证优惠券

### 用户接口（需要认证）
- `GET /api/profile` - 获取用户信息
- `POST /api/points` - 添加积分
- `POST /api/orders` - 创建订单
- `GET /api/orders` - 获取订单列表
- `GET /api/orders/:id` - 获取订单详情
- `POST /api/coupon/claim` - 领取优惠券
- `GET /api/coupons/mine` - 获取我的优惠券

### 管理接口（需要管理员权限）
- 商品管理: CRUD 操作
- 分类管理: CRUD 操作
- 卡密管理: 导入、列表、删除、导出
- 优惠券管理: 创建、列表、删除
- 订单管理: 列表查看
- 用户管理: 列表查看
- 系统设置: 获取、保存

## 数据库模型

- **User**: 用户信息（用户名、密码、邮箱、等级、积分）
- **Product**: 商品信息（名称、价格、库存、类型）
- **ProductCategory**: 商品分类
- **BlindBoxPool**: 盲盒奖池
- **CardKey**: 卡密信息
- **Coupon**: 优惠券
- **UserCoupon**: 用户优惠券关联
- **Order**: 订单
- **OrderItem**: 订单商品
- **Review**: 商品评论

## 部署

### Docker 部署

```bash
# 构建镜像
docker build -t my-shop-python .

# 运行容器
docker run -p 8080:8080 -v $(pwd)/data:/app/data my-shop-python
```

### 手动部署

1. 安装 Python 3.8+
2. 安装依赖：`pip install -r requirements.txt`
3. 运行：`python main.py`

## 开发计划

### 正在更新

**日志系统**
- 用户注册记录到日志
- 日志单行显示，超出用省略号，双击查看详情
- 登录失败/注册失败记录及原因
- 日志搜索功能
- 日志美化
- 日志单独保存

**订单管理**
- 订单搜索功能
- 显示商品数量（非件数）
- 金额显示支付金额
- 手动发货计入已售出
- 退货功能
- 概览显示未发货订单数量

**商品管理**
- 评论管理
- 星星评分
- 商品编辑添加积分奖励设置与标签
- 图片换位
- 拖动调节顺序
- 最多10个媒体文件限制
- 上传文件类型改为媒体文件
- 把不打折放最前面
- 套餐功能

**媒体文件**
- 视频播放优化（左右切换按钮）
- 下方添加媒体预览
- 图片自动切换（3秒/张，手动操作暂停）
- 视频和缩略图匹配
- FFmpeg压缩视频

**用户体验**
- 弹窗添加（替代alert）
- 日期改为选项
- 验证码输入错误自动清空
- 滑动效果
- 通知功能
- 预加载
- 菜单闪现问题修复
- 拖动排序提示、限制10提示

**系统功能**
- 客服对话相关
- API与KEY管理
- 使用指南
- 手动发货标签提示
- 优惠码/优惠券使用修复
- 积分设置
- 系统设置功能实现
- 购物车

**安全与优化**
- API安全
- 防盗链
- 文件删除联动（商品/媒体删除时清理服务器文件）
- 文件结构优化
- 性能优化
- 接口优化
- 路径问题修复（相对路径）
- 丢失文件后台记录，管理员登录提示

**支付配置**
- 支付配置中文本地化

**其他**
- 概览整理
- 评论管理
- 布局优化
- 详情页布局+套餐功能
- 自定义商品详情页
- 店铺关闭时封禁前台API
- 管理员权限测试

### 后续更新

- 添加换页时间相关设置
- 所有资源全本地化
- 添加单元测试
- 添加集成测试
- 添加邮件通知
- 添加短信验证

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License