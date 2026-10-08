"""Read and recompile the saved Blueprint in an isolated commandlet; never save."""
from pathlib import Path
import json
import unreal as u

bp = u.load_asset('/Game/Monsters/BoundCongregate/BP_BoundCongregate')

def describe():
    cdo = u.get_default_object(bp.generated_class())
    movement = cdo.get_editor_property('character_movement')
    return dict(walk_speed=cdo.get_editor_property('walk_speed'),
                animation_walk_speed=cdo.get_editor_property('animation_walk_speed'),
                max_walk_speed=movement.get_editor_property('max_walk_speed'),
                max_acceleration=movement.get_editor_property('max_acceleration'),
                tentacle_cooldown=cdo.get_editor_property('tentacle_cooldown'),
                move_clip=cdo.get_editor_property('move_clip').get_path_name(),
                visual_mesh=cdo.get_editor_property('visual_mesh').get_path_name())

report = dict(cold_load=describe())
u.BlueprintEditorLibrary.compile_blueprint(bp)
report['after_compile'] = describe()
Path('D:/FPS3D/FPSGAME/Saved/bound-movement-cold-inspection-20261008.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('BOUND_MOVEMENT_COLD_READ '+json.dumps(report))
