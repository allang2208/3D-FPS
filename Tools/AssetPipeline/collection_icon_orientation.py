"""Camera framing convention for collection icons, independent of equipment art."""
import math
import bpy
from mathutils import Vector

def orient_collection_camera(camera, grid_w, grid_h, forward=(-1, 0, 0), upright=None, dimensions=None):
    """Centre narrow inventory shapes on an axis; retain authored views for broad items.

    2x1 / 3x1 icons use a horizontal main axis; 1x2 / 1x3 use a vertical axis.
    Physically slender 1x1 items (USB and DIMM) also use a horizontal main axis.
    2x2, 3x2 and other broad items keep their original three-quarter view.
    """
    slender_single=False
    if grid_w==grid_h==1 and dimensions:
        planar=sorted(float(v) for v in dimensions[:2])
        slender_single=planar[0]>0 and planar[1]/planar[0]>=2.4
    mode='standard_inventory'
    if upright is not None:mode='vertical_centered' if upright else 'horizontal_centered'
    elif grid_w==1 and grid_h>1:mode='vertical_centered'
    elif (grid_h==1 and grid_w>1) or slender_single:mode='horizontal_centered'
    if mode=='standard_inventory':
        return dict(mode=mode,authored_axis=list(forward),target_screen_up_angle_degrees=None,camera_roll_delta_degrees=0.)
    target=math.pi*.5 if mode=='vertical_centered' else math.pi
    bpy.context.view_layer.update()
    projected=camera.matrix_world.inverted().to_3x3() @ Vector(forward)
    roll=math.atan2(projected.y,projected.x)-target
    camera.rotation_euler.rotate_axis('Z',roll)
    bpy.context.view_layer.update()
    return dict(mode=mode,
                authored_axis=list(forward),target_screen_up_angle_degrees=math.degrees(target),
                camera_roll_delta_degrees=math.degrees(roll))
