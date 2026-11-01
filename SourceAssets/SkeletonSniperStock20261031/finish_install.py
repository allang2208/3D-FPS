"""Run after the ordinary Editor DLL build; keep native arm topology intact."""
import unreal as u,json,shutil,copy
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]
if not json.loads((O/'install_receipt.json').read_text())['complete']:raise RuntimeError('Finish stock asset import first')
# The SVD FBX import reported near-zero exported tangents. Preserve its vertex
# normals and UVs, and derive the tangent basis with the engine's built-in solver.
svd=u.load_asset('/Game/Weapons/SkeletonSniperStock20261031/Meshes/SM_SniperSkeleton_SVD')
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
settings=sub.get_lod_build_settings(svd,0);settings.recompute_tangents=True;settings.use_mikk_t_space=False
sub.set_lod_build_settings(svd,0,settings)
if not u.EditorAssetLibrary.save_loaded_asset(svd,False):raise RuntimeError('SVD tangent basis not saved')
asset='/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9';mesh=u.load_asset(asset)
target=P/'Content/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9.uasset';backup=O/'Before/SK_M24_MotionV9.uasset'
if not backup.exists():shutil.copy2(target,backup)
centers=[u.Vector(*p) for p in json.loads((O/'Inputs/m24_factory_stock_faces.json').read_text())]
if not u.M24ChassisAssetTools.split_factory_stock(mesh,centers):raise RuntimeError('Factory stock partition could not be authored')
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Factory stock partition not saved')
path=P/'Content/ColdSteelData/gunsmith.json';raw=path.read_bytes();data=json.loads(raw)
option=dict(id='sniper_skeleton_stock',name='骨架狙击枪托',description='镂空金属托架配可调贴腮板、调节轮与橡胶肩垫，按各枪型连接端独立适配。',stats={'recoil_mult':.85,'stability_mult':1.2,'ads_percent':.05},effects=[{'text':'后坐力-15%','benefit':1},{'text':'稳定性+20%','benefit':1},{'text':'开镜耗时+5%','benefit':-1}])
for row in data['weapons']:
    if row['id'] not in ('ue_m24','ue_svd','ue_svch'):continue
    options=row['options'].setdefault('stock',[]);options[:]=[v for v in options if v['id']!=option['id']];options.append(copy.deepcopy(option))
    if 'stock' not in row['allowed']:row['allowed'].append('stock')
    if row['id']=='ue_m24':
        factory=next(v for v in options if v['id']=='m24_cheekrest');factory['name']='M24 原装枪托';factory['description']='原装后托与贴腮板，保持原有肩托和握持轮廓。'
    if row['id']=='ue_svch':
        factory=next(v for v in options if v['id']=='false');factory['name']='SVCH 原装枪托';factory['description']='恢复 SVCH 原装后托、贴腮面与肩垫。'
backup=O/'Before/gunsmith.json'
if not backup.exists():backup.write_bytes(raw)
if path.read_bytes()!=raw:raise RuntimeError('Catalog changed during publication; original retained')
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'delivery.json').write_text(json.dumps(dict(complete=True,id=option['id'],weapons=['ue_m24','ue_svd','ue_svch'],host=asset,host_saved=True,animations_changed=False,runtime_tested=False,editor_opened=False),indent=2))
print('SKELETON_SNIPER_CATALOG_AND_NATIVE_SECTION_SAVED')
