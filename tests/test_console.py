"""Production UI feature checks with synthetic I/Q and actual Web Audio."""
import asyncio
import os
import subprocess
import sys
import httpx
import pytest
from playwright.async_api import async_playwright
from tests.test_backend import backend, free_port
from tests.test_browser import ROOT, AUDIO_MONITOR
from tests.test_capture import wait_status


@pytest.mark.asyncio
async def test_console_automation_fft_bookmarks_freeze_visibility_and_mobile(tmp_path):
    iq_port, health_port, web_port = free_port(), free_port(), free_port()
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join(str(ROOT/p) for p in ['shared', 'sdr-server'])}
    with (tmp_path/'console.log').open('w') as log:
        source = subprocess.Popen([sys.executable, str(ROOT/'tools/synthetic_iq.py'),
            '--address', f'tcp://127.0.0.1:{iq_port}', '--health-port', str(health_port),
            '--idle-seconds', '.1'], env=env, stdout=log, stderr=log)
        server = None
        try:
            async with backend(free_port(), iq_port, tmp_path) as receiver, httpx.AsyncClient() as http:
                server = subprocess.Popen([sys.executable, str(ROOT/'tests/serve_frontend.py'),
                    '--port', str(web_port), '--backend', receiver], stdout=log, stderr=log)
                origin = f'http://127.0.0.1:{web_port}'
                for _ in range(100):
                    try:
                        if (await http.get(origin+'/config.yaml')).status_code == 200: break
                    except httpx.ConnectError: pass
                    await asyncio.sleep(.05)
                async with async_playwright() as playwright:
                    browser = await playwright.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH', '/usr/bin/google-chrome'),
                        headless=True, args=['--no-sandbox', '--autoplay-policy=no-user-gesture-required'])
                    page = await browser.new_page(viewport={'width':1280, 'height':1000})
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    await page.add_init_script(AUDIO_MONITOR)
                    await page.goto(origin+'/sdr')
                    await page.get_by_text('CONNECTED', exact=True).wait_for()
                    await page.get_by_role('button', name='Find strongest').wait_for()
                    await page.wait_for_function('!document.querySelector(".assist-actions button").disabled')
                    await page.get_by_role('button', name='Find strongest').click()
                    frequency = int(await page.locator('#receiver-frequency').input_value())
                    assert abs(frequency - 10489700300) < 200
                    assert await page.locator('#receiver-bandwidth').input_value() == '1800'
                    await page.get_by_role('button', name='Auto all', exact=True).click()
                    for label in ['Auto frequency','Auto bandwidth','Auto display gain','Auto range']:
                        assert await page.get_by_role('checkbox', name=label, exact=True).is_checked()
                    await page.get_by_role('button', name='START AUDIO').click()
                    await page.wait_for_function('window.__audio.starts > 10')
                    contexts = await page.evaluate('window.__audio.created')
                    starts = await page.evaluate('window.__audio.starts')
                    await page.get_by_role('combobox', name='FFT size', exact=True).select_option('32768')
                    await page.wait_for_function('document.body.innerText.includes("3.9 Hz/bin")')
                    await page.wait_for_function(f'window.__audio.starts > {starts + 15}')
                    assert await page.evaluate('window.__audio.created') == contexts
                    await page.get_by_role('button', name='Freeze display', exact=True).click()
                    await asyncio.sleep(.3)
                    pixels = await page.locator('canvas.spectrum').evaluate('(c)=>c.toDataURL()')
                    starts = await page.evaluate('window.__audio.starts')
                    await asyncio.sleep(.5)
                    assert await page.locator('canvas.spectrum').evaluate('(c)=>c.toDataURL()') == pixels
                    assert await page.evaluate('window.__audio.starts') > starts
                    await page.get_by_role('button', name='Resume display', exact=True).click()
                    await page.get_by_role('button', name='Zoom in', exact=True).click()
                    await page.wait_for_function('document.querySelector(".plot-toolbar").innerText.includes("1.3×")')
                    await page.get_by_role('button', name='Reset zoom', exact=True).click()
                    await page.get_by_role('button', name='Fullscreen spectrum', exact=True).click()
                    await page.wait_for_function('document.fullscreenElement !== null')
                    await page.get_by_role('button', name='Fullscreen spectrum', exact=True).click()
                    await page.wait_for_function('document.fullscreenElement === null')
                    await page.get_by_role('combobox', name='Palette', exact=True).select_option('cividis')
                    await page.get_by_role('combobox', name='Display profile', exact=True).select_option('eco')
                    assert await page.get_by_role('combobox', name='FFT size', exact=True).input_value() == '2048'
                    assert await page.get_by_role('combobox', name='Display FPS', exact=True).input_value() == '5'
                    await page.get_by_role('slider', name='Display gain', exact=True).press('ArrowRight')
                    assert not await page.get_by_role('checkbox', name='Auto display gain', exact=True).is_checked()
                    await page.get_by_role('slider', name='Dynamic range', exact=True).press('ArrowRight')
                    assert not await page.get_by_role('checkbox', name='Auto range', exact=True).is_checked()
                    await page.get_by_role('button', name='Tune up', exact=True).click()
                    assert not await page.get_by_role('checkbox', name='Auto frequency', exact=True).is_checked()
                    assert not await page.get_by_role('checkbox', name='Auto bandwidth', exact=True).is_checked()
                    await page.get_by_role('button', name='Save', exact=True).click()
                    saved = await page.locator('#receiver-frequency').input_value()
                    saved_bw = await page.locator('#receiver-bandwidth').input_value()
                    await page.get_by_role('button', name='Share', exact=True).click()
                    link = await page.get_by_role('textbox', name='Receiver share link').input_value()
                    assert 'freq='+saved in link and 'bw='+saved_bw in link
                    # A visibility event is injected to exercise the browser's actual handler.
                    await page.evaluate('''() => { Object.defineProperty(document, 'hidden', {configurable:true, value:true});
                        document.dispatchEvent(new Event('visibilitychange')); }''')
                    await asyncio.sleep(.4)
                    assert (await http.get(receiver+'/stream-info')).json()['clients'] == 1
                    starts = await page.evaluate('window.__audio.starts')
                    await asyncio.sleep(.3)
                    assert await page.evaluate('window.__audio.starts') > starts
                    await page.get_by_role('button', name='STOP AUDIO').click()
                    await page.get_by_text('PAUSED IN BACKGROUND', exact=True).wait_for()
                    idle = await wait_status(http, f'http://127.0.0.1:{health_port}/health', lambda s: s['mode'] == 'idle')
                    assert idle['subscribers'] == 0 and not idle['capture_active']
                    await page.evaluate('''() => { Object.defineProperty(document, 'hidden', {configurable:true, value:false});
                        document.dispatchEvent(new Event('visibilitychange')); }''')
                    await page.get_by_text('CONNECTED', exact=True).wait_for()
                    active = await wait_status(http, f'http://127.0.0.1:{health_port}/health', lambda s: s['capture_active'])
                    assert active['capture_starts'] == 2
                    await page.reload()
                    await page.get_by_text('CONNECTED', exact=True).wait_for()
                    assert await page.locator('#receiver-frequency').input_value() == saved
                    assert await page.get_by_role('combobox', name='Palette', exact=True).input_value() == 'cividis'
                    assert await page.get_by_role('combobox', name='FFT size', exact=True).input_value() == '2048'
                    assert await page.locator('.bookmark-row').count() == 1
                    await page.get_by_role('button', name='Remove saved frequency 1').click()
                    assert await page.locator('.bookmark-row').count() == 0
                    await page.screenshot(path='/tmp/websdr-console-desktop.png', full_page=True)
                    for width in [390, 450, 768]:
                        await page.set_viewport_size({'width':width,'height':900})
                        await asyncio.sleep(.2)
                        assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), width
                        assert await page.get_by_role('slider', name='Volume', exact=True).is_visible()
                    await page.set_viewport_size({'width':390,'height':900})
                    await page.screenshot(path='/tmp/websdr-console-mobile.png', full_page=True)
                    assert errors == [], errors
                    await browser.close()
        finally:
            source.terminate(); source.wait(timeout=10)
            if server is not None: server.terminate(); server.wait(timeout=5)
