"""Historical FitV2 readback; only use after explicitly installing that fallback.

The accepted default is NaturalV3. This comparison retains the original FitV2
evidence contract and must not be reported as a current NaturalV3 validation.
"""
import gc,json,math
from pathlib import Path
import unreal as u

def main():
    base=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedDogMeshy20260924')
    before=json.loads((base/'GodotRunFitV2/binding_before.json').read_text())
    authored=json.loads((base/'RunBloodDiagnosis/blender_godot_fit.json').read_text())
    ds=u.load_asset(before['dataset']);mesh=ds.get_editor_property('reference_mesh')
    actions=ds.get_editor_property('actions')
    clip=actions['Run'].get_editor_property('sequence')
    failures=[];errors=[];source_errors=[];foot=[]
    for role,old in before['actions'].items():
        action=actions[role]
        for key,value in old.items():
            if key=='sequence' and role in ('Run','RunTurnLeft','RunTurnRight'):
                if action.get_editor_property(key)!=clip:failures.append(role+' run mismatch')
            elif key=='sequence':
                current=action.get_editor_property(key)
                if (current.get_path_name() if current else None)!=value:failures.append(role+' sequence changed')
            elif str(action.get_editor_property(key))!=value:failures.append(role+' '+key+' changed')
    for mode in ('SOURCE','COMPRESSED'):
        opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=getattr(u.AnimDataEvalType,mode);opts.optional_skeletal_mesh=mesh
        for i,row in enumerate(authored['frames']):
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,clip.get_play_length()*i/(len(authored['frames'])-1),opts)
            for name,position in row['bones'].items():
                t=u.AnimPoseExtensions.get_bone_pose(pose,name.replace('.','_'),u.AnimPoseSpaces.WORLD)
                error=math.dist([position[0]*100,-position[1]*100,position[2]*100],[t.translation.x,t.translation.y,t.translation.z])
                (errors if mode=='COMPRESSED' else source_errors).append(error)
    m=u.load_asset('/Game/Weapons/GunplayFX/Impacts/Blood/M_FleshStainV3')
    L=u.MaterialEditingLibrary
    convert=L.get_material_property_input_node(m,u.MaterialProperty.MP_FRONT_MATERIAL)
    coverage=L.get_inputs_for_material_expression(m,convert)[1]
    opacity=L.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY)
    if coverage!=opacity:failures.append('Decal Coverage is not connected to the opacity mask')
    shape=next(n for n in L.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)
               and n.get_editor_property('description')=='Fluid polish blood stain')
    if 'float line=' in shape.get_editor_property('code'):failures.append('Reserved shader identifier remains')
    if max(errors)>.6:failures.append('Run differs from authored pose by over 6 mm')
    report={'failures':failures,'run_asset':clip.get_path_name(),'seconds':clip.get_play_length(),
            'sampled_poses':len(authored['frames']),'bones_per_pose':len(authored['rest']),
            'source_max_position_error_cm':max(source_errors),'compressed_max_position_error_cm':max(errors),
            'non_run_contracts_unchanged':not any('changed' in x for x in failures),
            'blood_coverage_connected':coverage==opacity,'run_speed':ds.get_editor_property('run_speed'),
            'gameplay_tested':False,'gameplay_rendered':False}
    (base/'RunBloodDiagnosis/saved_readback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('RUN_BLOOD_READBACK '+json.dumps(report))
    if failures:raise RuntimeError(str(failures))

main()
gc.collect()
