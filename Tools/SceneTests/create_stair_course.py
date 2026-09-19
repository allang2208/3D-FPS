"""Place a reproducible walking-stair course beside the existing traversal walls."""
import json
from pathlib import Path
import unreal

ROOT = Path('D:/FPS3D/FPSGAME')
LEVEL = '/Game/GameMaps/DayNight_Lighting'
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert level.load_level(LEVEL)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
existing = {a.get_actor_label(): a for a in actors.get_all_level_actors()}
wall = existing['TraversalTest_High']
center, extent = wall.get_actor_bounds(False)
# Clear of the wall's side; stairs remain accessible at both ends and from the sides.
origin = unreal.Vector(center.x - extent.x - 420, center.y - extent.y - 180, center.z - extent.z)
folder = 'Movement/StairWalkTest'
asset_dir = '/Game/Movement/StairWalkTest'
unreal.EditorAssetLibrary.make_directory(asset_dir)
cube = unreal.load_asset('/Engine/BasicShapes/Cube')

def material(name, rgb):
    path = asset_dir + '/' + name
    result = unreal.load_asset(path)
    if result:
        return result
    result = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, asset_dir, unreal.Material, unreal.MaterialFactoryNew())
    color = unreal.MaterialEditingLibrary.create_material_expression(result, unreal.MaterialExpressionConstant3Vector)
    color.set_editor_property('constant', unreal.LinearColor(*rgb, 1))
    unreal.MaterialEditingLibrary.connect_material_property(color, '', unreal.MaterialProperty.MP_BASE_COLOR)
    rough = unreal.MaterialEditingLibrary.create_material_expression(result, unreal.MaterialExpressionConstant)
    rough.set_editor_property('r', .82)
    unreal.MaterialEditingLibrary.connect_material_property(rough, '', unreal.MaterialProperty.MP_ROUGHNESS)
    unreal.MaterialEditingLibrary.recompile_material(result)
    unreal.EditorAssetLibrary.save_loaded_asset(result)
    return result

blue = material('M_StairBlue', (.055, .24, .32))
yellow = material('M_Step40', (.62, .36, .035))
red = material('M_Step45', (.44, .065, .035))
rows = []

def box(name, pos, size, mat):
    actor = existing.get(name) or actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*pos))
    actor.set_actor_label(name)
    actor.set_folder_path(folder)
    component = actor.static_mesh_component
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_static_mesh(cube)
    component.set_collision_profile_name('BlockAll')
    actor.set_actor_location(unreal.Vector(*pos), False, True)
    actor.set_actor_scale3d(unreal.Vector(*(v / 100 for v in size)))
    component.set_material(0, mat)
    component.set_mobility(unreal.ComponentMobility.STATIC)
    rows.append(dict(name=name, position=pos, size=size))

def label(name, text, pos, color):
    actor = existing.get(name) or actors.spawn_actor_from_class(unreal.TextRenderActor, unreal.Vector(*pos))
    actor.set_actor_label(name)
    actor.set_folder_path(folder)
    actor.set_actor_location(unreal.Vector(*pos), False, True)
    actor.set_actor_rotation(unreal.Rotator(pitch=0, yaw=180, roll=0), True)
    component = actor.get_component_by_class(unreal.TextRenderComponent)
    component.set_text(text)
    component.set_world_size(23)
    component.set_text_render_color(unreal.Color(*color, 255))
    component.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER)

x, y, z = origin.x, origin.y, origin.z
for i in range(6):
    h = 20 * (i + 1)
    box('StairWalk_Step_%02d' % (i + 1), (x + 30 + 60*i, y, z + h/2), (60, 220, h), blue)
box('StairWalk_Landing', (x + 480, y, z + 60), (240, 220, 120), blue)
label('StairWalk_Label', 'WALK STAIRS\n20 cm x 6 | HOLD W', (x-15, y, z+180), (155,225,250))
box('StairWalk_Boundary40', (x-200, y-400, z+20), (260, 240, 40), yellow)
box('StairWalk_Boundary45', (x+230, y-400, z+22.5), (260, 240, 45), red)
label('StairWalk_Label40', '40 cm\nAUTO STEP', (x-340, y-400, z+130), (255,210,70))
label('StairWalk_Label45', '45 cm\nJUMP REQUIRED', (x+90, y-400, z+135), (255,110,80))
assert level.save_current_level()
output = ROOT/'Saved/StairMovement/course.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(dict(level=LEVEL, wall=wall.get_actor_label(), origin=[x,y,z], actors=rows), indent=2), encoding='utf-8')
unreal.log('STAIR_COURSE_SAVED ' + str(output))
