# Flatnotes Shared Notes

这是 [dullage/flatnotes](https://github.com/dullage/flatnotes) `5.5.5` 的本地 fork，当前固定上游 commit 为 `7f5b773c9cb37cc84978079ed4790e7de38d3970`。

目标部署路径为 `https://www.040323.xyz/apps/notes/`。应用通过现有 Authelia 的 OIDC 登录，未登录访问会回跳本站统一登录；应用不保存独立密码。应用会话是单实例内存会话，退出或过期后必须重新通过 OIDC 登录。

Flatnotes 的 markdown 笔记、Whoosh 索引和附件使用同一个共享 `/data` 目录。`zhuqing` 与 `yaojia` 共享查看和编辑权限，当前没有按用户隔离数据的设计。

本地检查：

```text
uv sync --locked --no-dev
uv run --no-dev python -m unittest discover -s tests -v
npm ci
npm run build
python -m compileall -q server
```

生产配置中的 OIDC issuer、回调地址和 `/data/apps/notes/shared` 挂载由部署文件提供；秘密只留在 VPS 的受限目录。生产部署和浏览器登录闭环仍须以 `SPEC.md` 和 `LOG.MD` 的证据为准。
