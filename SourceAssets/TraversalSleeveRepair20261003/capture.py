"""Read the saved traversal garments for the reported deformation diagnosis."""
import json, sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_ue import source_snapshot, snapshot, transform
from garment_pipeline import write, digest, asset_file
c=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
native_path='/Game/Characters/ModularOutfit20260924/BarePalmV7/Traversal/SK_Traversal_BareArmsV7.SK_Traversal_BareArmsV7'
paths={'native':native_path,'skin':c['profiles'][native_path]['native_bare_skin']}
for key in ['ue_chainmail_shirt']:
    paths[key]=c['items'][key]['rig_meshes']['Traversal']
write(R/'before.json',{'paths':paths,'profile':c['profiles'][native_path]})
for key,path in paths.items():
    asset=u.load_asset(path);dm,d=source_snapshot(asset)
    d['slots']=[{'name':str(m.material_slot_name),'material':m.material_interface.get_path_name() if m.material_interface else None} for m in asset.materials]
    d['asset_sha256']=digest(asset_file(path))
    _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    d['parents']={str(b.name):b.parent_index for b in bones}
    d['bone_order']=[str(b.name) for b in bones]
    write(R/'Before'/(key+'.json'),d)
    # NullRHI has no render skin-weight buffer. Source geometry remains valid
    # for this diagnosis; do not label unavailable render LODs as inspected.
    if key.startswith('ue_'):
        write(R/'Before'/(key+'-lod-policy.json'),{'render_lods_read':False,
            'source_models':[{'triangles_ratio':m.get_editor_property('reduction_settings').get_editor_property('num_of_triangles_percentage'),
                              'max_bones_per_vertex':m.get_editor_property('reduction_settings').get_editor_property('max_bones_per_vertex')}
                             for m in asset.get_editor_property('source_models')]})
    print('TRAVERSAL_GARMENT_SOURCE',key,len(d['positions']),len(d['triangles']),flush=True)
native=u.load_asset(native_path);_,d=source_snapshot(native)
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=native;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
poses=[]
for action in ['Vault','Mantle','Climb']:
    path='/Game/Movement/Traversal/Native/A_Traversal_'+action
    clip=u.load_asset(path)
    for i in range(11):
        time=clip.get_play_length()*i/10
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opts)
        poses.append({'action':action,'time':time,'bones':{n:transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in d['rest']}})
write(R/'source-poses.json',poses)
print('TRAVERSAL_GARMENT_INPUTS_SAVED',flush=True)
