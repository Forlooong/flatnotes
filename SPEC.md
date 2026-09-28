# Flatnotes Shared Notes 规范

状态：首应用与六项前端整改已发布；实际实现/验证状态见 README，用户视觉审核单独记录。

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
- 桌面/移动真实浏览器检查与用户视觉审核分别记录。六项完整规范见 `D:/DEV/Lab/project-docs/docs/plans/flatnotes-ui-revision.md`；实现与验证状态见 README。

## 发布验收

必须验证 `/apps/notes/`、深层笔记刷新、静态资源、API、附件、匿名回跳、OIDC state/nonce/PKCE、cookie Path、退出、过期、两个账号共享同一笔记、并发编辑的最后写入行为和 18080 回环旁路拒绝。未通过前 `deployed=false`。

## 附件生命周期与返回入口（2026-09-28 用户补充）

- 内容相同的重复上传复用附件；文件仍放在共享目录 attachments/，不拆用户目录。
- 正式笔记、保留的浏览器草稿和上传待插入状态均保护附件；保存、离开编辑、删除笔记、明确丢弃草稿时清理无引用的受管附件。
- 用户已选择：离开保留草稿引用，只有丢弃草稿后才释放引用；不得以任意短期限清掉仍保留的草稿附件。
- 草稿正文保存在浏览器，服务端只存附件名和引用状态；所有笔记写入、上传与清理共享单进程锁，扫描失败不删除附件。
- 兼容旧 API 未带 draftId 的上传和历史文件：不凭文件年龄自动删除未纳入管理的附件；需单独盘点。实施前生产笔记/附件均为 0。
- 统一返回首页按钮独立固定右下角，参照 `D:/DEV/Lab/project-docs/docs/spec/application-return-home.md`；不放回顶部导航，不改变认证。
