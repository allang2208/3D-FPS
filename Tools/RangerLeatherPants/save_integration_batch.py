"""Save one heavy wearable per batch; release its memory when the process exits."""
import gc,hashlib,importlib.util,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent))
from integration_common import *
from integration_materials import create,save
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End PIE before saving the new trousers')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    authored=read(R/'authored.json')
    if not authored.get('completed'):raise RuntimeError('Finish integration authoring')
    materials=create();io=module('ranger_v3_native_writer','Tools/GarmentSleeveRepair/save_assets.py');io.R=R;io.DEST=DEST;io.receipt_path=R/'saved_assets.json';io.receipt=read(io.receipt_path) if io.receipt_path.exists() else dict(saved={},runtime_tested=False)
    io.receipt['completed']=False;io.record()
    for row in authored['records']:
        key=row['item']+'/'+row['profile'];old=io.receipt['saved'].get(key)
        if old and old['author_sha256']==row['author_sha256'] and E.does_asset_exist(old['asset']):continue
        if hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()!=row['author_sha256']:raise RuntimeError('Author changed '+key)
        d=read(row['file'])
        if row['item']=='ue_leather_pants':mats=materials['robe_materials'] if row['profile'].endswith('_RobeInner') else materials['materials']
        else:
            recipe=read(R/'baseline.json')['items']['ue_field_sweater'];source=recipe['owner_body_meshes']['Jason'] if row['profile']=='Owner_Jason' else recipe['rig_meshes']['Jason'];asset=u.load_asset(source)
            mats=[m.material_interface.get_path_name() for m in asset.materials]
        desc=R/'SaveInputs'/(row['profile']+'_'+row['item']+'.json');write(desc,dict(materials=mats,material_slots=d['material_slots']));del d;gc.collect()
        io.write_mesh(dict(item=row['item'],profile=row['profile'],file=str(desc)))
        asset=u.load_asset(io.receipt['saved'][key]['asset']);s=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
        for lod in range(s.get_lod_count(asset)):
            build=s.get_lod_build_settings(asset,lod);build.set_editor_property('use_full_precision_u_vs',True);s.set_lod_build_settings(asset,lod,build)
        save(asset);print('RANGER_V3_BATCH_WEARABLE',key,flush=True);return
    # Icon and pickup share current geometry, material slots and vertex finish.
    displays=io.receipt.setdefault('displays',{})
    for kind in ('icon','pickup'):
        if displays.get(kind) and E.does_asset_exist(displays[kind]):continue
        source=u.load_asset(io.receipt['saved']['ue_leather_pants/Jason']['asset']);dm,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Display geometry copy failed')
        T=u.GeometryScript_MeshTransforms
        if kind=='icon':T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=180,roll=0))
        else:
            d=read(SOURCE/'Authored/ue_leather_pants/Jason.json');center=[(min(p[i] for p in d['positions'])+max(p[i] for p in d['positions']))*.5 for i in range(3)];del d;gc.collect()
            T.translate_mesh(dm,u.Vector(*[-v for v in center]));T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=0,roll=-90))
        static=module('ranger_v3_static_writer','Tools/ChainmailPants/save_assets.py');static.DEST=DEST
        path=DEST+('/Icons/SM_RangerLeatherPants_Display' if kind=='icon' else '/Pickups/SM_RangerLeatherPants')
        displays[kind]=static.static(dm,path,[u.load_asset(p) for p in materials['materials']]);io.record();print('RANGER_V3_DISPLAY_SAVED',kind,flush=True);return
    if not io.receipt.get('icon_texture'):
        icon=read(R/'icon_source.json');t=u.AssetImportTask();t.filename=icon['icon'];t.destination_path='/Game/ColdSteelData/Icons/RangerLeatherPantsRealisticCutV3';t.destination_name='ue_leather_pants';t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+t.destination_name)
        for k,v in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():tex.set_editor_property(k,v)
        tex.modify()
        if not E.save_loaded_asset(tex,False):raise RuntimeError('Cannot save inventory thumbnail')
        io.receipt['icon_texture']=tex.get_path_name()
    # UE normalizes generated section metadata on first package reload. Persist
    # that import fixup after the isolated mesh-building processes have exited.
    for row in authored['records']:
        asset=u.load_asset(io.receipt['saved'][row['item']+'/'+row['profile']]['asset'])
        save(asset);asset=None;gc.collect();u.SystemLibrary.collect_garbage()
    io.receipt.update(completed=True,geometry_assets=8,display_assets=2,materials=materials['materials'],robe_materials=materials['robe_materials'],runtime_tested=False);io.record();print('RANGER_V3_ALL_ASSETS_SAVED',flush=True)
main()
