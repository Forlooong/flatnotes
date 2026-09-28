# Flatnotes Shared Notes

[dullage/flatnotes](https://github.com/dullage/flatnotes) v5.5.5 的独立 fork：[Forlooong/flatnotes](https://github.com/Forlooong/flatnotes)，分支 `vps-flatnotes-oidc`。固定上游 `7f5b773c9cb37cc84978079ed4790e7de38d3970`。

正式入口：[共享笔记](https://www.040323.xyz/apps/notes/)。未登录自动进入 Authelia，成功后回到原深层路径与查询。使用 OIDC Code + S256 PKCE；全部授权 site-users 成员共享笔记和附件，无独立应用密码、无用户数据分区。

应用会话仅存单实例内存，Cookie Secure/HttpOnly/Lax/Path=/apps/notes/。每个请求复核当前网站会话，网站退出、空闲/绝对过期或身份变化后拒绝访问；写请求要求精确 Origin。重启后重新登录。

中文首页含最近修改与搜索；菜单展开搜索笔记、全部笔记、切换主题、退出登录。品牌与标签为 Flatnotes，图标复用网站应用 notes.svg。桌面导航及内容采用最大 960px 居中布局；新建/编辑页包含中文工具栏、提示、弹窗、Markdown/富文本与预览，保留保存、草稿、附件、标签和浅暗主题。实际输入区保留输入光标，阅读区正文可选择复制。

六项前端整改已于 2026-09-28 实施并发布。当前版本完成本地及正式账户 Chromium 检查，用户视觉审核尚未确认通过。网站首页的锁/可点击和 favicon 已同步更新；已部署 Flatnotes 仅保留原简介，不显示额外“打开共享笔记”或“请先登录”。当前规范和交接提示词见 `D:/DEV/Lab/project-docs/docs/plans/flatnotes-ui-revision.md` 与 `D:/DEV/Lab/project-docs/docs/prompts/flatnotes-ui-revision-prompt.md`。

## 开发检查

```text
uv sync --locked --no-dev
uv run --no-dev --with httpx python -m unittest discover -s tests -v
npm ci
npm run build
python -m compileall -q server
```

`tests/check_ui.py` 使用隔离 UI fixture；`tests/check_production.py` 打开真实 Chromium 两账户窗口，用户仅在网站输入密码，不保存凭据或 Cookie。测试脚本与 `docs/evidence/` 结果分开；`work/`、截图和构建目录不进 Git。

此前六项整改使用 `tests/check_revision.py`，新报告位于 `docs/evidence/2026-09-28/ui-revision/production/production-checks.json`，覆盖 1280/1440/1920/390/320（移动含设备/触控模拟）、登录深层回跳、中文编辑/草稿/附件、主题、返回首页/刷新/前进后退/退出。测试进程已结束；凭据仅由用户在网站输入，未记录 Cookie/token/storage state。旧 style-unification 测试没有通过报告，仍只作历史资料。

## 部署与数据

生产源码 `d6e73ef9fd50365603500ef6a8483512138f36cd`，镜像 `site-flatnotes:<完整commit>`，仅监听 127.0.0.1:18080，UID/GID 1000、256MiB/0.5CPU。宿主机唯一共享目录 `/data/apps/notes/shared/` 包含 markdown、Whoosh 索引和附件。

从 GitHub 获取完整 commit 后执行该版本 `deploy.sh <40位commit>`。发布目录 `/opt/flatnotes/releases/<commit>`，`current` 指向当前版本，保留 source-commit、SHA256SUMS、部署时间与 previous-release。systemd `flatnotes.service` 绑定 data.mount、RequiresMountsFor=/data，启动前核验 UUID `6cb900e1-697a-4305-884c-cfd1620f5adf`；Docker restart=no，缺盘不自动创建数据目录。

当前 previous-release 为 `18a0c01c9e50a828d0b5c3b9ad92e7adfda47de8`。回滚仅停止 Notes、原子切回旧 release symlink 并启动 Notes，保留共享数据。此次发布/回滚/验证证据见 `docs/evidence/2026-09-28/attachment-lifecycle/release.md`；网站有独立固定提交和回滚，身份不变。不得 down -v、删除数据或操作代理容器。

## 验证与限制

10 项认证/HTTP 测试、前端构建、真实隔离 Authelia 与应用联测、正式双账户桌面/移动 Chromium 的深层回跳、共享编辑/附件、菜单/搜索/主题、CSRF、网站旧 Cookie 退出重放和应用退出通过。空闲/绝对过期用真实隔离 provider 缩短期限验证，生产保持 30m/8h。部署证据在 `D:/DEV/Lab/vps-site/docs/evidence/2026-09-28/notes-release.md`，本仓库有 production-checks.json 和匿名边界结果。

并发编辑沿用上游最后写入语义，不提供协作锁或冲突合并。没有 WebSocket。至少两个真实应用 SSO、整机重启/真实缺盘、最终参考截图视觉确认与真实 VLESS + Reality 客户端验证尚未完成。npm audit 报告 8 项依赖公告（含编辑器传递 DOMPurify）；本轮未扩大为全依赖升级，不能据此宣称全部安全风险已解决。备份自动化尚未部署。

此前六项报告限制：没有等待生产 30m/8h 自然过期；前端失效状态使用服务端响应模拟，真实退出已经验证。一次本地 removeChild 异常在后续完整/局部和生产测试均未复现，原因未确认。最终视觉效果仍需用户确认。

当前附件管理：宿主机 `/data/apps/notes/shared/attachments/`（容器 `/data/attachments/`）。网页重复上传按内容复用；笔记与浏览器保留草稿共同保护附件，明确丢弃草稿、保存移除引用或删除最后引用笔记后自动清理受管文件；清理失败的明确丢弃会在下次编辑重试。行为与边界见 `docs/attachment-lifecycle.md`。返回网站首页为独立右下角房屋图标胶囊按钮。2026-09-28 本轮真实账户桌面/移动专项通过，结果见 `docs/evidence/2026-09-28/attachment-lifecycle/production/checks.json`；视觉审核待用户确认。
