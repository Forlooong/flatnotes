# Flatnotes Shared Notes

[dullage/flatnotes](https://github.com/dullage/flatnotes) v5.5.5 的独立 fork：[Forlooong/flatnotes](https://github.com/Forlooong/flatnotes)，分支 `vps-flatnotes-oidc`。固定上游 `7f5b773c9cb37cc84978079ed4790e7de38d3970`。

正式入口：[共享笔记](https://www.040323.xyz/apps/notes/)。未登录自动进入 Authelia，成功后回到原深层路径与查询。使用 OIDC Code + S256 PKCE；全部授权 site-users 成员共享笔记和附件，无独立应用密码、无用户数据分区。

应用会话仅存单实例内存，Cookie Secure/HttpOnly/Lax/Path=/apps/notes/。每个请求复核当前网站会话，网站退出、空闲/绝对过期或身份变化后拒绝访问；写请求要求精确 Origin。重启后重新登录。

中文首页含最近修改与搜索；菜单展开搜索笔记、全部笔记、切换主题、退出登录。保留上游编辑器、搜索、标签和主题；编辑器部分英文沿用上游。

页面已统一网站首页的浅灰绿背景、深绿文字、系统字体、三角标、页面边距与细线列表，覆盖首页、搜索、阅读和编辑器。旧版前端已被用户判定审核不通过；这次样式修正已发布，本地桌面/移动真实 Chromium 检查通过，新版视觉审核仍待用户确认。

## 开发检查

```text
uv sync --locked --no-dev
uv run --no-dev --with httpx python -m unittest discover -s tests -v
npm ci
npm run build
python -m compileall -q server
```

`tests/check_ui.py` 使用隔离 UI fixture；`tests/check_production.py` 打开真实 Chromium 两账户窗口，用户仅在网站输入密码，不保存凭据或 Cookie。测试脚本与 `docs/evidence/` 结果分开；`work/`、截图和构建目录不进 Git。

## 部署与数据

生产源码 `76dd37d075f0cb120d0677969f793fad3108594d`，镜像 `site-flatnotes:<完整commit>`，仅监听 127.0.0.1:18080，UID/GID 1000、256MiB/0.5CPU。宿主机唯一共享目录 `/data/apps/notes/shared/` 包含 markdown、Whoosh 索引和附件。

从 GitHub 获取完整 commit 后执行该版本 `deploy.sh <40位commit>`。发布目录 `/opt/flatnotes/releases/<commit>`，`current` 指向当前版本，保留 source-commit、SHA256SUMS、部署时间与 previous-release。systemd `flatnotes.service` 绑定 data.mount、RequiresMountsFor=/data，启动前核验 UUID `6cb900e1-697a-4305-884c-cfd1620f5adf`；Docker restart=no，缺盘不自动创建数据目录。

当前 previous-release 为 `01946e76e28ddf61feae3df9bdb4c87a1e9b3ef4`。回滚本次样式仅停止 Notes 服务、原子切回旧 release symlink 并启动 Notes，保留共享数据，网站和身份不变。操作与保护证据见 `docs/evidence/2026-09-28/style-unification/release.md`。不得 down -v、删除数据或操作代理容器。

## 验证与限制

10 项认证/HTTP 测试、前端构建、真实隔离 Authelia 与应用联测、正式双账户桌面/移动 Chromium 的深层回跳、共享编辑/附件、菜单/搜索/主题、CSRF、网站旧 Cookie 退出重放和应用退出通过。空闲/绝对过期用真实隔离 provider 缩短期限验证，生产保持 30m/8h。部署证据在 `D:/DEV/Lab/vps-site/docs/evidence/2026-09-28/notes-release.md`，本仓库有 production-checks.json 和匿名边界结果。

并发编辑沿用上游最后写入语义，不提供协作锁或冲突合并。没有 WebSocket。至少两个真实应用 SSO、整机重启/真实缺盘、最终参考截图视觉确认与真实 VLESS + Reality 客户端验证尚未完成。npm audit 报告 8 项依赖公告（含编辑器传递 DOMPurify）；本轮未扩大为全依赖升级，不能据此宣称全部安全风险已解决。备份自动化尚未部署。
