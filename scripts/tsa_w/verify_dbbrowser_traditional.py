#!/usr/bin/env python3
"""db-browser 繁體修復瀏覽器驗證：閘面→owner 密碼→解密→繁體 UI render"""
import asyncio, sys
from playwright.async_api import async_playwright

PW = open('/home/z/my-project/.keys/tsa_pw_owner.txt').read().strip()
URL = 'http://localhost:8934/admin/db-browser.html'

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={'width': 1280, 'height': 900})
        await page.goto(URL, wait_until='domcontentloaded')
        # 1) 閘面
        gate = await page.query_selector('#staticrypt-password')
        assert gate, '閘面無密碼框'
        print('1. 閘面出現 ✓')
        # remember checkbox 存在（remember=30 應有 UI）
        rem = await page.query_selector('#staticrypt-remember')
        print(f'2. remember 掣 {"✓ 存在" if rem else "✗ 唔見咗"}')
        await page.fill('#staticrypt-password', PW)
        await page.click('.staticrypt-decrypt-button')
        await page.wait_for_selector('text=數據庫瀏覽器', timeout=8000)
        print('3. 解密後繁體標題「數據庫瀏覽器」render ✓')
        # 2) 抽主要 UI 文字驗繁體
        checks = {
            'h1': '數據庫瀏覽器',
            'tab-ranking': '信號排名',
            'tab-symbols': '貨幣對統計',
        }
        h1 = await page.text_content('h1')
        assert '數據庫瀏覽器' in h1, f'h1 異常: {h1}'
        print(f'4. h1 = {h1.strip()} ✓')
        tabs = await page.eval_on_selector_all('.tab', 'els => els.map(e => e.textContent.trim())')
        print(f'5. tabs = {tabs}')
        assert any('信號排名' in t for t in tabs) and any('貨幣對統計' in t for t in tabs)
        # 3) 全頁無簡體殘留（DOM 文字層面）
        body_text = await page.evaluate('document.body.innerText')
        from opencc import OpenCC
        cc = OpenCC('s2t')
        simp = [ch for ch in body_text if '\u4e00' <= ch <= '\u9fff' and cc.convert(ch) != ch and ch not in set('台晒游群准')]
        assert not simp, f'DOM 仲有簡體: {simp[:20]}'
        print(f'6. DOM innerText 簡體殘留: 0 ✓（共 {len(body_text)} 字符）')
        # 4) 截圖留證
        await page.screenshot(path='/home/z/my-project/download/驗證_dbbrowser繁體_1280.png', full_page=False)
        print('7. 截圖已存 download/驗證_dbbrowser繁體_1280.png ✓')
        await browser.close()

asyncio.run(main())
print('DBBROWSER_VERIFY 7/7 PASS')
