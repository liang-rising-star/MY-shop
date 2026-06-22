# MY-Shop Python版本

基于 FastAPI + SQLAlchemy 构建的现代化电商系统

## ✨ 功能特性

- 🔐 用户认证与授权（JWT）
- 📦 商品管理（普通商品、盲盒、限时商品）
- 🎫 卡密自动发货
- 🎲 盲盒抽奖系统
- 🛒 订单管理
- 💰 优惠券系统
- 👥 用户等级系统
- 📊 管理后台
- 💳 支付集成
- 📱 响应式设计

## 🛠️ 技术栈

- **后端框架**: FastAPI
- **数据库**: SQLite + SQLAlchemy ORM
- **认证**: JWT + bcrypt
- **前端**: Vue 3 + 原生CSS
- **异步支持**: async/await

## 📦 安装

### 1. 进入项目目录

```bash
cd python-version
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量（可选）

创建 `.env` 文件：

```env
PORT=8080
DB_PATH=shop.db
JWT_SECRET=your-secret-key-change-me
UPLOAD_DIR=uploads
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASS=your-password
```

### 4. 运行项目

```bash
python main.py
```

或使用 uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### 5. 访问应用

- 前台: http://localhost:8080
- 管理后台: http://localhost:8080/admin

首次访问会自动跳转到初始化页面，创建管理员账户。

## 📁 项目结构

```
python-version/
├── main.py                # 主入口
├── requirements.txt       # 依赖
├── Dockerfile            # Docker配置
├── app/                  # 应用目录
│   ├── config.py         # 配置管理
│   ├── database.py       # 数据库连接
│   ├── models.py         # 数据模型
│   ├── auth.py           # 认证模块
│   └── routers/          # API路由
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
│       └── dashboard.py  # 数据面板
└── static/               # 静态文件
    ├── index.html        # 前台页面
    ├── admin.html        # 管理后台
    ├── css/              # 样式文件
    └── js/               # JavaScript文件
```

## 🔧 API文档

启动项目后访问：
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## 🐛 已修复的问题

### 性能优化
- ✅ bcrypt密码哈希优化（从7-8秒降至毫秒级）
- ✅ JWT token生成优化
- ✅ 数据库查询优化

### 安全修复
- ✅ 文件上传安全验证（类型、大小限制）
- ✅ 并发安全（防止超卖）
- ✅ SQL注入防护
- ✅ XSS防护

### 功能修复
- ✅ 盲盒抽奖逻辑修复
- ✅ 订单号唯一性保证
- ✅ 分类删除关联检查
- ✅ 库存检查完善
- ✅ 管理后台加载问题修复

## 🚀 部署

### Docker部署

```bash
docker build -t my-shop-python .
docker run -p 8080:8080 -v $(pwd)/data:/app/data my-shop-python
```

### 手动部署

1. 安装Python 3.8+
2. 安装依赖：`pip install -r requirements.txt`
3. 运行：`python main.py`

## 📝 开发计划

- [ ] 添加单元测试
- [ ] 添加集成测试
- [ ] 优化前端性能
- [ ] 添加更多支付方式
- [ ] 添加邮件通知
- [ ] 添加短信验证
- [ ] 添加日志系统
- [ ] 添加缓存支持

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
