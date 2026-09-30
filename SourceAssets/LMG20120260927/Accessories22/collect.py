"""Read installed animation donors and export shared geometry for 201 authoring."""
import json, hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).resolve().parent
P=O.parents[2]
S=O/'Sources'; S.mkdir(exist_ok=True)
def tr(t):
    return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
def sha(path):
    return hashlib.sha256((P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
out={'meshes':{},'donors':{},'clips':{}}
for family,path in {'201':'/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10','pkm':'/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular'}.items():
    mesh=u.load_asset(path)
    dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _,rows=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    names={b.index:str(b.name) for b in rows}
    bones={str(b.name):dict(tr(b.world_transform),parent=names.get(b.parent_index)) for b in rows}
    out[family]={'asset':path,'sha256':sha(path),'bones':bones,'skeleton':mesh.skeleton.get_path_name()}
    selected=[n for n in bones if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
    ancestors=set(['WPN_root','hand_r'])
    for n in selected+list(ancestors):
        p=bones[n]['parent']
        while p:ancestors.add(p);p=bones[p]['parent']
    selected=list(dict.fromkeys(selected+list(ancestors)))
    clips=['idle','aim','fire','aim_fire','inspect','equip','reload','reload_empty','sprint_enter','sprint_loop','sprint_exit','quick_melee','reload_belt','reload_belt_empty'] if family=='201' else ['vertical','canted','prism','angled']
    for key in clips:
        asset=('/Game/Weapons/LMG201/Reload11/A_LMG201_'+key if key.startswith('reload_belt') else '/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_'+key) if family=='201' else '/Game/Weapons/PKMLowpoly20260922/Accessories14/Animations/'+key+'/A_PKM_'+key+'_idle'
        clip=u.load_asset(asset)
        if not clip:raise RuntimeError('Missing '+asset)
        model=clip.get_editor_property('data_model_interface')
        count=model.get_number_of_keys() if family=='201' else 1
        opts=u.AnimPoseEvaluationOptions(optional_skeletal_mesh=mesh,evaluation_type=u.AnimDataEvalType.SOURCE)
        record={'asset':asset,'sha256':sha(asset),'seconds':clip.get_play_length(),'count':count,'fps':[model.get_frame_rate().numerator,model.get_frame_rate().denominator],'metadata':{str(k):str(v) for k,v in u.EditorAssetLibrary.get_metadata_tag_values(clip).items()}}
        poses=[]
        for i in range(count):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,record['seconds']*i/max(1,count-1),opts)
            poses.append({n:{'local':tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)),'world':tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD))} for n in selected})
        file=S/(family+'_'+key+'.json');file.write_text(json.dumps(dict(record,poses=poses),separators=(',',':')),encoding='utf8')
        out['clips' if family=='201' else 'donors'][key]=dict(record,file=str(file))
        print('LMG20122_COLLECT',family,key,flush=True)
for key in ['vertical','tactical_vertical','canted','prism','angled','skeleton','core_stock','qr_performance','tactical_telescopic','phantom_reargrip','balanced_reargrip','stable_antislip_reargrip','laser','flashlight']:
    asset='/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes/SM_PKM_'+key
    mesh=u.load_asset(asset)
    if not mesh:raise RuntimeError('Missing '+asset)
    f=S/(key+'.fbx')
    task=u.AssetExportTask()
    task.object=mesh;task.filename=str(f);task.automated=True;task.prompt=False
    task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption()
    task.options.level_of_detail=False;task.options.collision=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+key)
    materials=[{'slot':str(m.material_slot_name),'path':m.material_interface.get_path_name()} for m in mesh.static_materials]
    sockets={}
    for sock in [mesh.find_socket(n) for n in ['Emitter','AimGuide','OpticAxis','Eye','ADS']]:
        if not sock:continue
        sockets[str(sock.socket_name)]={'p':list(sock.relative_location.to_tuple()),'r':list(sock.relative_rotation.to_tuple()),'s':list(sock.relative_scale.to_tuple())}
    out['meshes'][key]={'asset':asset,'sha256':sha(asset),'file':str(f),'materials':materials,'sockets':sockets}
(O/'sources.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print('LMG20122_SOURCES_SAVED',flush=True)
