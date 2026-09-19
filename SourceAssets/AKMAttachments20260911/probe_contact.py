import bpy
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(O/'AKM_Attachments_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();o=bpy.data.objects['AKM_Soviet_Native'];ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();xf=(r.matrix_world@r.pose.bones['WPN_root'].matrix).inverted()@o.matrix_world;b=BVHTree.FromPolygons([xf@v.co for v in me.vertices],[list(p.vertices) for p in me.polygons]);print('SURFACE',[(y,b.ray_cast(Vector((.0008,y,-.25)),Vector((0,0,1)),.5)[0][:]) for y in [-.34,-.33,-.30,-.27,-.26]])
