from pathlib import Path
import json,ast,sys,hashlib
import unreal as u
W=Path('F:/FPSGAME-Recovery-Work-20261120/HighlandClaymoreJunction20261121')
project=Path('D:/FPS3D/FPSGAME')
job=json.loads((W/'job.json').read_bytes())
source=project/'SourceAssets/HighlandClaymoreMeshy20260922'
P=source/'WedgeSpineJunctionR4_20261106'
spec=json.loads((P/'authoring.json').read_bytes())
target=package=job['blade']
broad=project/'SourceAssets/HighlandBroadbladeGuardFinish20261106'
sys.path.insert(0,str(broad))
from seat_finish import native_protection,REVISION
L=u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
static=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
mesh=u.load_asset(target)
if mesh is None:raise RuntimeError('Missing existing ridge mesh')
result={}
def save(asset,source_info):
    if not L.save_loaded_asset(asset,False):raise RuntimeError(asset.get_path_name())
    result[asset.get_path_name().split('.')[0]]=source_info
# Keep the original reimporter's FBX settings, existing LOD setup and material rebinding.
script=source/'RidgePiercerRootV2_20260927/import_ridge_piercer_root_v2.py'
txt=script.read_text(encoding='utf-8')
start=txt.index('materials={');end=txt.index('shutil.copy2(Path(spec.get')
exec(compile(txt[start:end],str(script),'exec'))
for path in job['mats']:
    mat=u.load_asset(path)
    masks=[n for n in u.MaterialEditingLibrary.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='BroadbladeGuardFinish20261106R1 gem and bezel preservation']
    if len(masks)!=1:raise RuntimeError('Unexpected seat graph '+path)
    masks[0].set_editor_property('code',native_protection(mat))
    errors=u.MaterialEditingLibrary.recompile_material(mat)
    if errors:raise RuntimeError(str(errors))
    L.set_metadata_tag(mat,'HighlandSeatFinish',REVISION)
    save(mat,'HighlandBroadbladeSeat20261107, native_protection')
data=json.loads((broad/'inputs.json').read_bytes())['guards']['highland_cloven_guard']
obj=L.duplicate_asset(data['mesh'].split('.')[0],job['cloven'])
if obj is None:raise RuntimeError('Cannot duplicate current cloven donor')
links={r['slot']:r['material'].split('.')[0] for r in data['slots']}
used={}
for i,slot in enumerate(obj.static_materials):
    name=str(slot.material_slot_name)
    original=links[name]
    ref=original if name=='M_Cloven_Inlay' else job['mats'][next(idx for idx,k in enumerate(job['mats']) if k.rsplit('/',1)[1]=='M_BroadbladeGuard_'+original.rsplit('/',1)[1].removeprefix('M_'))]
    bound=u.load_asset(ref)
    if not bound:raise RuntimeError('Missing '+ref)
    obj.set_material(i,bound)
    used[name]=ref
if set(used)!=set(links):raise RuntimeError('Incomplete cloven slots')
L.set_metadata_tag(obj,'BroadbladeGuardFinishRevision','BroadbladeGuardFinish20261106R1')
L.set_metadata_tag(obj,'BroadbladeGuardSource',data['mesh'])
save(obj,dict(donor=data['mesh'],slots=used))
if set(result)!=set(job['targets']):raise RuntimeError('Incomplete save batch')
(W/'saved.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
u.log('HIGHLAND_JUNCTION_RECOVERY_SAVED '+str(len(result)))
