"""Resume only the two subject saves after the production map has been saved."""
from pathlib import Path
import json,runpy
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
R=runpy.run_path(str(ROOT/'recipe.py'))
save=runpy.run_path(str(PROJECT/'SourceAssets/ReceptionCoverage20261009/install.py'))['save']
path=ROOT/'Receipts/install.json';report=json.loads(path.read_text('utf8'))
if report['stage']!='production_saved':raise RuntimeError('Unexpected resume stage')
for target in R['SUBJECTS']:
    if any(m['path']==target and m.get('saved') for m in report['maps']):continue
    world=u.EditorLoadingAndSavingUtils.load_map(target)
    changes=R['apply_subject'](world);save(world,target)
    report['maps'].append(dict(path=target,saved=True,changes=changes))
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
report['stage']='maps_saved';report.pop('error',None)
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('TRANSIT_EQUIPMENT_SUBJECTS_SAVED',len(report['maps']))
