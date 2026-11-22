"""Polish only Time Sand mode 7 on the current rune-sword masters."""
# Apply the shared workbench copy standard when publishing catalogs.
from pathlib import Path as _WorkbenchCopyPath
import runpy as _workbench_copy_runpy
_workbench_copy_root = next(p for p in _WorkbenchCopyPath(__file__).resolve().parents if (p / 'FPSGAME.uproject').exists())
_apply_workbench_copy = _workbench_copy_runpy.run_path(str(_workbench_copy_root / 'SourceAssets/WorkbenchCopy20261101/copy_rules.py'))['apply_for_target']

from pathlib import Path
import runpy
import json, shutil
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;REV='TimeSandPolish20261101V2'
MASTERS=['/Game/Weapons/AzureRunesword20260913/M_AzureRunesword',
 '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/M_AzureRunesword_NativeGold']
if u.EditorLevelLibrary.get_pie_worlds(False):raise RuntimeError('PIE is running; preserve the current session.')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_path_name() in MASTERS:raise RuntimeError('Unsaved target package '+package.get_path_name())

apply_graph=runpy.run_path(str(P/'finish_graph.py'))['apply']
saved=[]
for path in MASTERS:
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Missing current master '+path)
    if E.get_metadata_tag(mat,'TimeSandPolishRevision')==REV:
        saved.append({'asset':path,'already_current':True});continue
    source=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=P/'BeforeAssets'/source.relative_to(ROOT/'Content');backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(source,backup)
    apply_graph(mat)
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Time Sand shader compilation failed '+str(errors))
    E.set_metadata_tag(mat,'TimeSandPolishRevision',REV)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Material save failed '+path)
    saved.append({'asset':path,'saved':True,'mode':7,'compile_errors':list(errors)})

appearance='符文长剑专属。香槟金剑面泛起细腻拉丝亮泽，精抛刃缘清亮，细砂在金属深处缓缓流动。'
for filename in ['melee-gunsmith.json','rune-sword-modules.json']:
    path=ROOT/'Content/ColdSteelData'/filename;before=path.read_bytes();data=json.loads(before.decode('utf-8-sig'))
    if filename=='melee-gunsmith.json':
        options=next(c for c in data['columns'] if c['key']=='blade_material')['options']
        next(o for o in options if o['id']=='time_sand_gold')['description']=appearance
    else:data['slots']['blade_material']['time_sand_gold']['appearance']=appearance
    backup=P/'BeforeCatalog'/filename;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if path.read_bytes()!=before:raise RuntimeError('Catalog changed during merge '+filename)
    path.write_text(json.dumps(_apply_workbench_copy(path, data),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(P/'material-receipt.json').write_text(json.dumps(_apply_workbench_copy(P/'material-receipt.json', {'revision':REV,'materials':saved,
    'gameplay_tested':False,'preview_rendered':False}),indent=2)+'\n',encoding='utf8')
print('TIME_SAND_POLISH_SAVED',json.dumps(saved))
