"""Requested read-only examination of the active M07 membrane asset."""
import json
from pathlib import Path
import unreal as u
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/MembraneStabilityV31')
OUT.mkdir(parents=True,exist_ok=True)
bp=u.load_asset('/Game/Monsters/BlindSupplicantM07/BP_BlindSupplicantM07')
cdo=u.get_default_object(bp.generated_class())
mesh=cdo.get_editor_property('visual_mesh')
def value(v):
    if isinstance(v,(bool,int,float,str)) or v is None:return v
    if isinstance(v,u.Object):return v.get_path_name()
    return str(v)
def props(obj,names):
    result={}
    for name in names:
        try:result[name]=value(obj.get_editor_property(name))
        except Exception as exc:result[name]={'unavailable':str(exc)}
    return result
result=dict(mesh=mesh.get_path_name(),pie=False,settings=props(cdo,('b_enable_gill_bone_clearance','gill_clearance_angle_degrees','cloth_resume_distance','cloth_suspend_distance')),
    action_refs=props(cdo,('idle_clip','slow_walk_clip','chase_clip','melee_left_clip','melee_right_clip','magic_gather_clip','magic_release_clip','death_clip')))
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor:result['pie']=editor.is_in_play_in_editor()
try:
    cloths=mesh.get_editor_property('mesh_clothing_assets')
    result['cloths']=[]
    for cloth in cloths:
        row={'asset':cloth.get_path_name(),'class':cloth.get_class().get_name(),'props':props(cloth,('lod_map','reference_bone_index','used_bone_names')),'configs':{}}
        for name,config in cloth.get_editor_property('cloth_configs').items():
            row['configs'][str(name)]=props(config,('anim_drive_stiffness','anim_drive_damping','damping_coefficient','local_damping_coefficient',
                'bending_stiffness','edge_stiffness','area_stiffness','tether_scale','collision_thickness','use_self_collisions','use_self_collision_spheres',
                'self_collision_sphere_radius','self_collision_sphere_radius_cull_multiplier','iteration_count','max_iteration_count','subdivision_count'))
        result['cloths'].append(row)
except Exception as exc:result['cloth_read_error']=str(exc)
(OUT/'active_membrane_before_v31.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M07_V31_MEMBRANE_READ '+json.dumps(result,ensure_ascii=False))
