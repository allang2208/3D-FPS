"""Save both fitted caps, authored LODs, original PBR, pickup and inventory assets."""
import gc
import hashlib
import importlib.util
import json
import types
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SportsCap20261024';DEST='/Game/Characters/ModularOutfit20260924/SportsCap20261024'
KEY='ue_charcoal_sports_cap';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
S=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):Path(p).write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def save(asset):
    if not asset.get_path_name().startswith(DEST+'/'):raise RuntimeError('Outside sports cap asset scope')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+asset.get_path_name())
def record():write(R/'saved_assets.json',receipt)

if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Do not save sports cap assets during PIE')
delivery=read(R/'delivery.json')
if not delivery['completed']:raise RuntimeError('Finish authored LOD and inventory production first')
receipt=read(R/'saved_assets.json') if (R/'saved_assets.json').exists() else dict(completed=False,runtime_tested=False,wear={})
receipt['completed']=False;record()

# Reuse the established cloth/PBR construction, with this cap's native normal
# strength and restrained nylon fuzz. All destinations are isolated to this cap.
code=(P/'Tools/ST6Beret/save_assets.py').read_text(encoding='utf-8').split("if '-run='",1)[0]
code=code.replace('(.65,.65,1)','(1.,1.,1.)').replace('scalar(.28)','scalar(row.get("fuzz",.10))')
m=types.ModuleType('sports_cap_pbr_writer');exec(compile(code,'sports_cap_pbr_writer','exec'),m.__dict__);m.P=P;m.R=R;m.DEST=DEST
fingerprint=hashlib.sha256((sha(R/'materials.json')+code+''.join(sha(p) for p in sorted((R/'Textures').glob('*.png')))).encode()).hexdigest()
mat_receipt=read(R/'materials_saved.json') if (R/'materials_saved.json').exists() else {}
if mat_receipt.get('fingerprint')==fingerprint:
    mats=[m.load(path) for path in mat_receipt['materials']]
else:
    textures=m.textures();mats=[m.material(row,textures) for row in read(R/'materials.json')]
    mat_receipt=dict(completed=True,fingerprint=fingerprint,materials=[a.get_path_name() for a in mats],textures={k:v.get_path_name() for k,v in textures.items()})
    write(R/'materials_saved.json',mat_receipt)
receipt['materials']=mat_receipt['materials'];receipt['textures']=mat_receipt['textures'];record()
io=module('sports_cap_dynamic','Tools/FieldHat/save_icon.py')
slot_names=[row['name'] for row in read(R/'materials.json')]

def static_lods(rows,path,offset=None,icon=False):
    asset=u.load_asset(path)
    for lod,row in enumerate(rows):
        d=read(row['file']);dm=io.dynamic(d)
        if offset:u.GeometryScript_MeshTransforms.translate_mesh(dm,u.Vector(*offset))
        if icon:u.GeometryScript_MeshTransforms.inverse_transform_mesh(dm,u.Transform(rotation=u.Rotator(pitch=0,yaw=-90,roll=0)))
        if asset is None:
            asset,status=u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,enable_collision=False))
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Create failed '+path)
            asset.set_editor_property('static_materials',[u.StaticMaterial(material_interface=mat,material_slot_name=name) for mat,name in zip(mats,slot_names)])
        else:
            options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,replace_materials=True,new_materials=mats,new_material_slot_names=slot_names)
            _,status=G.copy_mesh_to_static_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD(lod_index=lod))
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('LOD write failed '+path+' '+str(lod))
        build=S.get_lod_build_settings(asset,lod);build.set_editor_property('use_full_precision_u_vs',True);S.set_lod_build_settings(asset,lod,build)
        del dm,d;gc.collect()
    if not S.set_lod_screen_sizes(asset,[1.,.18,.07][:len(rows)]):raise RuntimeError('LOD screen sizes not applied '+path)
    E.set_metadata_tag(asset,'EquipmentDefinition',KEY);E.set_metadata_tag(asset,'SportsCapRevision','20261024-authored-lods-v1')
    save(asset)
    return dict(asset=asset.get_path_name(),lod_source_hashes=[sha(row['file']) for row in rows],authored_triangles=[row.get('triangles') for row in rows],lod_count=len(rows))

by_body={row['body']:row['lods'] for row in delivery['records']}
for body,rows in by_body.items():
    old=receipt['wear'].get(body,{})
    if old.get('lod_source_hashes')!=[sha(row['file']) for row in rows]:
        receipt['wear'][body]=static_lods(rows,DEST+'/Wear/SM_SportsCap_'+body);record()
        print('SPORTS_CAP_WEAR_SAVED',body,flush=True)
    u.SystemLibrary.collect_garbage()
rows=by_body['Jason'];source=read(rows[0]['file']);offset=[-(min(p[i] for p in source['positions'])+max(p[i] for p in source['positions']))*.5 for i in range(3)];del source
if receipt.get('pickup',{}).get('lod_source_hashes')!=[sha(row['file']) for row in rows]:
    receipt['pickup']=static_lods(rows,DEST+'/Pickups/SM_SportsCap_Pickup',offset);record()
display=R/(KEY+'-display.json')
if receipt.get('icon',{}).get('lod_source_hashes')!=[sha(display)]:
    receipt['icon']=static_lods([dict(file=str(display))],DEST+'/Icons/SM_SportsCap_Icon',icon=True);record()
task=u.AssetImportTask();task.filename=str(R/(KEY+'.png'));task.destination_path=DEST+'/Icons';task.destination_name='T_SportsCap_Icon';task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task]);texture=m.load(DEST+'/Icons/T_SportsCap_Icon')
for prop,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():texture.set_editor_property(prop,value)
save(texture);receipt.update(completed=True,icon_texture=texture.get_path_name(),icon_sha256=sha(R/(KEY+'.png')),fits=read(R/'fit_candidate.json'),attachment='Existing static head-bone follower; independent native-head meshes; keep scalp hair visible')
record();print('SPORTS_CAP_ASSETS_SAVED',receipt['pickup']['asset'],flush=True)
