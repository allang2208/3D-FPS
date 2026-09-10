"""Read-only, unobstructed A/B review of the repaired linear-skinned hands."""
import bpy
import argparse, sys
from pathlib import Path
from mathutils import Vector

out = Path(r'D:/FPS3D/FPSGAME/SourceAssets/ArmsRepair20260909')
parser = argparse.ArgumentParser()
parser.add_argument('--blend', default='SK_ArmsRepair_anatomy.blend')
parser.add_argument('--prefix', default='root_review')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(out/args.blend))
rig = bpy.data.objects['SK_AKM_Viewmodel']
before = bpy.data.objects['SK_ArmsReplacement_WRAD']
after = bpy.data.objects['SK_ArmsRepair_WRAD']
scene = bpy.context.scene
sys.path.insert(0, str(Path(__file__).parent))
from repair_arms_skinning import setup_render
camera = setup_render(rig)
scene.render.resolution_x = 800
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
camera.data.type = 'ORTHO'
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj not in (before, after):
        obj.hide_render = True

for clip, frame, side in [('idle',1,'r'), ('reload',52,'l'), ('reload_empty',52,'l'), ('reload_empty',75,'r'), ('reload_empty',88,'r')]:
    action = bpy.data.actions['AKM_'+clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(frame)
    after.hide_set(False)
    bpy.context.view_layer.update()
    evaluated = after.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    names = {g.index:g.name for g in after.vertex_groups}
    indices = [v.index for v in after.data.vertices if sum(g.weight for g in v.groups
        if names[g.group].endswith('_'+side) and names[g.group].startswith(('hand_','thumb_','index_','middle_','ring_','pinky_'))) > 0.75]
    points = [after.matrix_world @ mesh.vertices[i].co for i in indices]
    evaluated.to_mesh_clear()
    lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center = (lo+hi)*0.5
    wrist = rig.matrix_world @ rig.pose.bones['hand_'+side].matrix.translation
    middle = rig.matrix_world @ rig.pose.bones['middle_01_'+side].matrix.translation
    index = rig.matrix_world @ rig.pose.bones['index_01_'+side].matrix.translation
    pinky = rig.matrix_world @ rig.pose.bones['pinky_01_'+side].matrix.translation
    normal = (index-pinky).cross(middle-wrist).normalized()
    radius = max((p-center).length for p in points)
    camera.data.ortho_scale = radius*2.5
    for sign in (1,-1):
        camera.location = center + normal*sign*max(1.0, radius*6)
        camera.rotation_euler = (center-camera.location).to_track_quat('-Z','Y').to_euler()
        for label, shown, hidden in [('before',before,after),('after',after,before)]:
            shown.hide_set(False)
            shown.hide_render = False
            hidden.hide_render = True
            scene.render.filepath = str(out/f'{args.prefix}_{clip}_{frame}_{side}_{sign}_{label}.png')
            bpy.ops.render.render(write_still=True)
print('ROOT_PALM_REVIEW_COMPLETE')
