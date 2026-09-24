"""Read the two user-reported faults; no gameplay or asset mutations."""
import json
from pathlib import Path
import unreal as u

OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedDogMeshy20260924/RunBloodDiagnosis')
OUT.mkdir(exist_ok=True)
L=u.MaterialEditingLibrary
report={}
def safe(fn):
    try:return fn()
    except Exception as e:return {'error':str(e)}
def props(obj,names):return {n:safe(lambda n=n:str(obj.get_editor_property(n))) for n in names}
def transform(t):
    return {'p':[t.translation.x,t.translation.y,t.translation.z],
            'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],
            's':[t.scale3d.x,t.scale3d.y,t.scale3d.z]}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_game_world() if editor else None
report['pie_active']=world is not None
report['dirty']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
report['materials']={}
for name in ('M_FleshMistV1','M_FleshDropletV2','M_FleshStainV3'):
    m=u.load_asset('/Game/Weapons/GunplayFX/Impacts/Blood/'+name)
    row=props(m,['blend_mode','material_domain','shading_model','use_material_attributes','used_with_instanced_static_meshes'])
    row['expressions']=[]
    for n in L.get_material_expressions(m):
        inputs=[str(x) for x in L.get_material_expression_input_names(n)]
        nd={'name':n.get_name(),'class':n.get_class().get_name(),'inputs':inputs,
            'description':safe(lambda n=n:str(n.get_editor_property('description')))}
        if isinstance(n,u.MaterialExpressionCustom):nd['code']=n.get_editor_property('code')
        nd['sources']=safe(lambda n=n:[str(x) for x in L.get_inputs_for_material_expression(m,n)])
        row['expressions'].append(nd)
    row['outputs']={p:safe(lambda p=p:str(L.get_material_property_input_node(m,getattr(u.MaterialProperty,'MP_'+p))))
                    for p in ['FRONT_MATERIAL','BASE_COLOR','OPACITY','ROUGHNESS']}
    report['materials'][name]=row
bp=u.load_asset('/Game/Monsters/InfectedDog/BP_InfectedDog')
cdo=u.get_default_object(bp.generated_class())
dataset=cdo.get_editor_property('animation_set');mesh=dataset.get_editor_property('reference_mesh')
report['dataset']=props(dataset,['run_speed','walk_speed','run_blend_start_ratio','run_blend_full_ratio','run_phase_offset'])
report['cdo']=props(cdo,['chase_speed'])
comp=u.SkeletalMeshComponent();comp.set_skeletal_mesh_asset(mesh)
names=[str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
report['bones']=names;report['clips']={}
for role in ('Run','Walk','AttackRunBite'):
    clip=dataset.get_editor_property('actions')[role].get_editor_property('sequence')
    row={'path':clip.get_path_name(),'duration':clip.get_play_length(),'poses':{}}
    for label,kind in [('source',u.AnimDataEvalType.SOURCE),('compressed',u.AnimDataEvalType.COMPRESSED)]:
        opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=kind;opt.optional_skeletal_mesh=mesh
        rows=[]
        for i in range(27):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/26,opt)
            rows.append({n:transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names})
        row['poses'][label]=rows
    report['clips'][role]=row
if world:
    report['live_dogs']=[]
    for dog in u.GameplayStatics.get_all_actors_of_class(world,u.InfectedDogMonster):
        mesh=dog.get_editor_property('mesh');anim=mesh.get_anim_instance()
        report['live_dogs'].append({'name':dog.get_path_name(),'velocity':str(dog.get_velocity()),
            'mesh':props(mesh,['relative_rotation','relative_scale3d']),
            'anim':props(anim,['active_action','action_time','gait_phase','speed','walk_run_alpha','move_alpha','turn_alpha'])})
    report['live_blood_decals']=[]
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        for decal in actor.get_components_by_class(u.DecalComponent):
            material=decal.get_decal_material()
            if material and 'Flesh' in material.get_path_name():
                report['live_blood_decals'].append({'material':material.get_path_name(),
                    'size':str(decal.get_editor_property('decal_size')),'visible':decal.is_visible()})
(OUT/'ue_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'file':str(OUT/'ue_before.json'),'pie':report['pie_active'],
                  'dataset':report['dataset'],'live_dogs':report.get('live_dogs',[])}))
