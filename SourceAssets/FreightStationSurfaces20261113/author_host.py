"""Scoped, unattended map editing on the saved station package."""
from pathlib import Path
import json,runpy,time,traceback
import unreal as u
ROOT=Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve()!=(ROOT/'RenderHost').resolve():raise RuntimeError('Unexpected project')
target='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject'
w=u.EditorLoadingAndSavingUtils.load_map(target)
if not w or w.get_path_name().split('.')[0]!=target:raise RuntimeError('Station map unavailable')
for step in range(1,14):
    job=ROOT/('job-%02d.json'%step);start=time.monotonic()
    while not job.exists() and time.monotonic()-start<2500:time.sleep(.5)
    if not job.exists():break
    row=json.loads(job.read_text('utf-8-sig'))
    if row.get('finish'):break
    try:
        result=runpy.run_path(str(ROOT/row['script']))['apply'](w)
        if row.get('save') and not u.EditorLoadingAndSavingUtils.save_map(w,target):raise RuntimeError('Cannot save station')
        (ROOT/('done-%02d.json'%step)).write_text(json.dumps(result,indent=1,ensure_ascii=False),'utf8')
    except Exception:(ROOT/('error-%02d.txt'%step)).write_text(traceback.format_exc(),'utf8')
