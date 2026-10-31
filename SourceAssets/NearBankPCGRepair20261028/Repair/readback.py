from pathlib import Path
from datetime import datetime
import json,unreal as u
R=Path(__file__).resolve().parent
w=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
rows=[];meshes={}
sm_editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.get_default_object(u.StaticMeshEditorSubsystem)
def tr(t):return dict(p=list(t.translation.to_tuple()),q=list(t.rotation.to_tuple()),s=list(t.scale3d.to_tuple()))
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
    label=a.get_actor_label()
    if not(label.startswith('NBPCG_') or label.startswith('NB28_Cell_')):continue
    for c in a.get_components_by_class(u.StaticMeshComponent):
        sm=c.static_mesh
        if not sm:continue
        if isinstance(c,u.InstancedStaticMeshComponent):
            transforms=[tr(c.get_instance_transform(i,True)) for i in range(c.get_instance_count())];stride=c.get_editor_property('num_custom_data_floats');custom=list(c.get_editor_property('per_instance_sm_custom_data'))
        else:transforms=[tr(c.get_world_transform())];stride=0;custom=[]
        if not transforms:continue
        p=sm.get_path_name()
        if p not in meshes:
            b=sm.get_bounding_box();body=sm.get_editor_property('body_setup')
            meshes[p]=dict(min=list(b.min.to_tuple()),max=list(b.max.to_tuple()),collision_trace=str(body.get_editor_property('collision_trace_flag')),simple_shapes=sm_editor.get_simple_collision_count(sm))
        rows.append(dict(actor=label,mesh=p,materials=[m.get_path_name() if m else None for m in c.get_materials()],transforms=transforms,collision=str(c.get_collision_enabled()),profile=str(c.get_collision_profile_name()),visible=c.is_visible(),hidden=c.get_editor_property('hidden_in_game'),custom_stride=stride,custom=custom))
(R/'saved_readback.json').write_text(json.dumps(dict(rows=rows,meshes=meshes,saved_at=datetime.now().astimezone().isoformat()),separators=(',',':')))
print('REPAIR_READBACK',len(rows),sum(len(r['transforms']) for r in rows))
