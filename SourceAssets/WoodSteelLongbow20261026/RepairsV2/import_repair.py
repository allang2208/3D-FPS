"""Save the two linen finishes and three repaired meshes through the UE batch gate."""
from pathlib import Path
import json,sys,re,hashlib,shutil
import unreal as u
R=Path(__file__).parent;P=R.parent;sys.path.insert(0,str(P))
from linen_materials import build_linen
DEST='/Game/Weapons/WoodSteelLongbow20261026'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
names=['M_WoodSteelLongbow_Linen_Static','M_WoodSteelLongbow_WaxedLinen_Static',
       'SM_WoodSteelLongbow_Grip_Linen','SM_WoodSteelLongbow_Optic2x','SM_WoodSteelLongbow_Optic4x']
dirty={x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(DEST+'/'+n for n in names):raise RuntimeError('Preserving unsaved target assets')
backup=R/'Before-UE';backup.mkdir(exist_ok=True)
for name in names:
    source=Path('D:/FPS3D/FPSGAME/Content/Weapons/WoodSteelLongbow20261026')/(name+'.uasset')
    if source.exists() and not (backup/source.name).exists():shutil.copy2(source,backup/source.name)
r={'saved':{},'bindings':{},'sources':{},'gameplay_tested':False}
def save(asset,source=None):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed '+asset.get_path_name())
    r['saved'][asset.get_name()]=asset.get_path_name()
    if source:r['sources'][asset.get_name()]=hashlib.sha256(source.read_bytes()).hexdigest()
    (R/'import-receipt.json').write_text(json.dumps(r,indent=2),encoding='utf8')
    print('WOODSTEEL_REPAIR_SAVED '+asset.get_path_name(),flush=True)
for name in names[:2]:
    m=u.load_asset(DEST+'/'+name) if E.does_asset_exist(DEST+'/'+name) else A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    build_linen(m,'Waxed' in name);save(m)

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for name in names[2:]:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_animations=False
    opt.import_materials=False;opt.import_textures=False
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    source=P/'Export'/(name+'.fbx')
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False;task.options=opt
    A.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name)
    if not mesh:raise RuntimeError('Mesh import failed '+name)
    slots=list(mesh.get_editor_property('static_materials'))
    for i,slot in enumerate(slots):
        material=re.sub(r'_\d{3}$','',str(slot.material_slot_name))
        if material.startswith('M_BowOptic_'):path='/Game/Weapons/DarkBow20260925/SingleLensOptics20260927/'+material
        elif material in ['M_WoodSteelLongbow_Linen','M_WoodSteelLongbow_Steel']:path=DEST+'/'+material+'_Static'
        else:raise RuntimeError('Unexpected mesh material '+material)
        asset=u.load_asset(path)
        if not asset:raise RuntimeError('Missing mesh material '+path)
        slot.material_interface=asset;slots[i]=slot
    mesh.set_editor_property('static_materials',slots)
    r['bindings'][name]=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in mesh.get_editor_property('static_materials')]
    save(mesh,source)
r['complete']=True
(R/'import-receipt.json').write_text(json.dumps(r,indent=2),encoding='utf8')
# The original resumable importer must recognize these newly exported sources.
old=json.loads((P/'import-receipt.json').read_text(encoding='utf8'))
for field in ('saved','sources'):old[field].update(r[field])
(P/'import-receipt.json').write_text(json.dumps(old,indent=2),encoding='utf8')
print('WOODSTEEL_REPAIR_COMPLETE 5')
