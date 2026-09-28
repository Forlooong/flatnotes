"""Compare actual homepage tokens and exercise Notes UI in a local fixture."""
import json,uuid
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright,expect
OUT=Path('docs/evidence/2026-09-28/style-unification'); OUT.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:18081/apps/notes'
SITE='https://www.040323.xyz'
def overflow(page):
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
def capture(page,name):
 overflow(page); page.screenshot(path=str(OUT/(name+'.png')),animations='disabled')
with sync_playwright() as p:
 browser=p.chromium.launch(); results=[]
 for width,height in [(1440,1000),(390,844),(320,760)]:
  context=browser.new_context(viewport={'width':width,'height':height},locale='zh-CN',reduced_motion='reduce',is_mobile=width<760,has_touch=width<760)
  site=context.new_page(); site.goto(SITE+'/',wait_until='networkidle')
  expected=site.locator('body').evaluate('e=>({background:getComputedStyle(e).backgroundColor,color:getComputedStyle(e).color,font:getComputedStyle(e).fontFamily})')
  site_left=site.locator('#inner_wrapper').evaluate('e=>e.getBoundingClientRect().left+parseFloat(getComputedStyle(e).paddingLeft)')
  if width!=320: capture(site,f'website-{width}')
  context.add_cookies([{'name':'flatnotes_session','value':'fixture-session','domain':'127.0.0.1','path':'/apps/notes/'},{'name':'site_session','value':'fixture-site','domain':'127.0.0.1','path':'/'}])
  page=context.new_page(); errors=[]; page.on('pageerror',lambda e: errors.append(str(e)))
  page.goto(BASE+'/',wait_until='networkidle')
  actual=page.locator('body').evaluate('e=>({background:getComputedStyle(e).backgroundColor,color:getComputedStyle(e).color,font:getComputedStyle(e).fontFamily})')
  assert actual==expected,(actual,expected)
  notes_left=page.locator('.notes-shell').evaluate('e=>e.getBoundingClientRect().left+parseFloat(getComputedStyle(e).paddingLeft)')
  assert abs(notes_left-site_left)<1,(width,notes_left,site_left)
  expect(page.get_by_role('link',name='欢迎使用',exact=True)).to_be_visible()
  expect(page.get_by_role('link',name='返回网站首页')).to_have_attribute('href','/')
  assert page.get_by_role('menuitem',name='全部笔记').count()==0
  if width!=320: capture(page,f'home-{width}')
  page.get_by_role('button',name='菜单',exact=True).click()
  expect(page.get_by_role('menuitem',name='全部笔记')).to_be_visible()
  if width!=320: capture(page,f'menu-{width}')
  page.get_by_role('menuitem',name='搜索笔记').click()
  search=page.locator('.notes-modal input'); expect(search).to_be_visible()
  search.fill('欢迎使用'); search.press('Enter')
  page.wait_for_url('**/search?term=*')
  expect(page.locator('.notes-search-result a').first).to_be_visible()
  if width!=320: capture(page,f'search-{width}')
  page.locator('.notes-search-result a').first.click()
  page.wait_for_url('**/note/**'); page.reload(wait_until='networkidle')
  expect(page.locator('.toast-viewer')).to_contain_text('共享笔记测试')
  expect(page.get_by_role('link',name='共享笔记',exact=True)).to_be_visible()
  if width!=320: capture(page,f'read-{width}')
  page.get_by_role('button',name='菜单',exact=True).click(); page.get_by_role('menuitem',name='切换主题').click()
  assert page.locator('body').evaluate("e=>e.classList.contains('dark')")
  if width!=320: capture(page,f'dark-read-{width}')
  page.get_by_role('button',name='菜单',exact=True).click(); page.get_by_role('menuitem',name='切换主题').click()
  page.get_by_role('link',name='新建笔记').click()
  title='样式验证-'+uuid.uuid4().hex[:8]
  page.get_by_placeholder('Title').fill(title)
  editor=page.locator('.toastui-editor.md-mode .ProseMirror'); editor.click(); page.keyboard.type('## 共享日常\n记录今天的小事 #shared')
  if width!=320: capture(page,f'editor-{width}')
  page.get_by_role('button',name='菜单',exact=True).click(); page.get_by_role('menuitem',name='切换主题').click()
  assert page.locator('body').evaluate("e=>e.classList.contains('dark')")
  if width!=320: capture(page,f'dark-editor-{width}')
  page.get_by_role('button',name='菜单',exact=True).click(); page.get_by_role('menuitem',name='切换主题').click()
  with page.expect_response(lambda r:r.request.method=='POST' and r.url==BASE+'/api/notes') as saved:
   page.get_by_role('button',name='Save',exact=True).click()
  assert saved.value.status==200
  page.get_by_role('button',name='Edit',exact=True).click()
  expect(page.locator('.toast-viewer')).to_contain_text('记录今天的小事')
  page.get_by_role('button',name='Edit',exact=True).click()
  expect(page.locator('.toastui-editor.md-mode .ProseMirror')).to_be_visible()
  page.locator('.toastui-editor.md-mode .ProseMirror').click()
  page.keyboard.press('Control+End'); page.keyboard.type('\n共同编辑的补充')
  with page.expect_response(lambda r:r.request.method=='PATCH') as edited:
   page.get_by_role('button',name='Save',exact=True).click()
  assert edited.value.status==200
  assert context.request.delete(BASE+'/api/notes/'+quote(title),headers={'Origin':'http://127.0.0.1:18081'}).status==200
  overflow(page); assert not errors,errors
  results.append({'viewport':width,'homepage_palette_font_and_alignment':'exact computed match','menu_search_theme_read_editor_create_save_edit':'passed','overflow':False,'pageErrors':errors})
  context.close()
 browser.close()
(OUT/'checks.json').write_text(json.dumps({'environment':'local authenticated fixture; authentication protocol unchanged','results':results},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False))
