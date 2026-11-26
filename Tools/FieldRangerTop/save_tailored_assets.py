"""Save detailed bodies plus material-only native FP shirt variants."""
import gc,importlib.util,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerTop20261020/TailoredFinish20261021';KEY='ue_field_sweater'
DEST='/Game/Characters/ModularOutfit20260924/FieldRangerTop20261020/TailoredFinish20261021'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def module(name,path):
    s=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('End play before saving tailored shirt assets')
manifest=read(R/'authored.json');inputs=read(R/'inputs.json')
materials=module('tailored_shirt_materials','Tools/FieldRangerTop/tailored_materials.py');base=materials.create();revision=read(R/'materials.json')['revision']
io=module('tailored_native_io','Tools/GarmentSleeveRepair/save_assets.py');io.R=R;io.DEST=DEST;io.receipt_path=R/'saved_assets.json'
io.receipt=read(io.receipt_path) if io.receipt_path.exists() else dict(saved={},runtime_tested=False)
io.receipt['completed']=False;io.record()
for row in manifest['records']:
    d=read(Path(row['authored']));mats=base+[base[2]]
    if row['profile']=='Body':mats[-1]=u.load_asset(d['binding_source']).materials[4].material_interface
    if row['profile']=='Owner_Jason':mats+=mats
    desc=R/'SaveInputs'/(row['profile']+'.json');desc.write_text(json.dumps(dict(materials=[m.get_path_name() for m in mats],material_slots=d['material_slots'])),encoding='utf-8')
    io.write_mesh(dict(profile=row['profile'],item=KEY,file=str(desc)));del d;gc.collect();u.SystemLibrary.collect_garbage()
for profile,source_path in inputs['recipe']['rig_meshes'].items():
    if profile in ('Body','Jason'):continue
    path=DEST+'/'+KEY+'/'+profile+'/SK_'+profile+'_'+KEY;asset=u.load_asset(path)
    if not asset:asset=u.AssetToolsHelpers.get_asset_tools().duplicate_asset(path.rsplit('/',1)[1],path.rsplit('/',1)[0],u.load_asset(source_path))
    slots=list(asset.materials)
    for i,material in enumerate(base):slots[i].set_editor_property('material_interface',material)
    asset.set_editor_property('materials',slots)
    u.EditorAssetLibrary.set_metadata_tag(asset,'TailoredFinishMaterialRevision',revision);u.EditorAssetLibrary.set_metadata_tag(asset,'TailoredFinishNativeSource',source_path);io.save(asset)
    io.receipt['saved'][KEY+'/'+profile]=dict(asset=asset.get_path_name(),native=source_path,material_revision=revision,geometry_unchanged=True,lod_count=io.S.get_lod_count(asset));io.record()
    print('TAILORED_FP_MATERIAL_SAVED',profile,flush=True);u.SystemLibrary.collect_garbage()
io.receipt.update(completed=True,body_profiles=3,material_only_profiles=len(inputs['recipe']['rig_meshes'])-2,materials_revision=revision);io.record()
print('TAILORED_ASSETS_SAVED',len(io.receipt['saved']),flush=True)
