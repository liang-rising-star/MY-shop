# MY-Shop Go版本

基于 Gin + GORM 构建的高性能电商系统

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

- **后端框架**: Gin
- **数据库**: SQLite + GORM
- **认证**: JWT + bcrypt
- **前端**: Vue 3 + 原生CSS
- **性能**: 高性能、低延迟

## 📦 安装

### 1. 进入项目目录

```bash
cd go-version
```

### 2. 安装依赖

```bash
go mod download
```

### 3. 配置环境变量（可选）

创建 `.env` 文件：

```env
PORT=8080
DB_PATH=shop.db
JWT_SECRET=your-secret-key-change-me
UPLOAD_DIR=uploads
```

### 4. 运行项目

```bash
go run main.go
```

或编译后运行：

```bash
go build -o my-shop
./my-shop
```

### 5. 访问应用

- 前台: http://localhost:8080
- 管理后台: http://localhost:8080/admin

首次访问会自动跳转到初始化页面，创建管理员账户。

## 📁 项目结构

```
go-version/
├── main.go                # 主入口
├── go.mod                 # Go模块配置
├── go.sum                 # 依赖锁定
├── handlers/              # 处理器
│   ├── setup.go          # 系统初始化
│   ├── user.go           # 用户管理
│   ├── admin.go          # 管理员功能
│   ├── product.go        # 商品管理
│   ├── order.go          # 订单处理
│   ├── coupon.go         # 优惠券
│   ├── cardkey.go        # 卡密管理
│   ├── category.go       # 分类管理
│   ├── cart.go           # 购物车
│   └── review.go         # 评论管理
├── models/               # 数据模型
│   ├── user.go
│   ├── product.go
│   ├── order.go
│   ├── coupon.go
│   ├── cardkey.go
│   ├── category.go
│   ├── cart.go
│   └── review.go
├── routes/               # 路由配置
│   └── routes.go
├── config/               # 配置管理
│   └── config.go
└── static/               # 静态文件
    ├── index.html        # 前台页面
    ├── admin.html        # 管理后台
    ├── css/              # 样式文件
    └── js/               # JavaScript文件
```

## 🐛 已修复的问题

### 性能优化
- ✅ bcrypt密码哈希优化（从7-8秒降至毫秒级）
- ✅ 数据库查询优化

## 🚀 部署

### 编译部署

```bash
# Linux
GOOS=linux GOARCH=amd64 go build -o my-shop-linux

# Windows
GOOS=windows GOARCH=amd64 go build -o my-shop.exe

# macOS
GOOS=darwin GOARCH=amd64 go build -o my-shop-mac
```

### Docker部署

```dockerfile
FROM golang:1.23-alpine
WORKDIR /app
COPY . .
RUN go build -o my-shop
EXPOSE 8080
CMD ["./my-shop"]
```

## 📊 性能对比

| 指标 | Python版本 | Go版本 |
|------|-----------|--------|
| 启动时间 | ~2秒 | ~0.1秒 |
| 内存占用 | ~100MB | ~20MB |
| 并发性能 | 中等 | 高 |
| 响应时间 | 10-50ms | 1-10ms |

## 📝 开发计划

- [ ] 添加单元测试
- [ ] 添加集成测试
- [ ] 添加日志系统
- [ ] 添加缓存支持
- [ ] 添加限流功能
- [ ] 添加监控指标

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

LGPL 3.0 License
