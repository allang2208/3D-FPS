"""Save one native wearable/display per shared editor batch, with resumable receipts."""
import gc,hashlib,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
from materials import create,save,module
from distance_lods import apply as apply_distance_lods
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
def main():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():raise RuntimeError('End PIE before saving boots')
    check=read(R/'model_check.json');file=R/'Authored/ue_leather_boots/Jason.json';sha=hashlib.sha256(file.read_bytes()).hexdigest()
    if not check.get('completed') or check['author_sha256']!=sha:raise RuntimeError('Current exported boot requires the requested model check')
    inputs=read(R/'inputs.json');original=P/'Content'/(inputs['source_asset'].split('.')[0][6:]+'.uasset')
    if hashlib.sha256(original.read_bytes()).hexdigest()!=inputs['source_asset_sha256']:raise RuntimeError('Source boot changed during authoring')
    surfaces=create();io=module('boot_native_writer','Tools/GarmentSleeveRepair/save_assets.py');io.R=R;io.DEST=DEST;io.receipt_path=R/'saved_assets.json';io.receipt=read(io.receipt_path) if io.receipt_path.exists() else dict(saved={},runtime_tested=False);io.receipt['completed']=False;io.record()
    for profile in ('Jason','Jason_RobeInner'):
        path=R/'Authored/ue_leather_boots'/(profile+'.json')
        if profile.endswith('RobeInner'):
            data=read(file);data['profile']=profile;data['material_slots']=['RobeStairHidden_'+str(i) for i in range(len(SLOTS))];data['contract']+='; robe inner retains complete geometry and masked hem shader';path.write_text(__import__('json').dumps(data,separators=(',',':')),encoding='utf-8');del data;gc.collect()
        author_sha=hashlib.sha256(path.read_bytes()).hexdigest();key='ue_leather_boots/'+profile;old=io.receipt['saved'].get(key)
        if old and old['author_sha256']==author_sha and E.does_asset_exist(old['asset']):apply_distance_lods(u.load_asset(old['asset']));continue
        mats=surfaces['robe_materials'] if profile.endswith('RobeInner') else surfaces['materials'];slots=['RobeStairHidden_'+str(i) for i in range(len(SLOTS))] if profile.endswith('RobeInner') else SLOTS
        desc=R/'SaveInputs'/(profile+'.json');write(desc,dict(materials=mats,material_slots=slots));io.write_mesh(dict(item='ue_leather_boots',profile=profile,file=str(desc)))
        mesh=u.load_asset(io.receipt['saved'][key]['asset']);sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
        for lod in range(sub.get_lod_count(mesh)):
            build=sub.get_lod_build_settings(mesh,lod);build.set_editor_property('use_full_precision_u_vs',True);sub.set_lod_build_settings(mesh,lod,build)
        E.set_metadata_tag(mesh,'EquipmentDefinition','ue_leather_boots');save(mesh);apply_distance_lods(mesh);print('LEATHER_BOOT_WEARABLE_SAVED',profile,flush=True);return
    displays=io.receipt.setdefault('displays',{})
    for kind in ('icon','pickup'):
        if displays.get(kind) and E.does_asset_exist(displays[kind]):continue
        source=u.load_asset(io.receipt['saved']['ue_leather_boots/Jason']['asset']);dm,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Display geometry copy failed')
        T=u.GeometryScript_MeshTransforms
        if kind=='icon':
            remove=[]
            for ti in range(dm.get_triangle_count()):
                valid,a,b,c=u.GeometryScript_MeshQueries.get_triangle_positions(dm,ti)
                if valid and a.x+b.x+c.x<0:remove.append(ti)
            u.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm,u.GeometryScript_List.convert_array_to_index_list(remove),False);T.rotate_mesh(dm,u.Rotator(pitch=0,yaw=150,roll=0));T.rotate_mesh(dm,u.Rotator(pitch=30,yaw=0,roll=0))
        else:
            data=read(file);center=[(min(p[i] for p in data['positions'])+max(p[i] for p in data['positions']))*.5 for i in range(3)];T.translate_mesh(dm,u.Vector(*[-v for v in center]));del data;gc.collect()
        static=module('boot_static_writer','Tools/ChainmailPants/save_assets.py');static.DEST=DEST;path=DEST+('/Icons/SM_LeatherBoots_Display' if kind=='icon' else '/Pickups/SM_LeatherBoots');displays[kind]=static.static(dm,path,[u.load_asset(p) for p in surfaces['materials']]);io.record();print('LEATHER_BOOT_DISPLAY_SAVED',kind,flush=True);return
    if not io.receipt.get('icon_texture'):
        t=u.AssetImportTask();t.filename=str(R/'ue_leather_boots.png');t.destination_path='/Game/ColdSteelData/Icons/LeatherBootsTailoredV2';t.destination_name='ue_leather_boots';t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+t.destination_name)
        for k,v in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True).items():tex.set_editor_property(k,v)
        tex.modify()
        if not E.save_loaded_asset(tex,False):raise RuntimeError('Icon save failed')
        io.receipt['icon_texture']=tex.get_path_name()
    for row in io.receipt['saved'].values():save(u.load_asset(row['asset']))
    io.receipt.update(completed=True,materials=surfaces['materials'],robe_materials=surfaces['robe_materials']);io.record();print('LEATHER_BOOT_ALL_ASSETS_SAVED',flush=True)
main()
