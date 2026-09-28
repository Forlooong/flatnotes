# Flatnotes Shared Notes 规范

状态：首应用已发布；用户提出新的六项前端整改，视觉验收未通过，整改尚未实施。历史功能验证与当前视觉状态分别记录，见 README。

## 上游与路径

- 上游：`https://github.com/dullage/flatnotes`
- 上游版本：`5.5.5`
- 上游 commit：`7f5b773c9cb37cc84978079ed4790e7de38d3970`
- 服务 slug：`notes`
- 正式路径：`/apps/notes/`
- 禁止新增子域名和旧根路径入口。

## 认证边界

- `FLATNOTES_AUTH_TYPE=oidc`。
- issuer：`https://www.040323.xyz/auth`。
- client：`flatnotes`，Authelia 中为 public client，强制 `S256` PKCE。
- redirect URI：`https://www.040323.xyz/apps/notes/api/oidc/callback`。
- 只接受 HTTPS discovery、RS256 ID Token、精确 issuer、audience、nonce、`sub`、`iat` 和 `exp`。
- state 存在单实例内存并绑定 HttpOnly、Secure、SameSite=Lax 的短期 Cookie；应用会话是路径为 `/apps/notes/` 的 HttpOnly、Secure、SameSite=Lax Cookie。
- 未登录访问自动跳转 Authelia；Flatnotes 原生本地用户名密码接口和页面不启用。
- 退出先销毁应用会话，再跳转本站 Authelia logout；会话过期后 API 返回 401。
- 每次请求复核当前网站 Cookie 经回环 Authelia authz 得到的 `site-users` 成员和用户名；应用会话绑定网站 Cookie 指纹。网站退出、过期、身份切换后拒绝访问，无验证缓存；认证服务不可用时拒绝访问。
- 使用 UserInfo 的 `sub` 与已验签 ID Token 的 `sub` 绑定，再关联网站会话用户名。Cookie 写请求必须具有精确应用 Origin，应用退出为 POST；OIDC token 端点使用标准 code+PKCE 交换，无浏览器 Cookie，不放宽其他身份写请求规则。

## 共享数据

- 宿主机唯一 canonical 目录：`/data/apps/notes/shared/`。
- 容器路径：`/data`；运行 UID/GID：`1000:1000`。
- 笔记、`.flatnotes` Whoosh 索引和附件共享读写。
- 网站账户只决定是否通过统一身份认证，不参与对象级数据分区；因此两个账户拥有相同的业务数据权限。
- 当前无旧 Flatnotes 生产数据迁移。
- systemd `RequiresMountsFor=/data`、`BindsTo=data.mount` 和启动前 UUID 校验；Docker 自启动关闭，bind 不自动创建缺盘目录。实际整机重启/缺盘仍留维护窗口，不中断代理。

## 界面

- 应用左上角品牌显示 `Flatnotes`，使用网站首页 Flatnotes 对应的应用图标；替代“共享笔记”作为品牌名称的旧要求，共享编辑说明、中文搜索占位符和“最近修改”列表保留。
- “搜索笔记”“全部笔记”“切换主题”“退出登录”放在“菜单”弹出项中；“新建笔记”保留为主按钮。
- Flatnotes 编辑器、搜索结果、标签和主题能力继续使用上游功能。
- 与网站首页保持配色、字体和整体风格一致；首页、搜索、阅读和编辑器采用协调的主内容居中布局、合理宽度与留白，兼容大屏和移动端。不能仅以计算颜色/字体匹配认定视觉适配完成。
- Flatnotes 浏览器 favicon 使用对应应用图标，标签标题显示 Flatnotes，覆盖首页及各深层路由。
- 新建/编辑页调整标题、操作、工具栏、编辑/预览区域布局；用户可见控件、工具提示、弹窗、校验和反馈中文化，保留上游既有编辑/草稿/附件能力。
- 普通展示区域不出现 I 形输入指针或错误插入光标；实际搜索框、标题和编辑器保留输入、选中与光标，不全局禁止正文复制或键盘焦点提示。
- 桌面/移动真实浏览器检查与用户视觉审核分别记录。六项完整规范见 `D:/DEV/Lab/project-docs/docs/plans/flatnotes-ui-revision.md`；本次仅更新目标，未修改实现。

## 发布验收

必须验证 `/apps/notes/`、深层笔记刷新、静态资源、API、附件、匿名回跳、OIDC state/nonce/PKCE、cookie Path、退出、过期、两个账号共享同一笔记、并发编辑的最后写入行为和 18080 回环旁路拒绝。未通过前 `deployed=false`。
