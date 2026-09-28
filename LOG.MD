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
