"""Targeted production UI check. Credentials and cookies stay in memory."""
import json
import time
import uuid
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import expect, sync_playwright

SITE = "https://www.040323.xyz"
APP = SITE + "/apps/notes"
OUT = Path("docs/evidence/2026-09-28/style-unification")
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--window-size=1440,1000"])
    login = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = login.new_page()
    page.goto(APP + "/new?style=homepage", wait_until="networkidle")
    print("READY: 请在 Chromium 网站页面手动登录任一正式成员账户。", flush=True)
    deadline = time.monotonic() + 900
    while not page.url.startswith(APP + "/new") and time.monotonic() < deadline:
        page.wait_for_timeout(1000)
    if not page.url.startswith(APP + "/new"):
        browser.close()
        raise SystemExit("正式浏览器登录尚未完成；没有保存凭据。")
    assert page.url == APP + "/new?style=homepage"
    assert login.request.get(APP + "/api/auth-check").status == 200
    print("SIGNED IN: 开始正式页面样式验收。", flush=True)
    cookies = login.cookies()  # Never written to disk or logs.
    results = []
    for width, height in [(1440, 1000), (390, 844), (320, 760)]:
        context = browser.new_context(viewport={"width": width, "height": height}, locale="zh-CN", is_mobile=width<760, has_touch=width<760)
        context.add_cookies(cookies)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(SITE + "/", wait_until="networkidle")
        expected = page.locator("body").evaluate("e=>[getComputedStyle(e).backgroundColor,getComputedStyle(e).color,getComputedStyle(e).fontFamily]")
        left = page.locator("#inner_wrapper").evaluate("e=>e.getBoundingClientRect().left+parseFloat(getComputedStyle(e).paddingLeft)")
        page.goto(APP + "/", wait_until="networkidle")
        actual = page.locator("body").evaluate("e=>[getComputedStyle(e).backgroundColor,getComputedStyle(e).color,getComputedStyle(e).fontFamily]")
        assert actual == expected
        assert abs(left-page.locator(".notes-shell").evaluate("e=>e.getBoundingClientRect().left+parseFloat(getComputedStyle(e).paddingLeft)")) < 1
        if width != 320:
            page.bring_to_front(); page.screenshot(path=str(OUT/f"production-home-{width}.png"))
        page.get_by_role("button", name="菜单", exact=True).click()
        expect(page.get_by_role("menuitem", name="搜索笔记")).to_be_visible()
        page.get_by_role("menuitem", name="全部笔记").click()
        page.wait_for_url("**/search?*")
        page.get_by_role("link", name="新建笔记").click()
        title = "样式验收-" + uuid.uuid4().hex[:8]
        created = False
        try:
            page.get_by_placeholder("Title").fill(title)
            page.locator(".toastui-editor.md-mode .ProseMirror").click()
            page.keyboard.type("网站统一样式验证 #shared")
            if width != 320:
                page.screenshot(path=str(OUT/f"production-editor-{width}.png"))
            with page.expect_response(lambda r:r.request.method=="POST" and r.url==APP+"/api/notes") as saved:
                page.get_by_role("button", name="Save", exact=True).click()
            assert saved.value.status == 200
            created = True
            page.get_by_role("button", name="Edit", exact=True).click()
            expect(page.locator(".toast-viewer")).to_contain_text("网站统一样式验证")
            page.reload(wait_until="networkidle")
            expect(page.locator(".toast-viewer")).to_contain_text("网站统一样式验证")
            page.get_by_role("button", name="菜单", exact=True).click()
            page.get_by_role("menuitem", name="切换主题").click()
            assert page.locator("body").evaluate("e=>e.classList.contains('dark')")
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            assert not errors
            results.append({"viewport":width,"homepage_tokens_alignment":"matched","menu_all_notes_editor_save_read_refresh_theme":"passed","pageErrors":[],"overflow":False})
        finally:
            if created:
                assert context.request.delete(APP+"/api/notes/"+quote(title), headers={"Origin":SITE}).status==200
            context.close()
    browser.close()
    (OUT/"production-checks.json").write_text(json.dumps({"environment":"production; user manually logged in; no credentials persisted","results":results},ensure_ascii=False,indent=2),encoding="utf-8")
    print("PASS: 正式 1440/390/320 样式与操作检查通过，测试笔记已精确删除。", flush=True)
