"""Real browser band changes, recording finalization, bookmarks and shared URLs."""
import asyncio
import json
import os
import subprocess
import sys
import httpx
import pytest
from playwright.async_api import async_playwright
from tests.test_backend import backend, free_port
from tests.test_browser import ROOT, AUDIO_MONITOR, source_process


@pytest.mark.asyncio
async def test_band_switch_stops_recording_and_audio_and_preserves_shared_tuning(tmp_path):
    iq_port, web_port = free_port(), free_port()
    with (tmp_path/'bands-browser.log').open('w') as log:
        source = source_process(iq_port,log)
        server = None
        try:
            async with backend(free_port(),iq_port,tmp_path) as receiver, httpx.AsyncClient() as http:
                server = subprocess.Popen([sys.executable,str(ROOT/'tests/serve_frontend.py'),
                    '--port',str(web_port),'--backend',receiver],stdout=log,stderr=log)
                origin = f'http://127.0.0.1:{web_port}'
                for _ in range(100):
                    try:
                        if (await http.get(origin+'/config.yaml')).status_code == 200: break
                    except httpx.ConnectError: pass
                    await asyncio.sleep(.05)
                catalog = (await http.get(origin+'/bands')).json()
                assert len(catalog['bands']) == 5
                assert (await http.get(receiver+'/stream-info')).json()['clients'] == 0
                async with async_playwright() as playwright:
                    browser = await playwright.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH','/usr/bin/google-chrome'),
                        headless=True,args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
                    page = await browser.new_page(viewport={'width':1280,'height':1000})
                    errors, sockets, sent = [], [], []
                    page.on('pageerror',lambda error:errors.append(str(error)))
                    page.on('websocket',lambda ws:(sockets.append(ws.url),ws.on('framesent',lambda frame:sent.append(frame))))
                    await page.add_init_script(AUDIO_MONITOR)
                    await page.goto(origin+'/sdr')
                    await page.get_by_text('CONNECTED',exact=True).wait_for()
                    bands = page.get_by_role('combobox',name='Receive band',exact=True)
                    assert await bands.input_value() == '0'
                    await page.get_by_role('button',name='START AUDIO',exact=True).click()
                    await page.wait_for_function('window.__audio.starts > 5')
                    await page.get_by_role('button',name='Start recording',exact=True).click()
                    await asyncio.sleep(1.2)
                    await bands.select_option('1')
                    await page.get_by_text('CONNECTED',exact=True).wait_for()
                    await page.get_by_role('link',name='Download metadata',exact=True).wait_for()
                    metadata = await page.get_by_role('link',name='Download metadata',exact=True).get_attribute('href')
                    info = json.loads(await page.evaluate('(url)=>fetch(url).then(response=>response.text())',metadata))
                    assert info['stopReason'] == 'audio stopped' and info['durationSeconds'] > 1
                    assert await page.get_by_role('button',name='START AUDIO',exact=True).is_visible()
                    assert sockets[-1].endswith('/iq?band=1')
                    assert await page.locator('#receiver-frequency').input_value() == '10489780000'
                    # The 31 kHz synthetic carrier is also inside this overlapping band.
                    await page.locator('#receiver-frequency').fill('10489730500')
                    await page.locator('#receiver-frequency').press('Tab')
                    await page.get_by_role('button',name='Save',exact=True).click()
                    await page.get_by_role('button',name='Share',exact=True).click()
                    link = await page.get_by_role('textbox',name='Receiver share link',exact=True).input_value()
                    assert 'band=1' in link and 'freq=10489730500' in link
                    await page.reload()
                    await page.get_by_text('CONNECTED',exact=True).wait_for()
                    assert await bands.input_value() == '1'
                    assert await page.locator('#receiver-frequency').input_value() == '10489730500'
                    assert await page.locator('.bookmark-row').count() == 1
                    await bands.select_option('-1')
                    await page.get_by_text('CONNECTED',exact=True).wait_for()
                    await page.locator('.bookmark-row button').first.click()
                    await page.get_by_text('CONNECTED',exact=True).wait_for()
                    assert await bands.input_value() == '1'
                    assert await page.locator('#receiver-frequency').input_value() == '10489730500'
                    starts = await page.evaluate('window.__audio.starts')
                    await page.get_by_role('button',name='START AUDIO',exact=True).click()
                    await page.wait_for_function(f'window.__audio.starts > {starts+10}')
                    assert await page.evaluate('window.__audio.peaks.slice(-10).some(x=>x>0.1)')
                    assert (await http.get(receiver+'/stream-info')).json()['active_bands'] == 1

                    # Full IQ is an explicit selection and retains the current tuning.
                    await page.get_by_role('button',name='Start recording',exact=True).click()
                    await asyncio.sleep(1.2)
                    await bands.select_option('full')
                    await page.get_by_text('CONNECTED',exact=True).wait_for()
                    await page.get_by_role('link',name='Download metadata',exact=True).wait_for()
                    metadata = await page.get_by_role('link',name='Download metadata',exact=True).get_attribute('href')
                    info = json.loads(await page.evaluate('(url)=>fetch(url).then(response=>response.text())',metadata))
                    assert info['stopReason'] == 'audio stopped' and info['durationSeconds'] > 1
                    assert await page.get_by_role('button',name='START AUDIO',exact=True).is_visible()
                    assert sockets[-1].endswith('/iq?band=full')
                    frequency = page.locator('#receiver-frequency')
                    assert await frequency.input_value() == '10489730500'
                    assert await frequency.get_attribute('min') == '10489500000'
                    assert await frequency.get_attribute('max') == '10489900000'
                    assert '8.33 Mbit/s I/Q' in await page.locator('.tuning-panel').inner_text()
                    # Tuning outside a single subband must keep full reception selected.
                    full_sockets = len(sockets)
                    await frequency.fill('10489860000')
                    await frequency.press('Tab')
                    assert await bands.input_value() == 'full'
                    assert await frequency.input_value() == '10489860000'
                    # Return to a real carrier to check audio at the full input rate.
                    await frequency.fill('10489730000')
                    await frequency.press('Tab')
                    await page.get_by_role('button',name='Save',exact=True).click()
                    await page.get_by_role('button',name='Share',exact=True).click()
                    link = await page.get_by_role('textbox',name='Receiver share link',exact=True).input_value()
                    assert 'band=full' in link and 'freq=10489730000' in link
                    assert len(sockets) == full_sockets
                    await page.reload()
                    await page.get_by_text('CONNECTED',exact=True).wait_for()
                    assert await bands.input_value() == 'full'
                    assert await frequency.input_value() == '10489730000'
                    assert await page.locator('.bookmark-row').count() == 2
                    await bands.select_option('-2')
                    await page.get_by_text('CONNECTED',exact=True).wait_for()
                    await page.locator('.bookmark-row button').first.click()
                    await page.get_by_text('CONNECTED',exact=True).wait_for()
                    assert await bands.input_value() == 'full'
                    assert await frequency.input_value() == '10489730000'
                    starts = await page.evaluate('window.__audio.starts')
                    await page.get_by_role('button',name='START AUDIO',exact=True).click()
                    await page.wait_for_function(f'window.__audio.starts > {starts+10}')
                    assert await page.evaluate('window.__audio.peaks.slice(-10).some(x=>x>0.1)')
                    state = (await http.get(receiver+'/stream-info')).json()
                    assert state['clients'] == 1 and state['full_band_clients'] == 1
                    assert state['active_bands'] == 0 and state['sample_rate'] == 520834
                    assert sent == [] and errors == []
                    await page.screenshot(path='/tmp/websdr-iq-subbands.png',full_page=True)
                    await browser.close()
        finally:
            source.terminate();source.wait(timeout=5)
            if server is not None:server.terminate();server.wait(timeout=5)
