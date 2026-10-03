import asyncio
import os
import subprocess
import sys
from pathlib import Path
import httpx
import pytest
from playwright.async_api import async_playwright
from tests.test_backend import backend, free_port

ROOT=Path(__file__).resolve().parents[1]

AUDIO_MONITOR='''(() => {
  window.__audio={created:0,closed:0,starts:0,gains:[],peaks:[]};
  const Original=window.AudioContext;
  window.AudioContext=class extends Original {
    constructor(options){super(options);window.__audio.created++;}
    createGain(){const gain=super.createGain();const set=gain.gain.setTargetAtTime.bind(gain.gain);
      gain.gain.setTargetAtTime=(value,...rest)=>{window.__audio.gains.push(value);return set(value,...rest)};return gain;}
    createBufferSource(){const source=super.createBufferSource();const start=source.start.bind(source);
      source.start=(...args)=>{window.__audio.starts++;const pcm=source.buffer?.getChannelData(0);
        if(pcm)window.__audio.peaks.push(Math.max(...pcm.map(Math.abs)));return start(...args)};return source;}
    close(){window.__audio.closed++;return super.close();}
  };
})();'''

def source_process(port,log):
    env={**os.environ,'PYTHONPATH':os.pathsep.join(str(ROOT/p) for p in ['shared','sdr-server'])}
    return subprocess.Popen([sys.executable,str(ROOT/'tools/synthetic_iq.py'),
        '--address',f'tcp://127.0.0.1:{port}'],env=env,stdout=log,stderr=log)

@pytest.mark.asyncio
async def test_production_browser_receiver_audio_local_tune_and_source_recovery(tmp_path):
    source_port,web_port,backend_port=free_port(),free_port(),free_port()
    log=(tmp_path/'browser-services.log').open('w')
    source=source_process(source_port,log)
    server=None
    try:
        async with backend(backend_port,source_port,tmp_path) as receiver:
            server=subprocess.Popen([sys.executable,str(ROOT/'tests/serve_frontend.py'),
                '--port',str(web_port),'--backend',receiver],stdout=log,stderr=log)
            async with httpx.AsyncClient() as http:
                for _ in range(100):
                    try:
                        if (await http.get(f'http://127.0.0.1:{web_port}/config.yaml')).status_code==200:break
                    except httpx.ConnectError:pass
                    await asyncio.sleep(.05)
            async with async_playwright() as playwright:
                browser=await playwright.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH','/usr/bin/google-chrome'),headless=True,
                    args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'])
                page=await browser.new_page(viewport={'width':1280,'height':900})
                errors=[];sent=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('websocket',lambda ws:ws.on('framesent',lambda frame:sent.append(frame)))
                await page.add_init_script(AUDIO_MONITOR)
                await page.goto(f'http://127.0.0.1:{web_port}/sdr')
                try:
                    await page.get_by_role('button',name='START AUDIO').wait_for(timeout=10000)
                except Exception:
                    await page.screenshot(path='/tmp/websdr-browser-failure.png', full_page=True)
                    raise AssertionError({'errors': errors, 'body': await page.locator('body').inner_text()})
                await page.wait_for_function("document.querySelector('button') && document.body.innerText.includes('CONNECTED')")
                await page.wait_for_function('''() => {
                    const canvas=document.querySelector('.waterfall-area canvas');if(!canvas)return false;
                    const data=canvas.getContext('2d').getImageData(0,0,canvas.width,Math.min(60,canvas.height)).data;
                    let low=765,high=0;
                    for(let i=0;i<data.length;i+=4){const value=data[i]+data[i+1]+data[i+2];
                        low=Math.min(low,value);high=Math.max(high,value);}
                    return high-low>120;
                }''')
                await page.get_by_role('button',name='START AUDIO').click()
                await page.get_by_role('button',name='STOP AUDIO').wait_for()
                await page.wait_for_function('window.__audio.starts > 10')
                assert await page.evaluate('window.__audio.peaks.some(x=>x>0.1)')
                await page.locator('#receiver-frequency').fill('10489730000')
                await page.locator('#receiver-frequency').press('Tab')
                await page.locator('[aria-label="Sideband"]').select_option('-1')
                await page.locator('#receiver-frequency').fill('10489680000')
                await page.locator('#receiver-frequency').press('Tab')
                ruler='document.querySelector("canvas.ruler").toDataURL()'
                await page.locator('.waterfall-area').scroll_into_view_if_needed()
                await page.screenshot(path='/tmp/websdr-console-desktop.png', full_page=True)
                before=await page.evaluate(ruler)
                waterfall=await page.locator('.waterfall-area canvas').first.bounding_box()
                x=waterfall['x']+waterfall['width']/2
                y=waterfall['y']+waterfall['height']/2
                await page.mouse.move(x,y)
                await page.mouse.wheel(0,-600)
                await page.wait_for_function(f'{ruler} !== '+repr(before))
                before=await page.evaluate(ruler)
                await page.mouse.down();await page.mouse.move(x+30,y);await page.mouse.up()
                await page.wait_for_function(f'{ruler} !== '+repr(before))
                await page.get_by_role('combobox',name='Palette').select_option('inferno')
                await page.get_by_role('slider',name='Volume').press('Home')
                await page.wait_for_function('window.__audio.gains.includes(0)')
                assert sent==[], 'Browser sent remote tuning/control frames'
                starts=await page.evaluate('window.__audio.starts')
                source.terminate();source.wait(timeout=5)
                source=source_process(source_port,log)
                await page.wait_for_function(f'window.__audio.starts > {starts+10}')
                await page.screenshot(path='/tmp/websdr-browser.png')
                await page.get_by_role('button',name='STOP AUDIO').click()
                await page.wait_for_function('window.__audio.closed === window.__audio.created')
                await page.get_by_role('button',name='START AUDIO').click()
                await page.get_by_role('button',name='STOP AUDIO').wait_for()
                await page.get_by_role('button',name='Disconnect',exact=True).click()
                await page.wait_for_function('window.__audio.closed === window.__audio.created')
                # Delay native resume to exercise rapid cancellation and a new session
                # while earlier starts are still awaiting browser permission/resume.
                await page.evaluate('''() => {
                    const Previous=window.AudioContext;
                    window.AudioContext=class extends Previous {
                        resumed=false;
                        get state(){const state=super.state;
                            return state==='closed'||this.resumed?state:'suspended';}
                        async resume(){await new Promise(resolve=>setTimeout(resolve,800));
                            await super.resume();this.resumed=true;}
                    };
                }''')
                await page.get_by_role('button',name='Connect',exact=True).click()
                await page.get_by_text('CONNECTED',exact=True).wait_for()
                await page.get_by_role('button',name='START AUDIO').click()
                await page.get_by_role('button',name='START AUDIO').click()
                await page.wait_for_function('window.__audio.closed === window.__audio.created')
                await page.get_by_role('button',name='START AUDIO').click()
                await page.get_by_role('button',name='Disconnect',exact=True).click()
                await page.get_by_role('button',name='Connect',exact=True).click()
                await page.get_by_text('CONNECTED',exact=True).wait_for()
                await page.get_by_role('button',name='START AUDIO').click()
                await page.get_by_role('button',name='STOP AUDIO').wait_for()
                assert await page.get_by_text('Audio unavailable',exact=True).count()==0
                await page.get_by_role('button',name='Disconnect',exact=True).click()
                await page.wait_for_function('window.__audio.closed === window.__audio.created')
                async with httpx.AsyncClient() as http:
                    for _ in range(20):
                        if (await http.get(receiver+'/stream-info')).json()['clients']==0:break
                        await asyncio.sleep(.1)
                    assert (await http.get(receiver+'/stream-info')).json()['clients']==0
                assert errors==[], errors
                failure=await browser.new_page()
                await failure.route('**/dsp.wasm',lambda route:route.fulfill(status=404,body='missing'))
                await failure.goto(f'http://127.0.0.1:{web_port}/sdr')
                await failure.get_by_text('DSP UNAVAILABLE',exact=True).wait_for()
                await browser.close()
    finally:
        source.terminate();source.wait(timeout=5)
        if server:server.terminate();server.wait(timeout=5)
        log.close()
