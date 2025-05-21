# OpenManus 挂载工具使用指南

## 介绍

OpenManus 挂载工具是一个简单易用的命令行工具，用于管理开发容器的挂载点和容器生命周期。通过这个工具，您可以快速执行挂载、卸载、查看挂载列表以及重启容器等操作，而无需手动调用 API 或编写脚本。

## 安装与配置

### 前提条件

- Python 3.8 或更高版本
- 运行中的 OpenManus 监控容器和开发容器

### 安装步骤

1. 确保 Python 环境已正确配置
2. 安装所需依赖：
   ```
   pip install requests argparse
   ```
3. 确保 `mount_tool.py` 脚本具有执行权限：
   ```
   chmod +x scripts/mount_tool.py
   ```

## 基本用法

挂载工具提供以下几个主要命令：

- `mount`: 挂载本地目录
- `unmount`: 卸载目录
- `list`: 列出当前挂载
- `restart`: 重启开发容器

### 命令详解

#### 挂载目录

```bash
python scripts/mount_tool.py mount --user [用户ID] --workspace [工作区ID] --path [本地路径] [选项]
```

参数说明：
- `--user`, `-u`: 用户ID (必填)
- `--workspace`, `-w`: 工作区ID (必填)
- `--path`, `-p`: 本地目录路径 (必填)
- `--desc`, `-d`: 描述信息 (选填)
- `--api`, `-a`: API地址，默认为 http://localhost:8089/api
- `--restart`, `-r`: 是否自动重启容器

示例：
```bash
python scripts/mount_tool.py mount -u user1 -w workspace1 -p D:\projects\mycode -d "我的项目代码" -r
```

#### 卸载目录

```bash
python scripts/mount_tool.py unmount --user [用户ID] --workspace [工作区ID] [选项]
```

参数说明：
- `--user`, `-u`: 用户ID (必填)
- `--workspace`, `-w`: 工作区ID (必填)
- `--api`, `-a`: API地址，默认为 http://localhost:8089/api
- `--restart`, `-r`: 是否自动重启容器

示例：
```bash
python scripts/mount_tool.py unmount -u user1 -w workspace1 -r
```

#### 列出挂载

```bash
python scripts/mount_tool.py list [选项]
```

参数说明：
- `--api`, `-a`: API地址，默认为 http://localhost:8089/api

示例：
```bash
python scripts/mount_tool.py list
```

#### 重启容器

```bash
python scripts/mount_tool.py restart [选项]
```

参数说明：
- `--api`, `-a`: API地址，默认为 http://localhost:8089/api

示例：
```bash
python scripts/mount_tool.py restart
```

## 使用场景

### 快速开发环境设置

当您需要在新机器上快速设置开发环境时：

```bash
# 启动容器服务
docker compose -f docker-compose.dev.yml up -d

# 挂载项目代码目录
python scripts/mount_tool.py mount -u dev1 -w main -p D:\projects\openmanus -r

# 挂载另一个工作目录
python scripts/mount_tool.py mount -u dev1 -w examples -p D:\projects\examples -r
```

### 团队协作

团队成员可以使用相同的工具来确保一致的挂载配置：

```bash
# 查看当前挂载
python scripts/mount_tool.py list

# 根据团队规范添加指定挂载
python scripts/mount_tool.py mount -u team1 -w shared -p D:\team\shared_code -r
```

### 定期维护

系统管理员可以使用该工具进行定期维护：

```bash
# 检查当前挂载
python scripts/mount_tool.py list

# 重启容器应用更新
python scripts/mount_tool.py restart
```

### 处理挂载配置变更

当您修改挂载配置后，系统现在使用 docker compose 进行容器重启，确保挂载配置正确应用：

```bash
# 添加新的挂载
python scripts/mount_tool.py mount -u dev1 -w project1 -p D:\projects\new_project -r

# 系统将自动执行以下操作：
# 1. 更新 docker-compose.dev.yml 中的挂载配置
# 2. 使用 docker compose 重启容器，确保新配置生效
# 3. 提供重启状态反馈
```

这种方式解决了以前直接使用 Docker API 重启容器时，配置更改可能未完全应用的问题。通过完整的 docker compose 重启流程，确保所有配置（包括挂载点）都能正确应用。

## 常见问题与解决方案

### 挂载失败

问题：执行挂载命令后显示失败
解决方案：
1. 确认目录路径是否正确且存在
2. 检查用户ID和工作区ID是否合法
3. 确认监控容器是否正常运行
4. 检查网络连接是否正常

### Windows 路径格式问题

问题：Windows 路径格式（如 `D:\path\to\folder`）导致挂载失败
解决方案：
1. 系统已自动处理 Windows 路径中的反斜杠，将其转换为正斜杠
2. 如果仍然遇到问题，可以手动将路径中的反斜杠 `\` 替换为正斜杠 `/`
3. 避免在路径中使用特殊字符
4. 如果路径包含空格，请使用引号包围整个路径

### API 连接问题

问题：无法连接到 API
解决方案：
1. 确认监控容器是否正常运行
2. 检查 API 地址是否正确，可能需要使用 `--api` 参数指定正确的地址
3. 查看容器日志以获取更多信息

### 重启容器超时

问题：重启容器时操作超时
解决方案：
1. 增加 API 超时时间
2. 检查容器状态，可能需要手动干预
3. 检查 Docker 服务状态
4. 如果使用 docker compose 重启失败，系统会尝试使用 Docker API 作为备选方案

### Docker Compose 未安装

问题：重启容器时提示 Docker Compose 未安装
解决方案：
1. 监控容器现在会自动检测宿主机上可用的 docker compose 命令
2. 如果检测失败，将回退到使用 Docker API 重启容器
3. 确保宿主机上已安装 Docker CLI 且已挂载到监控容器

## 高级用法

### 自定义 API 地址

如果您的监控容器运行在不同的端口或地址，可以使用 `--api` 参数指定：

```bash
python scripts/mount_tool.py list --api http://192.168.1.100:8089/api
```

### 批处理脚本

您可以创建批处理脚本来自动执行一系列操作：

```bash
#!/bin/bash
# 批量设置开发环境

# 清理旧挂载
python scripts/mount_tool.py unmount -u dev1 -w workspace1
python scripts/mount_tool.py unmount -u dev1 -w workspace2

# 添加新挂载
python scripts/mount_tool.py mount -u dev1 -w workspace1 -p /path/to/workspace1
python scripts/mount_tool.py mount -u dev1 -w workspace2 -p /path/to/workspace2

# 重启容器使更改生效
python scripts/mount_tool.py restart
```

## 系统架构和工作原理

挂载工具是监控容器解决方案的客户端组件，它通过 HTTP API 与监控容器通信，从而管理挂载配置和容器生命周期。

完整系统架构包括：

1. **挂载工具（客户端）**：提供用户友好的命令行界面
2. **监控容器（服务端）**：管理挂载配置和容器生命周期
3. **开发容器**：实际的开发环境，由监控容器管理

挂载工具的工作流程：

1. 用户执行命令
2. 工具构建 API 请求并发送到监控容器
3. 监控容器处理请求并执行相应操作
   - 对于重启操作，监控容器现在使用 docker compose 确保配置完全应用
4. 工具接收响应并向用户展示结果

## 贡献与反馈

如果您发现任何问题或有改进建议，请通过以下方式提交：

1. 在 GitHub 仓库提交 Issue
2. 发送邮件至开发团队
3. 提交 Pull Request 贡献代码

## 更多资源

- [监控容器文档](README-monitor.md)
- [API 参考](api-reference.md)
- [开发指南](development-guide.md)
