"""Real Chromium UI checks against isolated fixture or authenticated release."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

OUT = Path("docs/evidence/2026-09-28")
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    results = []
    for width, height in ((1440, 1000), (390, 844)):
        context = browser.new_context(viewport={"width": width, "height": height}, locale="zh-CN")
        context.add_cookies([{"name": "flatnotes_session", "value": "fixture-session", "domain": "127.0.0.1", "path": "/apps/notes/"}, {"name": "site_session", "value": "fixture-site", "domain": "127.0.0.1", "path": "/"}])
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:18081/apps/notes/", wait_until="networkidle")
        expect(page.get_by_text("Flatnotes", exact=True)).to_be_visible()
        expect(page.get_by_role("link", name="欢迎使用", exact=True)).to_be_visible()
        assert page.get_by_role("menuitem", name="搜索笔记").count() == 0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(OUT / f"local-home-{width}.png"))
        page.get_by_role("button", name="菜单", exact=True).click()
        expect(page.get_by_role("menuitem", name="全部笔记")).to_be_visible()
        page.screenshot(path=str(OUT / f"local-menu-{width}.png"))
        page.get_by_role("menuitem", name="切换主题").click()
        assert page.locator("body").evaluate("el => el.classList.contains('dark')")
        page.get_by_role("button", name="菜单", exact=True).click()
        page.get_by_role("menuitem", name="全部笔记").click()
        expect(page.get_by_role("link", name="欢迎使用", exact=False).first).to_be_visible()
        page.goto("http://127.0.0.1:18081/apps/notes/note/" + "欢迎使用", wait_until="networkidle")
        page.reload(wait_until="networkidle")
        expect(page.locator(".toast-viewer")).to_contain_text("共享笔记测试")
        page.get_by_role("link", name="新建笔记").click()
        expect(page.get_by_placeholder("笔记标题")).to_be_visible()
        expect(page.locator(".toastui-editor-defaultUI")).to_be_visible()
        assert not errors, errors
        results.append({"viewport": width, "home_menu_search_theme_editor_deep_refresh": "passed", "provider": "isolated fixture, not production OIDC"})
        context.close()
    browser.close()
    (OUT / "local-ui.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False))
