# 六项前端整改发布与验收边界

六项前端代码已实施并发布。用户视觉审核仍未确认；自动检查不等于视觉验收通过。

## 固定发布

- Flatnotes source：`18a0c01c9e50a828d0b5c3b9ad92e7adfda47de8`，已推送 `Forlooong/flatnotes` 的 `vps-flatnotes-oidc`，VPS 从 GitHub fetch 后按该完整 SHA 执行版本内 `deploy.sh`。
- 网站最终 source：`c9209559f34e4475f4d9bd7fc7682af78bbc01ab`（首轮为 `08b8deecb2ebbcf6baeb1a83896afbc50b1463a1`，随后按用户要求移除已部署应用辅助文字），已推送 `Forlooong/vps-site` 的 `main`，使用 `scripts/deploy.ps1 -Commit <完整SHA>`。
- 网站最终 release：`/opt/deploy/vps-site-releases/20260928T053951Z-c9209559f34e.HLyndt`，不可变资源包 `1a3401c6706106f3`。
- Notes release：`/opt/flatnotes/releases/18a0c01c9e50a828d0b5c3b9ad92e7adfda47de8`。
- 身份 source 保持 `c680822408814f2bb03d013431d46fc6488a2ea6`；未部署或重启身份服务，启动时间仍为 `2026-09-28T03:26:38.383255554Z`，restart=0。

## 本次验证

- 本地构建通过；生产使用未改动的锁文件和固定基础镜像 digest 构建，通过 compileall、ready JSON、release SHA256SUMS。保留既有大 chunk 提示，未升级依赖。
- 本地真实 Chromium 1280/1440/1920/390/320（移动尺寸包含设备与触控模拟）通过居中/导航对齐、不横向溢出、品牌/图标、favicon 字节及 SVG MIME、标签、中文校验及弹窗、新建/保存/深层刷新/再次编辑/删除、草稿恢复、Markdown/富文本/预览、图片上传/取回、浅暗主题及光标/复制断言。详见 `local/local-checks.json`。
- 网站桌面/移动、应用目录刷新、纪念日和折叠交互通过。模拟服务端 state 与授权响应验证匿名鼠标/键盘禁用、已授权只开放 Notes、无权限、过期响应、状态失败、BFCache 返回；这是前端状态集成测试，不是本轮重新验证真实 Authelia 自然过期。
- 网站线上 14 个发布文件 HTTP 字节与 manifest 一致；匿名路由边界通过。网站 favicon 位于内容指纹目录，Notes favicon 为 Vite 指纹资源；深层路由依赖既有服务端 base href，未改变 OIDC 自动回跳。
- Notes active/healthy、1000:1000、restart=no；data UUID `6cb900e1-697a-4305-884c-cfd1620f5adf`，release 清单验证通过。
- 保护前后：3x-ui/OpenResty 容器启动时间/重启数/挂载、443、证书/stream/main/vhost hash 不变；规范化 inbounds/settings/firewall 不变。数据库流量计数不作为配置变化。网站仅因 auth-theme 同内容资源的新 bundle 路径执行 `nginx -t` 和 reload；未改代理 vhost/stream 或重启代理。证据在 `D:/DEV/Lab/vps-site/docs/evidence/2026-09-28/ui-revision/`。

## 测试中发现的问题与限制

- 已修正旧 CSS 强制编辑器高度导致预览挡住底部模式切换的问题；通过实际点击富文本/Markdown 验证。
- 发现上游 CSS 的英文 Scroll 未包含在 locale 中，已单独中文化；移动展开工具栏约束为容器内换行。
- 扩大验证时出现过一次 removeChild DOM 异常；开启调用栈捕获后的完整五尺寸与局部复测均未复现，未确定原因，不宣称此间歇异常已修复。
- 首次正式账户验证登录后等待首页 networkidle 超时退出，未生成通过报告；第二次在图标加载完成前断言中止；改为等待实际控件与图片就绪，并在异常时保留浏览器以便续测。最终正式账户五尺寸及深层回跳/编辑/草稿/附件/返回/刷新/前进后退/退出通过，报告 `production/production-checks.json`，pageErrors=[]。没有记录真实凭据、Cookie、token 或 storage state。
- 本轮没有等待生产 30m 空闲/8h 绝对自然过期。协议和服务端期限未改，不借用历史结果宣称本轮重测通过。

## 回滚

Notes 的 `previous-release` 已核对指向 `76dd37d075f0cb120d0677969f793fad3108594d`。仅停止 Notes、切换 current、重新启动 Notes，保留共享数据：

```sh
sudo systemctl stop flatnotes.service
sudo ln -sfn /opt/flatnotes/releases/76dd37d075f0cb120d0677969f793fad3108594d /opt/flatnotes/current.stage
sudo mv -fT /opt/flatnotes/current.stage /opt/flatnotes/current
sudo systemctl start flatnotes.service
printf '%s\n' 76dd37d075f0cb120d0677969f793fad3108594d | sudo tee /opt/flatnotes/current-commit >/dev/null
```

网站使用该固定网站版本的 `server/rollback-home.sh /opt/deploy/vps-site-releases/20260928T053244Z-08b8deecb2eb.9geARr` 恢复保存的 HTML/静态 include。旧资源包与 release 已保留。回滚路径已检查，未在生产演练。身份服务及账户文件不随本次回滚。

## 人工审核与临时资产

用户视觉审核：待新版本确认，未通过。

截图与保护原始快照只保留本地，不进 Git，可在视觉复核后删除；正式 release、回滚包和原 UI 参考保留。本轮正式测试笔记通过 UI 删除，精确测试图片“正式界面验证-198fa7a8.png”已删除。本地五个测试图片及中间诊断截图/辅助脚本已清理，保留未知 fixture 数据。本轮预览/fixture/浏览器已停止。网站最终文本版本另行通过匿名桌面/移动和全部14个HTTP资源清单核对；成员锁逻辑没有因文字精简而变化。

最新网站 release 的 previous-index/previous-routes 仅回退辅助文字变更；上面列出的首轮网站 release 回退整个本轮网站整改。保护最终快照比较将 Docker mounts 按 Destination 排序（原始数组顺序不同、各挂载内容相同）；规范化配置/防火墙和其余保护项目不变。
