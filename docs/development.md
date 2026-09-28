# Flatnotes 开发接手指南

本 fork 服务 `/apps/notes/`，使用 Vue 3 + Vite 前端、Python 3.13 + FastAPI 后端。沿用原有主开发分支 `develop`，推送目标为 `Forlooong/flatnotes`；原作者为 `dullage/flatnotes`，不是本站发布目标。

## 程序入口、目录和路由

| 问题 | 位置与职责 |
|---|---|
| 后端入口 | `server/main.py` 的 `app = FastAPI(...)`；Uvicorn 导入 `main:app` |
| 前端入口 | `client/index.html` → `client/index.js` → `client/App.vue` |
| 前端 | `client/`；全局样式 `client/style.css`；状态 `client/globalStore.js` |
| 后端 | `server/`；笔记 `server/notes/`；附件 `server/attachments/` |
| 页面路由 | `client/router.js`：`/`、`/login`、`/new`、`/note/:title`、`/search`；生产统一加 `/apps/notes` 前缀 |
| 后端路由 | `server/main.py` 的 APIRouter、OIDC middleware、静态目录挂载 |
| 页面 | `client/views/Home.vue`、`Note.vue`、`SearchResults.vue`、`LogIn.vue` |
| 组件 | `client/components/`；编辑器 `components/toastui/`；导航/搜索 `client/partials/` |
| API 调用 | `client/api.js`；请求/响应模型 `server/notes/models.py`、`server/attachments/models.py` |
| 配置 | `server/global_config.py`、`server/helpers.py`、`server/auth/oidc.py` 读取环境变量；前端 `vite.config.js`；生产 `docker-compose.yml` |
| 登录鉴权 | `server/auth/oidc.py` + `server/main.py` middleware；身份提供方为网站 Authelia |
| 文件存储 | `server/notes/file_system/file_system.py`、`server/attachments/file_system/file_system.py` |
| 附件引用/去重/清理 | `server/attachments/lifecycle.py` |
| Docker/部署 | `Dockerfile`、`docker-compose.yml`、`entrypoint.sh`、`deploy.sh`、`flatnotes.service`、`check-data.sh` |
| 依赖 | 前端 `package.json` + `package-lock.json`；后端 `pyproject.toml` + `uv.lock` |

## 安装和构建

推荐对照 Docker 使用 Node 24；Python 必须为 3.13（项目限定 >=3.13,<3.14），使用 uv 管理。

```powershell
Set-Location D:\DEV\Lab\flatnotes
uv sync --locked --no-dev
npm ci
npm run build
```

Vite 输出 `client/dist/`。后端启动时会读取并替换其中 HTML 的 base 路径，因此即使只调后端，也要先构建一次前端。构建产物、虚拟环境、node_modules 不提交 Git。

## 本地界面开发：使用现有隔离 fixture

项目已经提供不连接生产账户/数据的 UI fixture，适合修改笔记页面、样式、附件交互：

```powershell
Set-Location D:\DEV\Lab\flatnotes
uv run --no-dev python tests/ui_fixture.py
```

它监听 `127.0.0.1:18081`，页面路径为 `/apps/notes/`，默认数据目录 `work/tests/ui-data/`，会生成一篇示例笔记；Ctrl+C 停止。

手工打开页面前，先访问 `http://127.0.0.1:18081/apps/notes/health`，在该本地页面的浏览器开发者工具 Console 中设置测试 Cookie：

```javascript
document.cookie = "flatnotes_session=fixture-session; Path=/apps/notes/; SameSite=Lax";
document.cookie = "site_session=fixture-site; Path=/; SameSite=Lax";
location.href = "/apps/notes/";
```

这些固定字符串仅是 fixture 内置测试值，不能登录生产。fixture 替代了身份提供方验证，**不能用于证明真实 OIDC 成功，也不能部署或监听公网**；其测试会话约一小时后过期，重启 fixture 可重新生成。测试结束可清除这两个本地 Cookie。

前端修改后运行 `npm run build` 并刷新；也可另开终端运行 `npm run watch` 持续构建。若重新生成的 HTML 尚未包含 `/apps/notes/` base，请重启 fixture 让后端重新处理 HTML。

`npm run dev` 虽然存在，但现有 Vite 开发服务器在 8080，代理目标为 8000，并明确不支持 `FLATNOTES_PATH_PREFIX`；不能直接当作本站 OIDC 全流程开发入口。

## 真实 OIDC 后端怎样启动

实际服务入口命令如下，必须在仓库根目录运行：

```powershell
uv run --no-dev python -m uvicorn main:app --app-dir server --host 127.0.0.1 --port 18080 --no-access-log
```

执行前必须准备存在的独立数据目录，并设置：

- `FLATNOTES_AUTH_TYPE=oidc`
- `FLATNOTES_PATH=<独立数据目录>`
- `FLATNOTES_PATH_PREFIX=/apps/notes`（不带尾斜杠）
- `FLATNOTES_OIDC_ISSUER=<HTTPS 身份提供方地址>`
- `FLATNOTES_OIDC_CLIENT_ID=<注册的客户端 ID>`
- `FLATNOTES_OIDC_REDIRECT_URI=<同源 HTTPS 地址>/apps/notes/api/oidc/callback`
- 可选 `FLATNOTES_SESSION_EXPIRY_SECONDS`，默认 28800。

真实联调还要求 HTTPS 同源入口、准确注册的回调，以及本机 `127.0.0.1:19091/auth/api/authz/auth-request` 身份校验服务。每次应用请求都校验网站 Cookie 和 site-users 成员权限，单独启动 Uvicorn 并不能完成登录。当前没有开箱即用的完整本地身份 Compose；不要通过关闭鉴权或恢复本地密码登录规避这个边界。

## 数据库在哪里

Notes 没有 MySQL/PostgreSQL/SQLite 业务数据库，使用文件存储：

```text
VPS /data/apps/notes/shared/      Docker 内 /data/
├─ *.md                         Markdown 笔记
├─ attachments/                 附件
├─ .flatnotes/                  Whoosh 搜索索引
└─ .attachment-drafts.json      附件引用/草稿登记
```

草稿正文保留在浏览器，后端登记附件引用。所有 site-users 共享这套数据；不是每个账户一份。身份服务的 SQLite 和用户文件在 vps-site 指南中说明。备份 Notes 应覆盖整个共享目录，不能只备份源码或 Docker 镜像。

## API 和鉴权链路

后端 API 均在 `server/main.py`；具体 HTTP 方法以路由装饰器为准：

- 笔记 `/api/notes`、`/api/notes/{title}`，搜索 `/api/search`，标签 `/api/tags`。
- 附件上传 `/api/attachments`、草稿附件登记 `/api/attachment-drafts/{draft_id}`；下载 `/attachments/...`。
- OIDC `/api/oidc/login`、`/api/oidc/callback`、`/api/oidc/logout`。
- 配置 `/api/config`、鉴权检查 `/api/auth-check`、健康检查 `/health`。
- FastAPI 文档 `/docs`，OpenAPI `/openapi.json`。

生产全部带 `/apps/notes` 前缀，例如 `/apps/notes/api/notes`。文档/API/附件同样经过 OIDC 边界，不是公开接口。写请求需匹配准确 Origin。

登录流程：应用 → 网站 Authelia → Code + S256 PKCE → 回调验证 token/state/nonce → 应用内存会话；后续逐次校验网站会话。不要根据前端按钮是否显示判断权限，最终以后端检查为准。

## 验证和部署

```powershell
# 针对后端鉴权/附件修改
uv run --no-dev --with httpx python -m unittest discover -s tests -v

# 前端构建
npm run build
```

UI 用实际浏览器检查；真实 OIDC 需要独立联调验证。`npm test` 目前只是失败占位命令，不是有效测试。`tests/check_production.py` 等脚本会连接生产，不应当成本地日常测试随手执行。

生产 Compose 使用 host 网络、回环 18080、UID/GID 1000、256MiB/0.5CPU；挂载 `/data/apps/notes/shared`。systemd 和 `check-data.sh` 负责数据盘依赖与 UUID 检查。它是 VPS 发布配置，不是 Windows 一键开发配置。

在 VPS `/opt/deploy/flatnotes` 更新你自己的 origin 后，只从已审查完整 SHA 提取/执行相应版本的 `deploy.sh <40位SHA>`。脚本创建 `/opt/flatnotes/releases/<SHA>`，构建镜像并管理 current/previous release。部署前先看 `README.md` 的挂载、回滚和数据保护要求；推送 develop 不会自动执行该部署。

## Git 日常用法

```powershell
Set-Location D:\DEV\Lab\flatnotes
git status
git remote -v
git switch develop
git pull --ff-only origin develop
git switch -c feat/任务名
# 修改、验证、追加 LOG.MD 和 LOG-INDEX.MD
git diff
git add <本轮明确修改的文件>
git commit -m "说明实际修改"
git switch develop
git merge --ff-only feat/任务名
git push origin develop:develop
git branch -d feat/任务名
```

占位符需要替换，出错就停止。当前 origin 是 `https://github.com/Forlooong/flatnotes.git`；upstream fetch 是 `https://github.com/dullage/flatnotes.git`，push 为 `DISABLED`。新克隆需重新设置：

```powershell
git remote set-url --push upstream DISABLED
```

若新克隆没有 upstream，先 `git remote add upstream https://github.com/dullage/flatnotes.git`。获取上游用 `git fetch upstream`；此操作既不向原作者写入，也不自动升级本站。不要运行 `git push upstream`、force push 或 mirror push。
