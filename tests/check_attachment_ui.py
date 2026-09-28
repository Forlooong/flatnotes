"""Focused real-browser checks; production login is entered manually on site."""
import base64
import json
import sys
import uuid
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

PROD = "--production" in sys.argv
SITE = "https://www.040323.xyz" if PROD else "http://127.0.0.1:8765"
BASE = SITE + "/apps/notes" if PROD else "http://127.0.0.1:18081/apps/notes"
OUT = Path("docs/evidence/2026-09-28/attachment-lifecycle") / ("production" if PROD else "local")
OUT.mkdir(parents=True, exist_ok=True)
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII=")
results = []


def upload(page, filename, data):
    button = page.locator("button.image")
    if not button.is_visible():
        page.locator("button.more").click()
        button = page.locator(".toastui-editor-dropdown-toolbar button.image")
    button.click()
    page.locator('.toastui-editor-popup input[type="file"]').set_input_files({"name": filename, "mimeType": "image/png", "buffer": data})
    with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/api/attachments")) as response:
        page.locator(".toastui-editor-popup:visible").get_by_text("确认", exact=True).click()
    assert response.value.status == 200
    attachment = response.value.json()
    expect(page.locator(".toastui-editor.md-mode .ProseMirror")).to_contain_text(attachment["filename"])
    return attachment


def status(page, url, expected):
    page.wait_for_function("""async ({url, expected}) => (await fetch(url)).status === expected""", arg={"url": BASE + "/" + url, "expected": expected})


with sync_playwright() as p:
    browser = p.chromium.launch(headless=not PROD)
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="zh-CN", reduced_motion="reduce")
    context.set_default_navigation_timeout(60000)
    if not PROD:
        context.add_cookies([{"name": "flatnotes_session", "value": "fixture-session", "domain": "127.0.0.1", "path": "/apps/notes/"}, {"name": "site_session", "value": "fixture-site", "domain": "127.0.0.1", "path": "/"}])
    if not PROD:
        context.route("http://127.0.0.1:18081/", lambda r: r.fulfill(body="local homepage target"))
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: (errors.append(str(error)), print("PAGE_ERROR:", str(error), flush=True)))
    if not PROD:
        page.on("console", lambda msg: print("CONSOLE:", msg.text, flush=True) if msg.type == "error" else None)
    page.on("dialog", lambda dialog: dialog.accept())
    page.goto(BASE + "/new?attachment_check=20260928", wait_until="domcontentloaded")
    if PROD:
        print("MANUAL_LOGIN_REQUIRED: 请仅在网站窗口手动登录。", flush=True)
        page.wait_for_url(BASE + "/new?attachment_check=20260928", timeout=900000)
    expect(page.get_by_placeholder("笔记标题")).to_be_visible(timeout=60000)
    for width, height in [(1440, 1000), (390, 844)]:
        page.set_viewport_size({"width": width, "height": height})
        cdp = context.new_cdp_session(page)
        cdp.send("Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": width < 760})
        cdp.send("Emulation.setTouchEmulationEnabled", {"enabled": width < 760})
        print(f"Testing viewport {width}", flush=True)
        title = "附件生命周期验证-" + uuid.uuid4().hex[:8]
        page.get_by_placeholder("笔记标题").fill(title)
        editor = page.locator(".toastui-editor.md-mode .ProseMirror")
        editor.fill("附件草稿验证")
        data = PNG + title.encode()
        first = upload(page, title + ".png", data)
        second = upload(page, title + "-重复.png", data)
        assert first == second
        expect(page.locator("nav .app-return-home")).to_have_count(0)
        home = page.get_by_role("link", name="返回网站首页")
        box = home.bounding_box()
        assert home.evaluate("e=>getComputedStyle(e).position") == "fixed"
        assert box["x"] > width / 2 and box["y"] > height / 2
        assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
        expect(page.get_by_text("附件已上传 ✓", exact=True)).to_have_count(0, timeout=15000)
        page.screenshot(path=str(OUT / f"editor-{width}.png"), full_page=True)
        # SPA navigation flushes the draft before the editor is unmounted.
        page.locator(".notes-wordmark").click()
        page.wait_for_url(lambda url: url.rstrip("/") == BASE, timeout=15000)
        expect(page.locator(".shared-notes-home")).to_be_visible()
        status(page, first["url"], 200)
        page.get_by_role("link", name="新建笔记").click()
        expect(page.get_by_text("发现未保存的草稿", exact=True)).to_be_visible()
        page.get_by_role("button", name="继续草稿", exact=True).click()
        expect(editor).to_contain_text(first["filename"])
        # A refresh also keeps the reference and the local draft.
        page.reload(wait_until="domcontentloaded")
        page.get_by_role("button", name="继续草稿", exact=True).click()
        expect(editor).to_contain_text(first["filename"])
        status(page, first["url"], 200)
        page.get_by_role("link", name="返回网站首页").click()
        page.wait_for_url(SITE + "/" if PROD else "http://127.0.0.1:18081/")
        if PROD:
            expect(page.locator("[data-app-url]")).to_have_attribute("aria-disabled", "false", timeout=30000)
            expect(page.locator(".app-lock:visible")).to_have_count(0)
            page.locator("[data-app-url]").click()
            expect(page.locator(".shared-notes-home")).to_be_visible(timeout=30000)
            page.get_by_role("link", name="新建笔记").click()
        else:
            page.goto(BASE + "/new", wait_until="domcontentloaded")
        page.get_by_role("button", name="继续草稿", exact=True).click()
        expect(editor).to_contain_text(first["filename"])
        status(page, first["url"], 200)
        failed_discard = not PROD and width == 1440
        def fail_discard(route):
            if route.request.post_data_json.get("discard"):
                route.fulfill(status=503, body="test cleanup interruption")
            else:
                route.continue_()
        if failed_discard:
            context.route(BASE + "/api/attachment-drafts/*", fail_discard)
        page.get_by_role("button", name="编辑", exact=True).click()
        page.get_by_role("button", name="放弃修改", exact=True).click()
        expect(page.locator(".shared-notes-home")).to_be_visible()
        if failed_discard:
            expect(page.get_by_text("附件清理暂未完成，下次打开编辑页时会重试。", exact=True)).to_be_visible()
            status(page, first["url"], 200)
            context.unroute(BASE + "/api/attachment-drafts/*", fail_discard)
        else:
            status(page, first["url"], 404)
        # A successful save converts draft references to note references.
        page.get_by_role("link", name="新建笔记").click()
        status(page, first["url"], 404)
        page.get_by_placeholder("笔记标题").fill(title)
        editor.fill("正式引用验证")
        saved_image = upload(page, title + ".png", data)
        with page.expect_response(lambda r: r.request.method == "POST" and r.url.endswith("/api/notes")) as saved:
            page.get_by_role("button", name="保存", exact=True).click()
        assert saved.value.status == 200, (saved.value.status, saved.value.text())
        page.wait_for_url("**/note/**")
        status(page, saved_image["url"], 200)
        editor.fill("已移除附件，保存后应清理")
        with page.expect_response(lambda r: r.request.method == "PATCH" and "/api/notes/" in r.url):
            page.get_by_role("button", name="保存", exact=True).click()
        status(page, saved_image["url"], 404)
        page.get_by_role("button", name="删除", exact=True).click()
        page.locator(".notes-modal").get_by_role("button", name="删除", exact=True).click()
        expect(page.locator(".shared-notes-home")).to_be_visible()
        expect(page.get_by_text("笔记已删除 ✓", exact=True)).to_have_count(0, timeout=15000)
        page.screenshot(path=str(OUT / f"home-{width}.png"), full_page=True)
        results.append({"width": width, "duplicate_reuse": True, "draft_leave_reload_retained": True, "discard_removed": True, "saved_note_retained": True, "removed_reference_collected": True, "floating_home": True})
        if width == 1440:
            page.get_by_role("link", name="新建笔记").click()
    page.get_by_role("link", name="返回网站首页").click()
    page.wait_for_url(SITE + "/" if PROD else "http://127.0.0.1:18081/")
    assert not errors, errors
    (OUT / "checks.json").write_text(json.dumps({"production": PROD, "checks": results, "pageErrors": errors}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False), flush=True)
    browser.close()
