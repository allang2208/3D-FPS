"""Capture installed donor/host assets for scoped drum authoring. No playback."""
import unreal as u, json, gzip, hashlib
from pathlib import Path
O=Path(__file__).parent; P=O.parents[2]; I=O/'Inputs'; I.mkdir(exist_ok=True)
out={'rigs':{},'clips':{},'meshes':{}}
def tr(t): return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
def sha(path): return hashlib.sha256((P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
def export(a,name):
    e=u.AssetExportTask();e.object=a;e.filename=str(I/(name+'.fbx'));e.automated=True;e.prompt=False;e.replace_identical=True;e.options=u.FbxExportOption();e.options.level_of_detail=False;e.options.collision=False;e.options.export_morph_targets=False;e.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
    if not u.Exporter.run_asset_export_task(e): raise RuntimeError('Export '+name)
    return e.filename
for tag,path in [('201','/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'),('akm','/Game/Weapons/AKMIntegration/SovietFab/RearGrip20260913/SK_AKM_MannyNative')]:
    mesh=u.load_asset(path)
    if not mesh: raise RuntimeError(path)
    dm,_=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _,rows=u.GeometryScript_BoneWeights.get_all_bones_info(dm);ids={b.index:str(b.name) for b in rows}
    bones={str(b.name):dict(tr(b.world_transform),parent=ids.get(b.parent_index)) for b in rows}
    out['rigs'][tag]={'asset':path,'sha256':sha(path),'bones':bones,'skeleton':mesh.skeleton.get_path_name(),'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.materials]}
    if tag=='201':out['rigs'][tag]['fbx']=export(mesh,'Current201')
    selected=list(bones)
    jobs=[]
    if tag=='201':
        for family in ['base','vertical','canted','prism','angled']:
            for key in ['idle','reload','reload_empty']:
                root='/Game/Weapons/LMG201'
                asset=(root+'/BeltFeed08/Animations/A_LMG201_idle' if family=='base' else f'{root}/Accessories22/Animations/{family}/A_LMG201_{family}_idle') if key=='idle' else f'{root}/Magazine24/Animations/{family}/A_LMG201_{family}_{key}'
                jobs.append((family,key,asset))
    else:
        jobs=[('base',key,'/Game/Weapons/AKMDrumFreeDrop20260920/base/A_AKM_drum_'+key) for key in ['reload','reload_empty']]
    for family,key,asset in jobs:
        clip=u.load_asset(asset)
        if not clip:raise RuntimeError(asset)
        model=clip.get_editor_property('data_model_interface');seconds=clip.get_play_length();count=model.get_number_of_keys()
        sample_count=1 if key=='idle' else count
        opts=u.AnimPoseEvaluationOptions(optional_skeletal_mesh=mesh,evaluation_type=u.AnimDataEvalType.SOURCE)
        poses=[]
        for i in range(sample_count):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,seconds*i/max(1,count-1),opts)
            poses.append({n:{'local':tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)),'world':tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD))} for n in selected})
        label=tag+'_'+family+'_'+key;f=I/(label+'.json.gz')
        with gzip.open(f,'wt',encoding='utf8') as z:json.dump(poses,z,separators=(',',':'))
        out['clips'][label]={'asset':asset,'sha256':sha(asset),'file':str(f),'seconds':seconds,'count':count,'fps':[model.get_frame_rate().numerator,model.get_frame_rate().denominator]}
        (O/'sources.json').write_text(json.dumps(out,indent=2));print('DRUM46_SOURCE',label,count,flush=True)
path='/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_drum';a=u.load_asset(path)
out['meshes']['drum']={'asset':path,'sha256':sha(path),'fbx':export(a,'DonorDrum'),'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in a.static_materials]}
for row in out['meshes']['drum']['slots']:
    m=u.load_asset(row['material']);row['base']=m.get_base_material().get_path_name()
    row['textures']={str(n):u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(m,n).get_path_name() for n in u.MaterialEditingLibrary.get_texture_parameter_names(m) if isinstance(m,u.MaterialInstance) and u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(m,n)}
(O/'sources.json').write_text(json.dumps(out,indent=2));print('DRUM46_COLLECT_SAVED',flush=True)
