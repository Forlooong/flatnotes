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

## 2026-09-28 — Notes 样式与网站首页统一（发布候选）

用户反馈：上一版前端审核不通过，要求与网站首页风格统一；历史功能通过不代表视觉审核通过。
目标与范围：以网站首页 bundle 05b633c8a337153b 为实际基线，仅调整 Flatnotes 前端字体、灰绿配色、三角标、统一导航、留白、细线列表、搜索/弹层及阅读/编辑器样式；认证、共享目录、接口、部署架构、依赖不变。
关键文件：client/style.css、App.vue、NavBar.vue、Home.vue、SearchResults.vue、Note.vue、SearchInput.vue、SearchModal.vue、CustomButton.vue、PrimeMenu.vue、Modal.vue、toastui-editor-overrides.scss、tailwind.config.js；tests/check_style.py、ui_fixture.py、SPEC.md。部分已有 CRLF/Mixed 文件在改动时统一 LF，无业务逻辑变化。
设计：浅色 #f5f7f6/#253c36/#64736d/#d8e0dc、网站 Aptos/Segoe UI/PingFang SC/Microsoft YaHei 字体；1280px shell 与 64/26/20px 边距；菜单展开条目不变，保留编辑器和主题，上游编辑操作仍部分英文。
验证：最终 npm build 通过；Playwright 真实 Chromium 1440x1000、390x844、320x760（移动模式+触控）逐项比较线上首页计算颜色/字体/内容左边距一致，菜单展开/搜索/阅读刷新/浅暗主题及编辑器/真实 POST 新建保存/PATCH 再编辑/精确删除本轮数据通过，无溢出与页面异常。检查结果 style-unification/checks.json，截图实际查看。未重跑未改动的 OIDC 认证密码学或双账户协议测试，不用历史结果冒充本轮 UI 验证。
测试问题：先前本地自建 fixture 欢迎使用.md 为 GBK，本次 UTF-8 进程读取失败，修正该测试数据；Save 保持编辑态是上游行为，测试显式退出编辑再读并真正修改内容后检查 PATCH。fixture 写请求仅测试 Origin localhost18081，不影响正式 server 配置。
状态：本地验证通过，候选尚未生产发布；用户视觉审核尚未收到，不能宣称审核通过。保持旧生产 01946e76e28ddf61feae3df9bdb4c87a1e9b3ef4 作为回滚点，发布记录另追加。
临时资产：截图 style-unification/*.png、work/tests/inspect-style-*.py、normalize-ui-lines.py、保护快照、fixture 数据及 dist 忽略 Git；截图待复核可删除，未知既有 test-data 不动。临时进程将在发布/审查收尾停止。
Git：本记录随样式候选提交，完整 commit 在后续部署记录标注。

HASH: 3c30109d7c500ad6f4358714c0cb2947e5edbb17050973a1990dcf16ba4b0cf4

## 2026-09-28 — Notes 统一样式实际发布与审核边界

目标：修正用户判定未通过的前端，与网站首页现有风格统一；不重复询问上游/OIDC/共享/路径等已确认选择。
实际变更：样式与最小前端组件修改 source 76dd37d075f0cb120d0677969f793fad3108594d，GitHub vps-flatnotes-oidc 推送后 VPS 精确 fetch/archive/build/deploy.sh 发布；网站和身份运行版本未变，未改认证、数据分区、依赖和部署架构。
验证：本轮最终 build、1440/390/320 Chromium 移动触控的首页计算样式/菜单/搜索/阅读深层刷新/浅暗主题与编辑器/POST 新建/PATCH 编辑通过，无溢出及 pageerror。正式 source/清单/health JSON/active/healthy/1000:1000/256MiB/0.5CPU/restart=no/data UUID 核对；匿名 API/CSS 401，HTML 深层 302；CSS 资源 SHA 已记录。没有放宽匿名资源边界。公开请求最初预期 CSS200/不带HTML Accept 跳转，已按实际协议纠正测试预期，而非修改应用鉴权。
发布：2026-09-28T04:11:39Z，/opt/flatnotes/releases/76dd37d075f0cb120d0677969f793fad3108594d，previous-release 01946e76e28ddf61feae3df9bdb4c87a1e9b3ef4 保留，回滚操作见 style-unification/release.md；未生产回滚演练。
保护：04:09:16Z/04:12:58Z 对比，3xui_app/OpenResty 启动时间、restarts=0、mounts、证书/stream/main/vhost/主页以及规范化 inbounds/settings/iptables/ip6tables 不变。仅更新 Notes，无其他服务改动或重启。
审核边界：旧前端用户审核不通过是事实；本次视觉审核尚未收到。正式单成员 UI 浏览器窗口已按既有手动登录授权打开，仍等待用户登录；该流程未完成，不能引用首轮双账户功能报告替代本轮样式生产浏览器结果。OIDC 代码未改动，未重复未改动协议测试。详见 style-unification/checks.json/public-checks.json/protected-comparison.json/release.md/production-pending.json。
清理：本轮自建 UI 测试笔记精确删除、本地 fixture 停止、命名诊断/记录脚本和失败调试截图清理成功；VPS 唯一临时部署脚本与空目录清理成功。原始保护快照/桌面移动截图待复核保留、忽略Git；旧 fixture 和未知 test-data 保留，未绕过前轮被拒绝的递归删除。node_modules/.venv/dist 单份开发资产不提交。当前唯一运行的测试为等待手动登录的 Chromium，测试仅存内存 Cookie，不保存凭据。
遗留：用户新版视觉审核、正式样式浏览器手动登录；既有依赖公告/备份/真实重启缺盘/代理客户端/多应用SSO不扩大处理。README 只更新当前实际 source 与验证边界；SPEC 加入用户要求的网站样式一致约束。
Git：生产 source 76dd37d075f0cb120d0677969f793fad3108594d。本轮随后仅提交测试/证据/文档收尾，生产固定源码不随文档提交变化。

HASH: 49e9a4764dcb5bbd7a00d63d7b71f5a7ef182ed3f0bc0defbea4c5c18ae96170

## 2026-09-28T13:05:09+08:00 — 六项前端整改需求与新会话文档交接

本轮目标：按用户要求，仅将六项反馈规范化并同步项目记忆，下一会话再实施；不修改页面/代码/资源/配置，不执行 commit/push/生产部署或新功能测试。
用户反馈：当前桌面布局与居中较差；左上角品牌要 Flatnotes、图标用首页应用图标；网站 favicon 与应用标签图标/名称需改；新建页布局和中文需改；首页未登录显示锁且不可进入、登录后才可点击；应用普通展示区不能出现输入光标。六项均待实施，视觉验收未通过，不再仅记“等待用户反馈”。
修改范围与关键文件：README.md、SPEC.md、LOG.MD、LOG-INDEX.MD。规范与验收主文档 D:/DEV/Lab/project-docs/docs/plans/flatnotes-ui-revision.md；完整执行提示词 docs/prompts/flatnotes-ui-revision-prompt.md。既有文档入口指向新版本，避免旧品牌/旧生产SHA/失效进程信息误导下一会话。
规范决定：品牌 Flatnotes 替代旧“共享笔记”品牌要求，共享数据与菜单功能不变；notes.svg 为应用图标基线。网站 favicon 默认复用现有网站品牌，这是实施默认解释，不是用户另指定新图标。布局居中指主内容而非全体文本居中。输入光标按首页区分普通展示区域和真实输入区域，后者保留正常编辑/选中/光标。登录解锁只开放已部署且获授权应用，其他七项仍未部署不可点击；直接深层 URL 的 OIDC 自动回跳与服务端授权不变。
为什么修改：自动测试曾通过，但用户指出实际视觉和交互仍有问题；正式当前文档必须明确待整改，并把新确认的设计约束与已经验证的历史功能分开。
只读恢复：本轮开始 Flatnotes HEAD 3bcfbdb3ef82f400930b649de1be750a82742b98/vps-flatnotes-oidc，vps-site HEAD 56f7a7650a2524dea128cdc9f6aa14e501994ec2/main，两仓库干净；当前只留下本轮文档未提交修改，HEAD 不变。最后记录生产网站 718a5d77d6c5f530c145e7da5fb758b494f16c8a、身份 c680822408814f2bb03d013431d46fc6488a2ea6、Notes 76dd37d075f0cb120d0677969f793fad3108594d，回滚 01946e76e28ddf61feae3df9bdb4c87a1e9b3ef4。本轮未连接 VPS 复核，生产版本来源是历史发布证据，下一轮发布前需再只读检查。
验证与结果：读取三项目 AGENTS/README/SPEC/索引并按上轮 HASH 定位 LOG；核对本地 Git、实际首页 notes.svg 参考与首页光标规则。旧 check_style_production.py 进程已不在运行、style-unification/production-checks.json 不存在；旧 session 读取返回 Unknown process id，不能认作线上样式验收通过，结束原因未核实。文档检查核对六项、路径、状态及LOG索引；不执行构建或业务浏览器测试，不引用旧通过结果替代新验证。
风险与遗留：六项代码全部尚未实现，视觉验收未通过；正式成员样式浏览器流程尚未完成，旧 PID/会话不可依赖。下一轮针对修改做桌面/移动实际流程和用户视觉审核，沿已授权固定commit发布链路保留回滚/保护证据。认证/OIDC、共享目录、身份期限、3x-ui/Xray等保护资源不变，其他遗留不扩大处理。
Git：本轮仅文档修改，未 commit/push；上列 HEAD 为本轮起点，不是新部署。没有创建测试脚本/产物，没有删除未知文件或改写历史 LOG。LOG 只追加，LOG-INDEX 只保存索引。

HASH: c4664e75c313c0a51228c360de8271c13ee0afb9aea964de12cf0ed60559542e

## 2026-09-28 六项前端整改候选与本地浏览器验证

时间：2026-09-28T05:31:56.972083+00:00；本轮目标仅为已确认的六项前端整改，保留上一轮未提交交接文档。
修改：Flatnotes 960px 居中内容与导航、首页居中引导与搜索；首页 notes.svg 品牌/带构建指纹 favicon/Flatnotes 标签；中文新建编辑、上游 zh-CN locale、标题与操作排列、桌面双栏/移动标签预览、可用的模式切换与附件；普通展示 cursor:default，输入/编辑保留 caret 与选择。网站默认禁用卡片，读取真实 state 与现有 /member/ 同组授权后只开放 Notes，回到首页/聚焦/可见性/30秒复核和点击前重新校验；新增三角 favicon 与不可变资源包 fa29a828efbcfc5a。
关键文件：flatnotes/client/{style.css,index.html,router.js,api.js,views/Note.vue,partials/NavBar.vue,partials/SearchInput.vue,components/toastui/*,components/ConfirmModal.vue,components/LoadingIndicator.vue,assets/notes.svg}；vps-site/public/index.html、public/assets/homepage/fa29a828efbcfc5a/、server/homepage-routes.conf；专项 tests/check_revision.py 与旧测试选择器。未改认证协议、身份配置、依赖锁或数据规范。
决定与原因：沿用灰绿主题和既有图标；主区域等距留白而非正文居中。旧 CSS 强制高度使编辑器预览遮挡底部模式切换，改用编辑器 height/setHeight 并响应窗口变化。上游 CSS 的 Scroll 单独中文化；移动展开工具栏约束在容器内。favicon 指纹避免旧缓存，网站路由只更新同内容 auth-theme 资源包路径，不重启身份服务。
验证：npm run build 通过（保留既有大 chunk 提示）；真实 Chromium 1280/1440/1920/390/320，后两者启用移动设备与触控模拟，创建、中文校验、保存、深层刷新、编辑、删除、草稿恢复、Markdown/富文本/预览、图片上传/取回、浅暗主题、图标 MIME/字节/标签、居中/不横向溢出、光标/复制通过。网站独立桌面移动、资源/目录刷新/纪念日/折叠通过。mock 网站会话响应验证未登录/无权限/失效/错误/BFCache，不能声称真实 provider 自然过期已重测。结果 flatnotes/docs/evidence/2026-09-28/ui-revision/local/local-checks.json 和 vps-site/docs/evidence/2026-09-28/ui-revision/local-checks.json。
诊断边界：扩大模式切换验证时一次出现 removeChild DOM 异常，增加调用栈捕获后完整五尺寸与1280/390局部复测未再复现，未确认根因，不宣称已修复该间歇异常。最初 Playwright 因 aria-disabled 拒绝点击属于测试驱动条件，改成真实强制鼠标点击验证禁用；重复诊断上传同名附件时服务端自动重命名，测试改以返回文件名断言。
生产只读：网站 718a5d77d6c5f530c145e7da5fb758b494f16c8a、Notes 76dd37d075f0cb120d0677969f793fad3108594d、身份 c680822408814f2bb03d013431d46fc6488a2ea6；/data UUID 正确。保护原始快照留本地 vps-site/work/tests/ui-revision，未改保护资源。身份 started=2026-09-28T03:26:38.383255554Z/restarts=0。
风险与遗留：本条为发布前候选，正式账户流程与生产部署在后续记录；用户视觉审核未通过/待新版本确认。真实自然过期、代理客户端、整机重启等不借旧测试声明完成。临时截图/隔离fixture/测试图片位于忽略目录，最终清理另记。
Git：本条随本轮源码固定 commit 提交，SHA 在后续发布记录；project-docs 非 Git 仓库。

HASH: 810eba0f45eef55bd3c290e160e9feff0a126a299e05d31cf490ecdbfb26a345
