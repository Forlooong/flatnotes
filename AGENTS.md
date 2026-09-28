# Flatnotes Fork 约定

本目录是 `dullage/flatnotes` 固定上游的本地 fork，服务 slug 为 `notes`，正式路径只能是 `https://www.040323.xyz/apps/notes/`。

- 先读 `README.md`、`SPEC.md`、`LOG-INDEX.MD`，再按 HASH 精确读取 `LOG.MD`。
- 认证只使用 Authelia OIDC Authorization Code + PKCE；不得恢复 Flatnotes 本地用户名密码登录。
- `/data` 是共享笔记目录，两个已授权网站账户共同查看、创建、编辑和删除笔记及附件；不按用户拆分目录。
- 不提交 OIDC 密钥、用户数据、cookie、真实配置或构建缓存。
- 测试脚本放 `tests/`，证据放 `docs/evidence/<日期>/`，临时文件放 `work/` 并在任务结束清理。
- 生产发布使用完整 source commit、固定构建输入、`deploy.sh` 和保留 release 回滚；不得修改 3x-ui/Xray、代理端口、证书或 stream 配置。
