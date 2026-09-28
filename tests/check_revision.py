"""Six-item UI regression, real Chromium; local fixture or manual production login.

No real credentials, cookie values, tokens or storage state are read or persisted.
"""
import json, sys, uuid, base64
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright, expect

PRODUCTION = '--production' in sys.argv
RESUME = '--resume' in sys.argv
WAIT = 'domcontentloaded' if PRODUCTION else 'networkidle'
SITE = 'https://www.040323.xyz' if PRODUCTION else 'http://127.0.0.1:8765'
BASE = SITE + '/apps/notes' if PRODUCTION else 'http://127.0.0.1:18081/apps/notes'
OUT = Path('docs/evidence/2026-09-28/ui-revision') / ('production' if PRODUCTION else 'local')
OUT.mkdir(parents=True, exist_ok=True)
results = []

def capture(page, name):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), name
    page.screenshot(path=str(OUT / (name + '.png')), animations='disabled', full_page=True)

def application_state(page, logged, enabled):
    expect(page.locator('[data-member-required][href]')).to_have_count(1 if enabled else 0)
    expect(page.locator('[data-member-required][aria-disabled="true"]')).to_have_count(7 if enabled else 8)
    assert page.locator('.app-lock:visible').count() == (0 if logged else 8)

def favicon(page, brand):
    assert brand in page.title()
    url = page.locator('link[rel="icon"]').evaluate('e=>e.href')
    response = page.request.get(url)
    assert response.status == 200 and 'image/svg+xml' in response.headers.get('content-type', '')
    if brand == 'Flatnotes':
        assert response.body() == Path('client/assets/notes.svg').read_bytes()
    return url

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9225') if RESUME else p.chromium.launch(headless=not PRODUCTION, args=['--remote-debugging-port=9225'] if PRODUCTION else [])
    try:
        context = browser.contexts[0] if RESUME else browser.new_context(viewport={'width':1440,'height':1000}, locale='zh-CN', reduced_motion='reduce')
        context.set_default_navigation_timeout(60000)
        home = context.new_page()
        if not PRODUCTION:
            state = {'logged':False, 'authorized':False, 'failed':False}
            def identity(route):
                route.fulfill(status=503 if state['failed'] else 200, content_type='application/json', body=json.dumps({'data':{'authentication_level':1 if state['logged'] else 0,'username':'fixture-user' if state['logged'] else ''}}))
            context.route(SITE+'/auth/api/state', identity)
            context.route(SITE+'/member/', lambda route: route.fulfill(status=200 if state['authorized'] else 403, body='authorized fixture' if state['authorized'] else 'denied'))
            context.add_cookies([{'name':'flatnotes_session','value':'fixture-session','domain':'127.0.0.1','path':'/apps/notes/'},{'name':'site_session','value':'fixture-site','domain':'127.0.0.1','path':'/'}])
        if not RESUME:
            home.goto(SITE+'/', wait_until=WAIT)
            application_state(home, False, False)
            favicon(home, '040323')
            app = home.locator('[data-app-url]')
            app.click(force=True)
            assert home.url == SITE+'/'
            assert app.get_attribute('tabindex') == '-1'
            app.evaluate('e=>e.focus()'); home.keyboard.press('Enter')
            assert home.url == SITE+'/'
            home.reload(wait_until=WAIT); application_state(home, False, False)
            capture(home, 'anonymous-home')
            results.append({'anonymous_mouse_keyboard_refresh':'passed'})
            if PRODUCTION:
                home.goto(BASE+'/new?ui_revision=20260928', wait_until='domcontentloaded')
                print('MANUAL_LOGIN_REQUIRED: 请仅在打开的网站窗口输入账户密码。', flush=True)
                # Only boolean server session state is evaluated; no credential/cookie extraction.
                home.wait_for_function("""async () => {
                  try { const r=await fetch('/auth/api/state',{cache:'no-store'}); const j=await r.json(); return j.data?.authentication_level>=1; }
                  catch { return false; }
                }""", timeout=900000, polling=2000)
                home.wait_for_url(BASE+'/new?ui_revision=20260928', timeout=60000)
                results.append({'anonymous_deep_route_login_return':'exact path and query preserved'})
            else:
                state.update(logged=True, authorized=True)
        home.goto(SITE+'/', wait_until=WAIT); application_state(home, True, True)
        home.reload(wait_until=WAIT); application_state(home, True, True)
        capture(home, 'member-home')
        page = context.new_page(); errors=[]
        device = context.new_cdp_session(page)
        page.on('pageerror', lambda e: errors.append({'message':e.message,'stack':e.stack,'path':page.url.split('?')[0]}))
        prefix = '正式界面验证-' if PRODUCTION else '界面验证-'
        title = prefix + uuid.uuid4().hex[:8]
        for width,height in [(1280,900),(1440,1000),(1920,1080),(390,844),(320,760)]:
            page.set_viewport_size({'width':width,'height':height})
            device.send('Emulation.setTouchEmulationEnabled', {'enabled':width<760})
            device.send('Emulation.setDeviceMetricsOverride', {'width':width,'height':height,'deviceScaleFactor':1,'mobile':width<760})
            page.goto(BASE+'/', wait_until=WAIT)
            expect(page.locator('.notes-wordmark')).to_have_text('Flatnotes')
            page.wait_for_function("document.querySelector('.notes-wordmark img')?.complete && document.querySelector('.notes-wordmark img')?.naturalWidth>0")
            expect(page.get_by_role('link',name='返回网站首页')).to_have_attribute('href','/')
            favicon(page, 'Flatnotes')
            for selector in ['.notes-nav','.shared-notes-home']:
                box=page.locator(selector).bounding_box()
                assert abs(box['x']*2+box['width']-width)<2, (width,selector,box)
                assert box['width']<=960
            capture(page,f'home-{width}')
            page.get_by_role('button',name='菜单',exact=True).click()
            page.get_by_role('menuitem',name='全部笔记').click()
            page.wait_for_url('**/search?**'); page.wait_for_load_state(WAIT)
            box=page.locator('.notes-search-results').bounding_box()
            assert abs(box['x']*2+box['width']-width)<2
            capture(page,f'search-{width}')
            page.get_by_role('link',name='新建笔记').click()
            expect(page.get_by_placeholder('笔记标题')).to_be_visible()
            editor=page.locator('.toastui-editor.md-mode .ProseMirror')
            expect(editor).to_be_visible()
            assert not page.evaluate('document.activeElement?.isContentEditable')
            page.get_by_role('button',name='保存',exact=True).click()
            expect(page.get_by_text('请先填写笔记标题。',exact=True)).to_be_visible()
            page.get_by_placeholder('笔记标题').fill(title)
            editor.fill('## 中文笔记\n一起记录日常，验证保存和重新读取。\n[网站首页](/)')
            assert editor.evaluate('e=>getComputedStyle(e).cursor')=='text'
            assert page.get_by_placeholder('笔记标题').evaluate('e=>getComputedStyle(e).caretColor')!='rgba(0, 0, 0, 0)'
            capture(page,f'editor-{width}')
            # Chinese editor image dialog, responsive toolbar overflow included.
            image_button=page.locator('button.image')
            if not image_button.is_visible():
                page.locator('button.more').click()
                image_button=page.locator('.toastui-editor-dropdown-toolbar button.image')
            image_button.click()
            expect(page.get_by_text('插入图片',exact=True).last).to_be_visible()
            capture(page,f'image-dialog-{width}')
            if width == 390:
                filename = title + '.png'
                image_data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl1sAAAAASUVORK5CYII=')
                page.locator('.toastui-editor-popup input[type="file"]').set_input_files({'name':filename,'mimeType':'image/png','buffer':image_data})
                with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/api/attachments')) as uploaded:
                    page.locator('.toastui-editor-popup:visible').get_by_text('确认',exact=True).click()
                assert uploaded.value.status == 200
                attachment = uploaded.value.json()['url']
                assert context.request.get(BASE+'/'+attachment).body() == image_data
                (OUT/'temporary-attachment.json').write_text(json.dumps({'filename':filename,'url':attachment,'cleanup':'remove only this test image after release validation'},ensure_ascii=False),encoding='utf-8')
                expect(editor).to_contain_text(uploaded.value.json()['filename'])
            else:
                page.locator('.toastui-editor-popup:visible').get_by_text('取消',exact=True).click()
            # Preserve upstream rich text and preview switching.
            page.locator('.toastui-editor-mode-switch').get_by_text('富文本',exact=True).click()
            expect(page.locator('.toastui-editor.ww-mode .ProseMirror')).to_be_visible()
            page.locator('.toastui-editor-mode-switch').get_by_text('Markdown',exact=True).click()
            if width < 760:
                page.locator('.toastui-editor-md-tab-container').get_by_text('预览',exact=True).click()
                expect(page.locator('.toastui-editor-md-preview')).to_contain_text('一起记录日常')
                page.locator('.toastui-editor-md-tab-container').get_by_text('编辑',exact=True).click()
            with page.expect_response(lambda r:r.request.method=='POST' and r.url==BASE+'/api/notes') as saved:
                page.get_by_role('button',name='保存',exact=True).click()
            assert saved.value.status==200
            page.get_by_role('button',name='编辑',exact=True).click()
            expect(page.locator('.toast-viewer')).to_contain_text('一起记录日常')
            page.reload(wait_until=WAIT)
            favicon(page,'Flatnotes')
            assert page.locator('.toast-viewer .toastui-editor-contents').evaluate('e=>getComputedStyle(e).cursor')=='default'
            assert page.locator('.toast-viewer a').evaluate('e=>getComputedStyle(e).cursor')=='pointer'
            assert page.locator('.toast-viewer').evaluate('e=>getComputedStyle(e).userSelect')!='none'
            assert page.locator('[contenteditable="true"]').count()==0
            capture(page,f'read-{width}')
            page.get_by_role('button',name='编辑',exact=True).click()
            editor.fill('## 中文笔记\n重新编辑后的正文。')
            if width == 1280:
                page.wait_for_timeout(1200)  # The existing draft debounce is 1 second.
                page.once('dialog', lambda dialog: dialog.accept())
                page.reload(wait_until=WAIT)
                page.get_by_role('button',name='编辑',exact=True).click()
                expect(page.get_by_text('发现未保存的草稿',exact=True)).to_be_visible()
                capture(page,'draft-dialog')
                page.get_by_role('button',name='继续草稿',exact=True).click()
                expect(editor).to_contain_text('重新编辑后的正文')
            page.get_by_role('button',name='编辑',exact=True).click()
            expect(page.get_by_text('是否保存本次修改？',exact=True)).to_be_visible()
            capture(page,f'save-dialog-{width}')
            page.get_by_role('button',name='取消',exact=True).click()
            with page.expect_response(lambda r:r.request.method=='PATCH') as edited:
                page.get_by_role('button',name='保存',exact=True).click()
            assert edited.value.status==200
            page.get_by_role('button',name='编辑',exact=True).click()
            page.reload(wait_until=WAIT)
            expect(page.locator('.toast-viewer')).to_contain_text('重新编辑后的正文')
            page.get_by_role('button',name='菜单',exact=True).click(); page.get_by_role('menuitem',name='切换主题').click()
            capture(page,f'dark-read-{width}')
            page.get_by_role('button',name='菜单',exact=True).click(); page.get_by_role('menuitem',name='切换主题').click()
            page.get_by_role('button',name='删除',exact=True).click()
            expect(page.get_by_text('确认删除',exact=True)).to_be_visible()
            with page.expect_response(lambda r:r.request.method=='DELETE') as deleted:
                page.locator('.notes-modal').get_by_role('button',name='删除',exact=True).click()
            assert deleted.value.status==200
            page.wait_for_url(BASE+'/')
            results.append({'viewport':width,'centered_layout_brand_favicon_chinese_validation_dialogs_create_read_edit_delete_cursor_theme':'passed'})
        # Local-only server session transitions: denial, expiry, failed status and BFCache restore.
        if not PRODUCTION:
            state.update(logged=True,authorized=False)
            home.reload(wait_until=WAIT); application_state(home,True,False)
            state.update(logged=False,authorized=False)
            home.evaluate("window.dispatchEvent(new Event('focus'))")
            expect(home.locator('.app-lock:visible')).to_have_count(8)
            application_state(home,False,False)
            state.update(logged=True,authorized=True)
            home.reload(wait_until=WAIT); application_state(home,True,True)
            state.update(logged=False,authorized=False)
            home.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
            expect(home.locator('[data-member-required][href]')).to_have_count(0)
            state.update(failed=True)
            home.reload(wait_until=WAIT); application_state(home,False,False)
            results.append({'server_state_fixture_denied_expired_bfcache_failed':'passed; UI integration only, not real provider expiry'})
        else:
            page.goto(BASE+'/',wait_until=WAIT)
            page.get_by_role('link',name='返回网站首页').click()
            page.wait_for_url(SITE+'/'); application_state(page,True,True)
            page.go_back(wait_until=WAIT); page.go_forward(wait_until=WAIT)
            application_state(page,True,True)
            page.goto(BASE+'/',wait_until=WAIT)
            page.get_by_role('button',name='菜单',exact=True).click(); page.get_by_role('menuitem',name='退出登录').click()
            page.wait_for_url('**/auth/**')
            page.goto(SITE+'/',wait_until=WAIT); application_state(page,False,False)
            page.reload(wait_until=WAIT); application_state(page,False,False)
            results.append({'real_member_return_refresh_back_forward_logout':'passed'})
        assert not errors, errors
        (OUT/('production-checks.json' if PRODUCTION else 'local-checks.json')).write_text(json.dumps({'environment':'production manual login' if PRODUCTION else 'local app fixture + mocked homepage session responses','results':results,'pageErrors':errors,'visual_user_approval':'pending'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(results,ensure_ascii=False),flush=True)
        browser.close()
    except Exception:
        import traceback
        traceback.print_exc()
        if not PRODUCTION:
            raise
        print('PRODUCTION_CHECK_FAILED_SESSION_RETAINED: browser remains available on localhost:9225; no cookies persisted by test.', flush=True)
        for _ in range(900):
            if not browser.is_connected():
                break
            home.wait_for_timeout(1000)
        raise
