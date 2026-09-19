"""Temporary local build driver, stopped by a stop request or after 45 minutes."""
import unreal, json, time, traceback, runpy
from pathlib import Path
ROOT = Path(__file__).parent
last = None
started = time.monotonic()

def tick(delta):
    global last
    p = ROOT / 'request.json'
    if time.monotonic() - started > 2700:
        unreal.unregister_slate_post_tick_callback(handle)
        return
    if not p.exists():
        return
    req = json.loads(p.read_text(encoding='utf-8'))
    if req['id'] == last:
        return
    last = req['id']
    result = {'id': last}
    try:
        if req.get('stop'):
            unreal.unregister_slate_post_tick_callback(handle)
        else:
            target = (ROOT / req['script']).resolve()
            assert target.parent == ROOT.resolve()
            runpy.run_path(str(target), run_name='__main__')
        result['success'] = True
    except Exception:
        result['success'] = False
        result['error'] = traceback.format_exc()
        unreal.log_error(result['error'])
    (ROOT / 'response.json').write_text(json.dumps(result, indent=2), encoding='utf-8')

handle = unreal.register_slate_post_tick_callback(tick)
unreal.log('ARMS_IK_EDITOR_SESSION_READY')
