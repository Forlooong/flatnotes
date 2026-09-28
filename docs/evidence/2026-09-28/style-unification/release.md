# Notes 与网站首页样式统一发布

用户反馈旧版前端审核不通过。本次仅修正视觉样式；新版用户视觉审核待确认，自动测试不能替代该结论。

- GitHub / VPS source：`76dd37d075f0cb120d0677969f793fad3108594d`，分支 `vps-flatnotes-oidc`。
- 发布时间：2026-09-28T04:11:39Z；release `/opt/flatnotes/releases/76dd37d075f0cb120d0677969f793fad3108594d`。
- 网站 source `718a5d77d6c5f530c145e7da5fb758b494f16c8a`、身份 source `c680822408814f2bb03d013431d46fc6488a2ea6` 未改变；只重建并更新 Notes。
- 固定镜像基础输入，生产 build、compileall 和部署健康响应 JSON 解析通过；source-commit、完整 release SHA256SUMS 核对通过，服务 active、容器 healthy、1000:1000、host network、restart=no。/data UUID 正确。
- 真实本地 Chromium 1440/390/320、移动触控模式的浅色计算颜色/字体/左右边距与线上网站首页一致；菜单、搜索、深层阅读刷新、浅暗主题与编辑器、新建保存和再次编辑通过，无横向溢出、无 pageerror。见 checks.json。生产真实成员浏览器检查在等待用户手动登录时启动，结果另记。
- 04:09:16Z / 04:12:58Z 保护快照对比通过，见 protected-comparison.json。3xui_app 与 OpenResty 启动时间仍为 2026-09-21T11:50:46、restarts=0；证书/stream/main/vhost/主页以及规范化 inbounds/settings/iptables/ip6tables 未变化。无代理重启、无网站 reload。
- 正式匿名检查：health 为 JSON `"OK"`，API 与 CSS 仍要求授权返回 401，HTML 深层请求跳转为 302（需 Accept:text/html；普通非 HTML 请求为 401）。见 public-checks.json。未为了匿名样式抓取放宽认证。
- 运行容器样式资源 SHA256：index-BDlDbwjQ.css `259e85505c4da3bdd840ca1d3d6018ba30b48131d744a7dd99a9838b1c38bb1d`；Note-mPyc_Fn4.css `df8afe3719a6bc1d1e67d2ca56ea1f5c6b76819d237cf47b17429c3e3efb8118`。

## 回滚

旧 release `/opt/flatnotes/releases/01946e76e28ddf61feae3df9bdb4c87a1e9b3ef4` 与 previous-release 已核对存在，未演练生产回滚。仅针对本次样式升级：

```sh
sudo systemctl stop flatnotes.service
sudo ln -sfn /opt/flatnotes/releases/01946e76e28ddf61feae3df9bdb4c87a1e9b3ef4 /opt/flatnotes/current.stage
sudo mv -fT /opt/flatnotes/current.stage /opt/flatnotes/current
sudo systemctl start flatnotes.service
printf '%s\n' 01946e76e28ddf61feae3df9bdb4c87a1e9b3ef4 | sudo tee /opt/flatnotes/current-commit >/dev/null
```

不回滚网站/身份，不覆盖共享数据。本次 deploy.sh 与旧版本相同，升级失败自动切回旧 symlink/service。

## 验证边界与临时资产

历史功能验收见上一轮生产报告，未重跑未改动的 OIDC 协议测试。本次用户视觉审核尚未确认；真实主机重启/缺盘、VLESS + Reality 客户端、自动备份及至少两个真实应用 SSO 仍待后续。npm audit 的既有 8 项公告未扩大处理。

本地截图及 work/tests 保护原始快照忽略 Git，待人工复核后可删除。开发依赖/构建和既有 fixture 为单份本地资产；未知 test-data 不动。VPS notes-style-stage 本轮唯一部署脚本及空目录已精确删除；保留正式 release 和回滚版本，不 broad prune。

本轮收尾：本地 UI fixture 已停止，本轮命名诊断/记录辅助脚本与失败 debug-read.png 已删除；保护原始快照和复核截图保留。旧 fixture/未知数据未删除。正式 headed Chromium 测试窗口仍等待用户手动登录，当前不能宣称线上成员页面验收通过。
