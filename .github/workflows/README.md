# CI/CD 部署文档

本文档说明项目的持续集成/持续部署（CI/CD）配置和使用方法。

## 📋 概述

项目使用 GitHub Actions 自动构建 Docker 镜像并推送到 Harbor 私有镜像仓库。

## 🚀 触发条件

### 自动触发

- **分支推送**：推送到 `main` 或 `master` 分支
- **标签推送**：推送符合 `v*.*.*` 格式的 Git 标签（如 `v1.0.1`）
- **Pull Request**：创建或更新针对 `main` 或 `master` 的 PR

### 手动触发

在 GitHub Actions 页面可以手动触发工作流（`workflow_dispatch`）。

## 🔧 配置要求

### 必需的 GitHub Secrets

在仓库的 Settings → Secrets and variables → Actions 中配置以下密钥：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `HARBOR_REGISTRY` | Harbor 仓库地址 | `harbor.example.com` |
| `HARBOR_USERNAME` | Harbor 用户名 | `admin` |
| `HARBOR_PASSWORD` | Harbor 密码 | `your-password` |

## 📦 版本管理策略

### 版本号生成规则

#### 1. Git Tag Push（正式发布）

```bash
git tag v1.0.1
git push origin v1.0.1
```

**生成版本**：`1.0.1`  
**生成标签**：
- `{harbor}/ai-agent/neg-agent:1.0.1`
- `{harbor}/ai-agent/neg-agent:latest`

#### 2. 分支 Push（开发版本）

```bash
git push origin main
```

**版本计算**：
- 查找最新的 Git Tag（如 `v1.0.5`）
- 自动递增修订号：`1.0.5` → `1.0.6`
- 如果没有任何 Tag，从 `0.0.1` 开始

**生成版本**：`1.0.6`  
**生成标签**：
- `{harbor}/ai-agent/neg-agent:1.0.6`
- `{harbor}/ai-agent/neg-agent:latest`

**自动操作**：
- 自动创建 Git Tag `v1.0.6`
- 自动推送回仓库

#### 3. Pull Request（测试版本）

**生成版本**：`pr-123-abc1234`（PR 编号 + 短 SHA）  
**生成标签**：
- `{harbor}/ai-agent/neg-agent:pr-123-abc1234`

**注意**：PR 构建不推送镜像，仅验证构建成功。

## 🐳 Docker 镜像构建

### 构建配置

- **上下文目录**：`./backend`
- **Dockerfile 路径**：`./backend/Dockerfile`
- **目标平台**：`linux/amd64`
- **缓存机制**：GitHub Actions Cache

### 构建参数

- `VERSION`：版本号
- `VCS_REF`：Git commit SHA

### 镜像标签

最终推送到 Harbor 的镜像路径：

```
{HARBOR_REGISTRY}/ai-agent/neg-agent:{VERSION}
{HARBOR_REGISTRY}/ai-agent/neg-agent:latest
```

## 📝 使用流程

### 日常开发流程

```bash
# 1. 开发功能
git checkout -b feature/new-feature
# ... 修改代码 ...

# 2. 提交代码
git add .
git commit -m "feat: add new feature"
git push origin feature/new-feature

# 3. 创建 PR
# 在 GitHub 上创建 Pull Request
# CI 会自动构建测试镜像（不推送）

# 4. 合并到 main
# 合并后自动：
#   - 构建生产镜像
#   - 自动递增版本号
#   - 创建 Git Tag
#   - 推送到 Harbor
```

### 正式发布流程

```bash
# 1. 确保 main 分支是最新的
git checkout main
git pull

# 2. 打标签发布
git tag v1.2.0
git push origin v1.2.0

# 3. 自动触发 CI/CD
# CI 会：
#   - 使用 tag 版本号 1.2.0
#   - 构建镜像
#   - 推送到 Harbor
#   - 更新 latest 标签
```

## 🔍 查看构建结果

### GitHub Actions

1. 进入仓库的 **Actions** 标签页
2. 查看最新的工作流运行记录
3. 点击查看详细日志

### 构建摘要

每次构建完成后，会在 GitHub Actions Summary 中显示：

- **Mode**：构建模式（tag/branch/pr）
- **Version**：生成的版本号
- **Ref**：触发的分支或标签
- **Tags**：推送的所有镜像标签

## 🛠️ 常见问题

### Q1: 为什么我的 push 没有触发构建？

**可能原因**：
- 推送的不是 `main` 或 `master` 分支
- 提交者是 `github-actions[bot]`（防止无限循环）
- 只修改了 `.md` 文档文件

### Q2: 版本号如何管理？

**回答**：
- 系统自动基于 Git Tag 递增版本号
- 分支 push 自动 +1 修订号
- 想跨版本更新（如 1.x → 2.0），需手动打 tag

### Q3: 如何回退到旧版本？

```bash
# 方法1：使用具体版本标签
docker pull {harbor}/ai-agent/neg-agent:1.0.5

# 方法2：检出旧的 tag 重新发布
git checkout v1.0.5
git tag v1.0.5-hotfix
git push origin v1.0.5-hotfix
```

### Q4: Harbor 登录失败怎么办？

**检查清单**：
1. 确认 Harbor Secrets 配置正确
2. 检查 Harbor 用户权限
3. 确认 Harbor 服务可访问
4. 查看 GitHub Actions 日志中的具体错误

## 🔐 安全说明

- **不要**在代码中硬编码密码或密钥
- 使用 GitHub Secrets 管理敏感信息
- Harbor 密码定期更新
- 限制 Harbor 用户权限（只给必要的推送权限）

## 📚 相关资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Docker Buildx 文档](https://docs.docker.com/buildx/working-with-buildx/)
- [Harbor 文档](https://goharbor.io/docs/)

## 🆘 获取帮助

遇到问题请：
1. 查看 GitHub Actions 运行日志
2. 检查 Harbor 仓库状态
3. 联系项目维护者
