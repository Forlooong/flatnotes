# 附件生命周期与返回入口发布验证

时间：2026-09-28 06:30 UTC。用户手动在本轮新 Chromium 窗口登录，未读取或保存凭据、Cookie、token、storage state。

## 固定发布

- Flatnotes source `d6e73ef9fd50365603500ef6a8483512138f36cd`，GitHub 分支 vps-flatnotes-oidc 已包含此提交；VPS `/opt/flatnotes/releases/d6e73ef9fd50365603500ef6a8483512138f36cd`，当前 symlink/source-commit 一致，服务 active、容器 healthy/restarts=0。
- 网站 source `b60e2ff5d764b6f0a2a642d5a53fa9d8134c6fc2`，GitHub main 已包含此提交；bundle `d6b57752247cf4d7`；release `/opt/deploy/vps-site-releases/20260928T062625Z-b60e2ff5d764.LwnnIR`。
- 身份 source `c680822408814f2bb03d013431d46fc6488a2ea6` 未变，启动时间 `2026-09-28T03:26:38.383255554Z`、restarts=0。
- Notes previous-release `18a0c01c9e50a828d0b5c3b9ad92e7adfda47de8`。回滚按原流程只停止 Notes、原子切回 previous-release，再启动 Notes；不改共享目录。
- 网站回滚：对上述本轮 release 使用 `server/rollback-home.sh`，恢复其中 previous-index/previous-routes（即上轮 c9209559f34e4475f4d9bd7fc7682af78bbc01ab）。不回滚用户密码、数据或代理资源。

## 实际验证

- 本地 npm build、4 项附件单元和 5 项 HTTP 边界通过。覆盖去重、其他笔记/草稿引用、上传待处理、引用重启保留、扫描失败暂停删除、新增写接口匿名/Origin 拒绝与保存后清理。
- 本地和正式 Chromium 1440×1000、390×844（移动设备/触控模拟）：重复图片只用同一 URL；离开编辑、刷新、独立按钮返回网站后恢复草稿，附件可读取；放弃修改清理；正式保存保留；移除引用再保存清理；新建/删除和按钮布局通过。新生产报告 `production/checks.json`，pageErrors=[]。用户回复“已在新窗口登录”只确认登录，不等于视觉认可。
- 本地模拟清理 503：文件保守保留，重新进入编辑页自动重试后删除。浏览器待清理 ID 可恢复失败的明确丢弃操作。
- 首页本地及正式资源的延迟服务端响应模拟：复核期间锁闪烁次数 0；聚焦/点击合并请求；失效结果阻止导航；成功授权进入；七项保持禁用。生产正常登录和应用实际往返另由真实账户流程验证。没有等待自然 30m/8h 过期，也没有重新运行全部旧认证测试。
- 网站 14 个文件 HTTP 内容 SHA256 等于源码；保护快照前后容器启动/重启、挂载、443、证书、stream/vhost/nginx 配置、代理业务配置和归一化防火墙一致。只 reload 验证过的静态 include，不重启 OpenResty/身份/3x-ui。
- 正确数据盘 UUID：6cb900e1-697a-4305-884c-cfd1620f5adf。发布前生产 0 笔记/0 附件，存量清理删除 0；正式测试后应用已删除全部具名测试数据，复核 0 笔记、0 附件、0 受管文件、0 草稿登记。

## 限制与临时资产

- 用户视觉审核尚未确认通过；截图仅供复核，不代表用户验收。
- 历史文件/不带 draftId 的旧 API 上传不自动删除；异常关闭、离线或手动清空浏览器数据时可能留下保守引用，需盘点处理。正文无法读取则暂停删除；没有用短 TTL 清掉保留草稿。
- 原编辑器 SVG width=auto 控制台警告仍存在；本轮无 pageerror，不扩展无关依赖/编辑器修改。构建仍有原大 chunk 提示。
- 本轮所有浏览器和本地服务已结束，18081/8765 无监听；不可复用旧 PID/会话。截图、原始保护快照仅本地保留，视觉审核后可删除。
- 自动审批拒绝本地测试资产删除命令，原因仅“blocked by policy”，未改用其他方式绕过。可删除的本轮目录为 `flatnotes/work/tests/attachment-ui-data/`；旧 fixture 中本轮产生的 `附件生命周期验证-ccee94aa.md`、attachments 内 ccee94aa/03649af3/2ba67419/346bc054/febbf585/9248e3d3 六个同前缀 png 及 `.attachment-drafts.json` 仍保留。旧 fixture 的其他文件不属于本轮清理范围。
- `vps-site/work/tests/attachment-lifecycle/` 保存前后原始快照/最终状态；待复核后可删除。构建目录/现有依赖不进 Git，未创建依赖副本。
