# Flatnotes 施工日志

## 2026-09-28 — OIDC 共享笔记 fork 初版

目标：将上游 Flatnotes 适配为 `/apps/notes/` 下的统一 OIDC 应用，并按用户要求保留单一共享笔记目录。

上游：`https://github.com/dullage/flatnotes`，固定 commit `7f5b773c9cb37cc84978079ed4790e7de38d3970`，版本 `5.5.5`。

修改：增加 OIDC Authorization Code + PKCE relying party；移除本地账号密码前端入口；增加 HTTPS discovery、RS256 ID Token、issuer/audience/nonce/时间声明校验；使用短期 state Cookie 和内存应用会话；退出跳转本站 Authelia logout。配置和 compose 固定 `/apps/notes/`、回环 18080、数据盘共享目录。首页恢复中文“共享笔记”视觉和菜单中的搜索/全部笔记选项。

数据决定：不创建用户独立目录；`zhuqing` 与 `yaojia` 共享 `/data/apps/notes/shared/` 中全部 markdown、索引和附件，拥有相同编辑权限。无旧数据迁移。

验证：Python OIDC 单元流程通过；`npm run build` 通过；`python -m compileall -q server` 通过。生产 OIDC provider、浏览器回跳、真实两个账户、并发编辑和部署尚未验证。

风险：Authelia 当前配置尚未发布 OIDC provider/client；应用 release 尚未部署；共享目录最后写入结果由上游文件写入语义决定，未增加协作锁或冲突合并。

HASH：`flatnotes-2026-09-28-oidc-shared-v1`

## 2026-09-28 — 审查与修正初稿（发布前）

本轮目标：复核初稿，保留原有未提交修改，不沿用旧通过声明。
修改：标准 OIDC discovery/RS256/azp/iat/nonce/at_hash、UserInfo sub 绑定、实时网站 authz 与 site Cookie 绑定、成员授权、精确 Origin CSRF、POST 应用退出、深层回跳、JSON 健康响应、systemd UUID 和挂载依赖、非 root 容器、固定镜像 digest、失败回滚。
关键文件：server/auth/oidc.py、server/main.py、client/views/LogIn.vue、docker-compose.yml、deploy.sh、flatnotes.service、check-data.sh、tests/。共享目录及上游最后写入语义保留。
验证：最终认证修改后 9 项 unittest/HTTP 边界通过；npm build 通过；真实 Chromium 1440/390 首页、菜单、搜索、主题、编辑器、深层刷新通过，截图实际查看。页面验证使用隔离 fixture，不能代替生产 OIDC。隔离 provider 发现密钥模板缩进错误，已修正；标准 consent 流程测试正在补齐。
固定上游：7f5b773c9cb37cc84978079ed4790e7de38d3970；fork：Forlooong/flatnotes；本轮 commit 尚未生成，生产尚未部署。
临时资产：work/tests/、test-data/、.venv/、node_modules/、client/dist/、本地截图均忽略 Git；测试进程和 fixture 数据在任务结束清理。
遗留：provider 最终配置、容器启动、生产两个账户、网站退出/过期、真实共享编辑和附件、回滚及代理前后对比；原会话参考截图未在当前附件中提供，最终视觉需用户确认。

HASH: fc80d171bb6a5bb941191ca41871567d4294839c610198957e4b75416c63b167

## 2026-09-28T03:45:17+00:00 — Flatnotes 实际 OIDC 修复与首应用发布

目标：审查未经验证初稿，完成标准身份、共享工作区、真实浏览器及固定版本发布，保留已有修改。
修改范围：server/auth/oidc.py、server/main.py、client 中文首页/菜单、Dockerfile/compose/entrypoint、deploy.sh、check-data.sh、flatnotes.service、tests、README/SPEC。初稿 RedirectResponse(location=...) 在真实联测返回 500，已改为 url 并新增成功登录/回调 HTTP 回归；同时修正 at_hash access_token、精确 Cookie Path、网站实时成员和会话绑定、Origin/POST 退出、深层回跳及部署首次失败回滚。
设计：标准 Code+S256 PKCE、单次 state/nonce/verifier、RS256/JWKS/iss/aud/azp/sub/iat/exp/at_hash、UserInfo sub 绑定；回环网站 authz 每请求复核，无缓存。全部 site-users 共享笔记和附件，最后写入语义沿用上游，不引入协作锁。UUID/data.mount 保护拒绝缺盘。
验证：修改后 10 项 unittest/真实 HTTP 通过；npm build 通过；真实隔离 Authelia+候选容器的标准 consent、签名回调、成员拒绝、PKCE/code replay/精确回调、共享/并发编辑、附件、CSRF、网站退出、空闲和绝对期限通过。生产 zhuqing/yaojia 用户手动登录后的 1440/390 Chromium 实际编辑器、共享编辑/附件、深层查询回跳及刷新、菜单/全部笔记/主题、Cookie、CSRF、网站旧 Cookie 退出重放 401 与应用退出 401 通过。截图超时通过 bring_to_front 修正；退出中间页竞态通过等待原生 logout POST 成功修正。最终报告 production-checks.json，未落盘密码/token/Cookie。
发布：GitHub Forlooong/flatnotes vps-flatnotes-oidc，生产 source 01946e76e28ddf61feae3df9bdb4c87a1e9b3ef4；/opt/flatnotes/releases/01946e76e28ddf61feae3df9bdb4c87a1e9b3ef4，03:26:29 UTC，systemd active/enabled、healthy、127.0.0.1:18080、1000:1000、256MiB/0.5CPU、restart=no。source manifest 核对，错误 UUID stub 拒绝启动。网站 source 718a5d77d6c5f530c145e7da5fb758b494f16c8a，身份 c680822408814f2bb03d013431d46fc6488a2ea6。完整回滚/代理证据位于 vps-site/docs/evidence/2026-09-28/notes-release.md；首次 Notes 回滚停止并禁用服务，保留数据/release。
清理：本轮三组 UUID 测试笔记/附件精确清理；本地 UI fixture 进程停止，临时脚本和数据清理，截图/保护快照忽略 Git 留待人工复核；既有未知 test-data 保留。开发 node_modules/.venv/dist 可闲置删除重建，未提交。
风险与遗留：npm audit 8 项公告（含编辑器 DOMPurify），未全依赖升级或证明不存在利用；最终参考视觉、真实主机重启/缺盘、VLESS+Reality 客户端、自动备份和至少两个真实应用 SSO 未完成。无 WebSocket，不宣称跨应用 SSO 或全部风险解决。
Git：实际修复/发布 01946e76e28ddf61feae3df9bdb4c87a1e9b3ef4；前序施工 commits 03b18bd、9234b8d、fb483c8。本次测试/文档收尾 commit 在其后单独生成，不替换生产固定源码。

HASH: 3d75afcbfd595a9178b075393255921bd1ca171fb50097f9622da6b251d2e129

## 2026-09-28 — 本轮临时资产清理结果澄清

此前最终记录的“本地临时脚本/数据清理”以此条实际结果为准：本地 UI fixture 与 preview 进程已停止，删除 flatnotes/work/tests/ui-data 及本轮脚本的 PowerShell 命令被自动审批拒绝，返回仅为 blocked by policy，因此本地 work/tests 文件保留、忽略 Git，未绕过审批删除。vps-site/work/tests 本轮脚本也保留待清理；可删除范围为本轮创建的命名脚本与 fixture，不能删除既有未知 test-data、参考资产或 vps-authelia checkout。

VPS 隔离测试容器/数据及六个完整 SHA 的 /opt/deploy/notes-validation staging 已精确清理；三组生产 UUID 测试笔记/附件已精确清理，随后运行现有 FileSystemNotes 同步索引。正式 release/用户数据/密钥/回滚保留。截图/原始保护快照待人工确认后可删除，开发依赖与构建缓存未 broad prune。本条不改变已通过功能和生产源码 commit。

HASH: 8edfc0f160897bef822289a9717f6a18274868a4a76ccdd70ab412a1f7c2f110
