# OpenManus 监控容器解决方案

## 解决方案概述

为解决开发容器工作区挂载和自动重启问题，我们实现了一个独立的监控容器，用于管理开发容器的生命周期。该方案具有以下特点：

1. **职责分离**：监控容器专注于管理开发容器，开发容器专注于业务逻辑
2. **完全自动化**：通过API接口管理挂载配置并自动重启容器
3. **可靠性高**：避免容器自重启问题，实现真正可靠的容器管理
4. **零用户干预**：用户只需调用API，无需手动重启容器

## 架构设计

该解决方案由以下组件组成：

1. **监控容器（Monitor Container）**
   - 提供REST API接口管理挂载配置
   - 直接操作Docker API进行容器管理
   - 监控配置变更，自动更新docker-compose文件

2. **开发容器（Development Container）**
   - 接收用户API请求并转发到监控容器
   - 继续保持原有的API接口，对用户透明

3. **共享数据卷**
   - 用于在两个容器间共享配置文件
   - 确保状态一致性

## 功能特性

### 1. 挂载管理功能

- 添加/删除工作区挂载
- 查询挂载信息
- 自动同步挂载配置到docker-compose文件

### 2. 容器生命周期管理

- 安全重启开发容器
- 监控容器状态
- 错误恢复机制

### 3. 调试功能

- 连接测试接口
- 容器状态查询
- 手动触发配置同步

## 使用说明

### 部署监控系统

使用提供的Docker Compose配置启动整个系统：

```bash
# 构建并启动所有容器
docker compose -f docker-compose.dev.yml up -d
```

这将启动两个容器：
- `openmanus-core-dev`：开发容器
- `openmanus-monitor`：监控容器

### 验证监控容器连接

通过开发容器API验证与监控容器的连接：

```bash
curl http://localhost:5172/api/mounts/test-monitor
```

正常响应示例：
```json
{
  "success": true,
  "message": "监控API可用",
  "data": {
    "api_url": "http://openmanus-monitor:8089/api",
    "status": "connected"
  }
}
```

### 管理挂载点

按照原有API使用方式管理挂载点，内部会自动重定向到监控容器：

```bash
# 添加挂载点
curl -X POST http://localhost:5172/api/mounts/mount -d '{
  "user_id": "user1",
  "workspace_id": "ws1",
  "local_path": "/path/to/local/folder",
  "description": "测试挂载点"
}'

# 查询挂载点
curl http://localhost:5172/api/mounts/mounts

# 删除挂载点
curl -X DELETE http://localhost:5172/api/mounts/mount/user1/ws1
```

### 直接访问监控容器API

高级用户也可以直接访问监控容器API：

```bash
# 健康检查
curl http://localhost:8089/api/health

# 查询挂载配置
curl http://localhost:8089/api/mounts

# 重启容器
curl -X POST http://localhost:8089/api/restart
```

## 故障排除

### 1. 监控容器无法访问

- 检查网络配置，确保两个容器在同一网络
- 验证端口映射是否正确配置
- 检查日志：`docker logs openmanus-monitor`

### 2. 容器重启失败

- 检查Docker权限是否正确
- 验证docker.sock是否正确挂载
- 检查开发容器名称是否匹配配置

### 3. 挂载配置未生效

- 检查工作区目录权限
- 确认docker-compose配置文件路径是否正确
- 验证挂载路径是否存在于宿主机

## 开发指南

### 1. 监控容器API

监控容器提供以下API：

- `GET /api/health` - 健康检查
- `GET /api/mounts` - 获取所有挂载配置
- `GET /api/mounts/:userId/:workspaceId` - 获取特定挂载配置
- `POST /api/mounts` - 添加挂载配置
- `DELETE /api/mounts/:userId/:workspaceId` - 删除挂载配置
- `POST /api/restart` - 重启开发容器
- `GET /api/debug/stats` - 获取容器状态（调试模式）
- `POST /api/debug/apply` - 应用配置并重启（调试模式）

### 2. 环境变量配置

监控容器支持以下环境变量：

- `DEBUG_MODE` - 启用调试模式（1=启用，0=禁用）
- `WORKSPACE_ROOT` - 工作区根目录（默认：/workspace）

开发容器支持以下环境变量：

- `MONITOR_API` - 监控容器API地址（默认：http://openmanus-monitor:8089/api）
- `MONITOR_API_FALLBACK` - 启用兼容模式（1=启用，0=禁用）
