"""Run scoped authoring jobs in the offscreen map copy; use the saved cart camera."""
from pathlib import Path
import json,runpy,time,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'FreightCameraMatch20261113'
ctx=runpy.run_path(str(BASE/'capture.py'))
photo=ctx['take']
photo.__globals__['ROOT']=ROOT
photo.__globals__['LABELS']=('REF_02_CartSurface',)
if Path(u.Paths.project_dir()).resolve()!=(ROOT/'RenderHost').resolve():raise RuntimeError('Unexpected project')
w,_=ctx['open_world']()
(ROOT/'ready.json').write_text(json.dumps(w.get_path_name()),'utf8')
for step in range(1,16):
    job=ROOT/('job-%02d.json'%step);start=time.monotonic()
    while not job.is_file() and time.monotonic()-start<1800:time.sleep(.5)
    if not job.exists():break
    row=json.loads(job.read_text('utf-8-sig'))
    if row.get('finish'):break
    try:
        if row.get('script'):runpy.run_path(str(ROOT/row['script']))['apply'](w,row)
        if row.get('capture'):photo(w,row['capture'])
        if row.get('save') and not u.EditorLoadingAndSavingUtils.save_map(w,ctx['TARGET']):raise RuntimeError('Map package not saved')
        (ROOT/('done-%02d.json'%step)).write_text(json.dumps(row),'utf8')
    except Exception:(ROOT/('error-%02d.txt'%step)).write_text(traceback.format_exc(),'utf8')
