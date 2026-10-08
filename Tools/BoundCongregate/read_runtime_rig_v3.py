import unreal as u, json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/RigRepairV3');ROOT.mkdir(exist_ok=True)
bp=u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate');cdo=u.get_default_object(bp.generated_class())
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report=dict(pie=bool(world),references={})
for key in ('visual_mesh','move_clip','turn_left_clip','turn_right_clip','idle_clip','bite_clip','hit_clip','death_clip','ai_controller_class'):
    obj=cdo.get_editor_property(key);report['references'][key]=obj.get_path_name() if obj else None
mesh=cdo.get_editor_property('visual_mesh')
report['materials']=[dict(slot=str(s.get_editor_property('imported_material_slot_name')),material=s.material_interface.get_path_name() if s.material_interface else None) for s in mesh.get_editor_property('materials')]
report['actors']=[]
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.BoundCongregate):
        comp=actor.get_mesh();anim=comp.get_anim_instance()
        item=dict(name=actor.get_name(),velocity=str(actor.get_velocity()),mesh=comp.get_skinned_asset().get_path_name(),
                  anim_class=anim.get_class().get_name() if anim else None)
        if anim:
            clip=anim.get_editor_property('active_clip');item['clip']=clip.get_name() if clip else None
        report['actors'].append(item)
(ROOT/'runtime_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
