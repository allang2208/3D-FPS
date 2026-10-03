import runpy, json, math
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent
module=runpy.run_path(str(OUT/'install_runtime.py'))
for phase in ('surface','animations'): module['install'](phase)

# Read the actual imported pose extremes requested in the user's defect report.
actor=u.get_default_object(u.HundredEyedSlagMonster)
mesh=actor.get_editor_property('visual_mesh'); clips=actor.get_editor_property('clips')
options=u.AnimPoseEvaluationOptions(); options.evaluation_type=u.AnimDataEvalType.SOURCE
options.optional_skeletal_mesh=mesh
report={'mesh':mesh.get_path_name(),'native_code_changed':False,'f6_class':actor.get_class().get_path_name(),
    'chase_speed_cm_s':actor.get_editor_property('chase_speed'),'return_speed_cm_s':actor.get_editor_property('return_speed'),
    'runtime_tested':False,'fps_measured':False,'actions':{}}
def point(pose,name,reference=False):
    fn=u.AnimPoseExtensions.get_ref_bone_pose if reference else u.AnimPoseExtensions.get_bone_pose
    p=fn(pose,name,u.AnimPoseSpaces.WORLD).translation
    return [p.x,p.y,p.z]
def subtract(a,b): return [x-y for x,y in zip(a,b)]
def length(a): return math.sqrt(sum(x*x for x in a))
for role in ('Run','Move','AttackSweep_R','AttackSlam_R'):
    clip=clips[role]; bends=[]; segment_errors=[]; max_dist=0
    count=clip.get_editor_property('data_model_interface').get_number_of_keys()
    for frame in range(count):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*frame/max(1,count-1),options)
        for kind in ('front','rear'):
            for side in ('L','R'):
                ns=[f'{kind}_{part}_{side}' for part in ('upper','lower','palm')]
                ps=[point(pose,n) for n in ns]; rs=[point(pose,n,True) for n in ns]
                a,b=subtract(ps[1],ps[0]),subtract(ps[2],ps[1])
                ra,rb=subtract(rs[1],rs[0]),subtract(rs[2],rs[1])
                cosine=sum(x*y for x,y in zip(a,b))/max(1e-9,length(a)*length(b))
                bends.append(math.degrees(math.acos(max(-1,min(1,cosine)))))
                segment_errors.extend([abs(length(a)/length(ra)-1)*100,abs(length(b)/length(rb)-1)*100])
                max_dist=max(max_dist,length(ps[2]))
    report['actions'][role]={'seconds':clip.get_play_length(),'keys':count,'max_bend_degrees':max(bends),
        'max_segment_length_error_percent':max(segment_errors),'max_palm_distance_cm':max_dist}
    if max(bends)>113 or max(segment_errors)>.1: raise RuntimeError('Imported pose mismatch '+role+' '+str(report['actions'][role]))
material=mesh.get_editor_property('materials')[0].material_interface
report['skin_textures']=[{'path':t.get_path_name(),'max_size':t.get_editor_property('max_texture_size'),
    'never_stream':t.get_editor_property('never_stream')} for t in u.MaterialEditingLibrary.get_material_used_textures(material)]
report['lod_count']=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(mesh)
report['lod0_triangles']=str(u.EditorAssetLibrary.get_tag_values(mesh.get_path_name()).get('Triangles',''))
(OUT/'saved_asset_diagnosis.json').write_text(json.dumps(report,indent=2))
(OUT/'installation_complete.json').write_text(json.dumps({'revision':'RuntimeV3','assets_saved':True,
    'runtime_paths_preserved':True,'native_build_required':False,'runtime_tested':False},indent=2))
print('V3_INSTALLATION_COMPLETE '+json.dumps(report))
