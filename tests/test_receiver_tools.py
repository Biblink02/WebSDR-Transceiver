"""Real worker/WASM audio, pinned drifting signals and native local recording."""
import asyncio
import os
import subprocess
import sys
import httpx
import pytest
from playwright.async_api import async_playwright
from tests.test_backend import backend, free_port
from tests.test_browser import ROOT, AUDIO_MONITOR


@pytest.mark.asyncio
async def test_audio_tracking_recording_and_shortcuts(tmp_path):
    iq_port, web_port = free_port(), free_port()
    mute = tmp_path/'mute-primary'
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join(str(ROOT/p) for p in ['shared', 'sdr-server'])}
    with (tmp_path/'tools.log').open('w') as log:
        source = subprocess.Popen([sys.executable, str(ROOT/'tools/synthetic_iq.py'),
            '--address', f'tcp://127.0.0.1:{iq_port}', '--drift-hz-per-second', '10',
            '--mute-primary-file', str(mute)], env=env, stdout=log, stderr=log)
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
                    errors = []; sent = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('websocket', lambda ws: ws.on('framesent', lambda frame: sent.append(frame)))
                    await page.add_init_script(AUDIO_MONITOR)
                    await page.goto(origin+'/sdr')
                    await page.get_by_text('CONNECTED', exact=True).wait_for()
                    await page.get_by_role('combobox', name='FFT size', exact=True).select_option('32768')
                    await page.get_by_role('button', name='Track signal 1', exact=True).wait_for()
                    await page.get_by_role('button', name='Track signal 1', exact=True).click()
                    await page.wait_for_function('document.querySelector(".tracking-controls").innerText.includes("TRACKING")')
                    initial = int(await page.locator('#receiver-frequency').input_value())
                    await page.wait_for_function(f'Number(document.querySelector("#receiver-frequency").value) > {initial + 20}')
                    mute.touch()
                    await page.wait_for_function('document.querySelector(".tracking-controls").innerText.includes("LOST")')
                    held = int(await page.locator('#receiver-frequency').input_value())
                    await asyncio.sleep(1)
                    assert await page.locator('#receiver-frequency').input_value() == str(held)
                    assert abs(held - initial) < 300, 'Pinned target jumped to a stronger remote carrier'
                    mute.unlink()
                    await page.wait_for_function('document.querySelector(".tracking-controls").innerText.includes("TRACKING")')
                    await page.get_by_role('button', name='Release tracking').click()
                    await page.get_by_role('combobox', name='Receiver mode', exact=True).select_option('cw')
                    assert await page.locator('#receiver-bandwidth').input_value() == '500'
                    await page.get_by_role('slider', name='CW pitch').press('End')
                    await page.get_by_role('button', name='START AUDIO').click()
                    await page.wait_for_function('window.__audio.peaks.some(value => value > .1)')
                    await page.wait_for_function('''Math.abs(Number(document.querySelector('.signal-frequency').textContent.trim().split(' ')[0])*1e6-10489701000)<500''')
                    await page.get_by_role('button', name='Track signal 1', exact=True).click()
                    before_hidden = int(await page.locator('#receiver-frequency').input_value())
                    await page.evaluate('''() => {Object.defineProperty(document, 'hidden', {configurable:true, value:true});
                        document.dispatchEvent(new Event('visibilitychange'));}''')
                    try:
                        await page.wait_for_function(f'Number(document.querySelector("#receiver-frequency").value) > {before_hidden + 10}', timeout=8000)
                    except Exception:
                        raise AssertionError({'before':before_hidden, 'after':await page.locator('#receiver-frequency').input_value(),
                            'tracking':await page.locator('.tracking-controls').inner_text(), 'errors':errors})
                    await page.evaluate('''() => {Object.defineProperty(document, 'hidden', {configurable:true, value:false});
                        document.dispatchEvent(new Event('visibilitychange'));}''')
                    await page.get_by_role('button', name='Release tracking').click()
                    await page.get_by_role('checkbox', name='Audio AGC', exact=True).uncheck()
                    await page.get_by_role('checkbox', name='Squelch', exact=True).check()
                    await page.get_by_role('slider', name='Squelch threshold').press('End')
                    await page.wait_for_function('document.querySelector(".audio-panel").innerText.includes("SQUELCH CLOSED")')
                    await page.get_by_role('checkbox', name='Squelch', exact=True).uncheck()
                    await page.get_by_role('slider', name='Volume', exact=True).press('Home')
                    await page.get_by_role('button', name='Start recording', exact=True).click()
                    await asyncio.sleep(1.2)
                    await page.locator('#receiver-frequency').fill(str(int(await page.locator('#receiver-frequency').input_value()) + 10))
                    await page.locator('#receiver-frequency').press('Tab')
                    await asyncio.sleep(.4)
                    await page.get_by_role('button', name='Stop recording', exact=True).click()
                    await page.get_by_role('link', name='Download audio', exact=True).wait_for()
                    async with page.expect_download() as download:
                        await page.get_by_role('link', name='Download audio', exact=True).click()
                    audio_path = await (await download.value).path()
                    audio = audio_path.read_bytes()
                    assert len(audio) > 1000 and audio[:4] in [b'\x1aE\xdf\xa3', b'OggS', b'\0\0\0\x20']
                    decoded = await page.evaluate('''async url => {
                        const context = new AudioContext();
                        try { const buffer = await context.decodeAudioData(await (await fetch(url)).arrayBuffer());
                            const data = buffer.getChannelData(0); let peak=0;
                            for (const value of data) peak=Math.max(peak,Math.abs(value));
                            return {duration:buffer.duration,peak}; }
                        finally {await context.close();}
                    }''', await page.get_by_role('link', name='Download audio').get_attribute('href'))
                    assert decoded['duration'] > 1 and decoded['peak'] > .1, decoded
                    metadata = await page.evaluate('async url => (await fetch(url)).json()',
                        await page.get_by_role('link', name='Download metadata').get_attribute('href'))
                    assert metadata['volumeIndependent'] and metadata['sampleRateHz'] == 48000
                    assert metadata['events'][0]['mode'] == 'CW' and metadata['events'][0]['cwPitchHz'] == 1200
                    assert len({e['frequencyHz'] for e in metadata['events']}) >= 2
                    await page.get_by_role('button', name='Start recording', exact=True).click()
                    await asyncio.sleep(.4)
                    await page.get_by_role('button', name='STOP AUDIO', exact=True).click()
                    await page.get_by_role('link', name='Download metadata').wait_for()
                    metadata = await page.evaluate('async url => (await fetch(url)).json()',
                        await page.get_by_role('link', name='Download metadata').get_attribute('href'))
                    assert metadata['stopReason'] == 'audio stopped'
                    await page.locator('h1').click()
                    await page.keyboard.press('ArrowRight')
                    next_frequency = int(await page.locator('#receiver-frequency').input_value())
                    await page.locator('#receiver-frequency').focus()
                    await page.keyboard.press('b')
                    assert await page.locator('.bookmark-row').count() == 0
                    await page.locator('h1').click()
                    await page.keyboard.press('b')
                    assert await page.locator('.bookmark-row').count() == 1
                    await page.keyboard.press('Shift+ArrowLeft')
                    assert int(await page.locator('#receiver-frequency').input_value()) == next_frequency - 1000
                    assert sent == [], 'Full-band controls left the browser'
                    assert errors == [], errors
                    await page.screenshot(path='/tmp/websdr-receiver-tools.png', full_page=True)
                    # An obsolete, failed WASM load must not tear down a newer session.
                    race = await browser.new_page()
                    requests = 0
                    async def delayed_module(route):
                        nonlocal requests
                        requests += 1
                        if requests == 1:
                            await asyncio.sleep(.8)
                            try: await route.fulfill(status=404, body='obsolete request')
                            except Exception: pass  # The old fetch was explicitly aborted.
                        else:
                            await route.fulfill(path=ROOT/'frontend/dev/src/public/dsp.wasm', content_type='application/wasm')
                    await race.route('**/dsp.wasm', delayed_module)
                    await race.goto(origin+'/sdr')
                    await race.get_by_text('LOADING DSP...', exact=True).wait_for()
                    await race.get_by_role('button', name='Disconnect', exact=True).click()
                    await race.get_by_role('button', name='Connect', exact=True).click()
                    await race.get_by_text('CONNECTED', exact=True).wait_for()
                    await asyncio.sleep(1)
                    assert await race.get_by_text('CONNECTED', exact=True).count() == 1
                    assert await race.get_by_text('DSP UNAVAILABLE', exact=True).count() == 0
                    assert requests == 2
                    await race.close()
                    await browser.close()
        finally:
            source.terminate(); source.wait(timeout=10)
            if server is not None: server.terminate(); server.wait(timeout=5)
