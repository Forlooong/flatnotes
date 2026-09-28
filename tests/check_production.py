"""Headed two-account acceptance. User enters real credentials in the website.

No passwords, tokens, cookies, auth URLs or private storage states are saved.
"""
import json
import time
import uuid
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright, expect

BASE = "https://www.040323.xyz"
APP = BASE + "/apps/notes"
OUT = Path("docs/evidence/2026-09-28")
OUT.mkdir(parents=True, exist_ok=True)
title = "接入验证-" + uuid.uuid4().hex[:12]
created = False
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    contexts = []
    pages = []
    for user, width, height in (("zhuqing", 1440, 1000), ("yaojia", 390, 844)):
        context = browser.new_context(viewport={"width": width, "height": height}, locale="zh-CN", is_mobile=width == 390, has_touch=width == 390)
        page = context.new_page()
        page.goto(APP + "/new?acceptance=" + user, wait_until="networkidle")
        contexts.append(context)
        pages.append(page)
    print("READY: 两个测试窗口已打开；分别登录 zhuqing（桌面）和 yaojia（移动），首次 OIDC 授权按页面确认。", flush=True)
    deadline = time.monotonic() + 900
    pending = set(range(2))
    while pending and time.monotonic() < deadline:
        for index in list(pending):
            if pages[index].url.startswith(APP + "/new"):
                response = contexts[index].request.get(BASE + "/auth/api/state")
                user = response.json().get("data", {}).get("username")
                if user == ("zhuqing", "yaojia")[index]:
                    pending.remove(index)
                    print("SIGNED IN:", user, flush=True)
        if pending:
            pages[0].wait_for_timeout(1000)
    if pending:
        raise SystemExit("Real-account login remains incomplete; no credentials were requested or persisted.")
    print("TESTING: 已获得两个正式网站会话，开始真实验收。", flush=True)
    errors = []
    for page in pages:
        page.on("pageerror", lambda error: errors.append(str(error)))
    a, b = contexts
    try:
        # First login preserves the exact original route and query.
        assert pages[0].url == APP + "/new?acceptance=zhuqing"
        assert pages[1].url == APP + "/new?acceptance=yaojia"
        for context in contexts:
            for name, path in (("site_session", "/"), ("flatnotes_session", "/apps/notes/")):
                cookie = next(c for c in context.cookies() if c["name"] == name)
                assert cookie["secure"] and cookie["httpOnly"] and cookie["sameSite"] == "Lax" and cookie["path"] == path
            assert context.request.get(APP + "/api/auth-check").status == 200
        # Create and save with the actual upstream editor UI.
        page = pages[0]
        page.get_by_placeholder("Title").fill(title)
        editor = page.locator(".toastui-editor.md-mode .ProseMirror")
        editor.click()
        page.keyboard.type("共享笔记真实验收 #shared")
        with page.expect_response(lambda r: r.request.method == "POST" and r.url == APP + "/api/notes"):
            page.get_by_role("button", name="Save", exact=True).click()
        expect(page).to_have_url(APP + "/note/" + quote(title))
        created = True
        note_url = APP + "/note/" + quote(title)
        api_url = APP + "/api/notes/" + quote(title)
        for page in pages:
            page.goto(note_url, wait_until="networkidle")
            page.reload(wait_until="networkidle")
            expect(page.locator(".toast-viewer")).to_contain_text("共享笔记真实验收")
        page = pages[1]
        page.get_by_role("button", name="Edit", exact=True).click()
        editor = page.locator(".toastui-editor.md-mode .ProseMirror")
        editor.click()
        page.keyboard.press("ControlOrMeta+A")
        page.keyboard.type("第二位成员共享编辑 #shared")
        with page.expect_response(lambda r: r.request.method == "PATCH" and r.url == api_url):
            page.get_by_role("button", name="Save", exact=True).click()
        assert a.request.get(api_url).json()["content"].startswith("第二位成员共享编辑")
        uploaded = a.request.post(APP + "/api/attachments", headers={"Origin": BASE}, multipart={"file": {"name": title + ".txt", "mimeType": "text/plain", "buffer": b"acceptance attachment"}})
        assert uploaded.status == 200
        attachment = APP + "/" + uploaded.json()["url"]
        assert b.request.get(attachment).body() == b"acceptance attachment"
        # Empty, foreign and near-match origins cannot mutate cookie sessions.
        for origin in ("", "https://evil.example", BASE + "/"):
            assert a.request.patch(api_url, headers={"Origin": origin}, data={"newContent": "csrf"}).status == 403
            assert a.request.post(BASE + "/auth/api/logout", headers={"Origin": origin}).status == 403
        results = []
        for page, width in zip(pages, (1440, 390)):
            page.goto(APP + "/", wait_until="networkidle")
            expect(page.get_by_text("共享笔记", exact=True)).to_be_visible()
            assert page.get_by_role("menuitem", name="全部笔记").count() == 0
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(OUT / f"production-home-{width}.png"))
            page.get_by_role("button", name="菜单", exact=True).click()
            expect(page.get_by_role("menuitem", name="搜索笔记")).to_be_visible()
            page.screenshot(path=str(OUT / f"production-menu-{width}.png"))
            page.get_by_role("menuitem", name="切换主题").click()
            assert page.locator("body").evaluate("el => el.classList.contains('dark')")
            page.get_by_role("button", name="菜单", exact=True).click()
            page.get_by_role("menuitem", name="全部笔记").click()
            expect(page.get_by_role("link", name=title, exact=False).first).to_be_visible()
            results.append({"viewport": width, "shared_ui_menu_search_theme_editor_refresh": "passed"})
        # Replay the original website and app cookies after native website logout.
        # They stay in memory only; this establishes backend invalidation.
        original = "; ".join(c["name"] + "=" + c["value"] for c in a.cookies() if c["name"] in ("site_session", "flatnotes_session"))
        pages[0].goto(BASE + "/auth/settings/security", wait_until="networkidle")
        pages[0].locator("#site-account-logout").click()
        pages[0].wait_for_url(lambda url: "/auth" in str(url) and "settings" not in str(url), timeout=30000)
        assert a.request.get(api_url, headers={"Cookie": original}).status == 401
        assert a.request.get(attachment, headers={"Cookie": original}).status == 401
        assert b.request.get(api_url).status == 200
        # App logout invalidates the app session and uses the standard website UI.
        pages[1].goto(APP + "/", wait_until="networkidle")
        pages[1].get_by_role("button", name="菜单", exact=True).click()
        with pages[1].expect_response(lambda r: r.url == APP + "/api/oidc/logout" and r.request.method == "POST"):
            pages[1].get_by_role("menuitem", name="退出登录").click()
        pages[1].wait_for_url(lambda url: "/auth" in str(url), timeout=30000)
        assert b.request.get(api_url).status == 401
        assert not errors, errors
        report = {"accounts": ["zhuqing", "yaojia"], "views": results, "deep_return": "exact path and query", "shared_edit_attachment_csrf": "passed", "website_logout_with_old_cookie_replay": "401 for notes and attachment; other member stays authorized", "app_logout": "passed", "expiry": "isolated real-provider shortened deadline test; production keeps 30m/8h", "test_note": title}
        (OUT / "production-checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), flush=True)
    finally:
        # If sessions still authorize, delete only this test note. Otherwise the
        # release operator removes its exact data paths, never arbitrary notes.
        if created:
            for context in contexts:
                response = context.request.delete(APP + "/api/notes/" + quote(title), headers={"Origin": BASE})
                if response.status in (200, 404):
                    break
        print("TEST_ASSET:", title, flush=True)
        browser.close()
