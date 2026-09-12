"""Non-destructive authoring source for QBZ hard-surface polish (metres)."""
import bpy, bmesh, math
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'QBZ191_Editable.blend'))
gun=bpy.data.objects['QBZ191_Export']
rig=bpy.data.objects['SK_M4_Infima']
hands=bpy.data.objects['SK_Manny_Arms_Export']
bpy.ops.object.select_all(action='DESELECT')
gun.select_set(True);bpy.context.view_layer.objects.active=gun
# Discontinuous mechanical pieces stay separate; bevel only actual sharp edges.
bm=bmesh.new();bm.from_mesh(gun.data)
weights=bm.edges.layers.float.new('bevel_weight_edge')
for edge in bm.edges:
    angle=edge.calc_face_angle(0) if edge.is_manifold else 0
    sharp=angle>math.radians(38)
    edge.smooth=not sharp
    iron=any(f.material_index==2 for f in edge.link_faces)
    edge[weights]=(0.6 if iron else 1.0) if sharp else 0.0
bm.to_mesh(gun.data);bm.free()
bevel=gun.modifiers.new('Machined edge radii 0.15mm sights 0.25mm body','BEVEL')
bevel.limit_method='WEIGHT';bevel.width=.00025;bevel.segments=4
bevel.affect='EDGES';bevel.use_clamp_overlap=True;bevel.harden_normals=True
bpy.ops.object.modifier_move_up(modifier=bevel.name)
bpy.ops.object.modifier_apply(modifier=bevel.name)
normal=gun.modifiers.new('Area weighted hard surface normals','WEIGHTED_NORMAL')
normal.keep_sharp=True;normal.weight=50
bpy.ops.object.modifier_move_up(modifier=normal.name)
bpy.ops.object.modifier_apply(modifier=normal.name)
# Explicit split normals + smoothing groups; unchanged rig and animation actions.
bpy.ops.object.select_all(action='DESELECT')
for obj in (rig,hands,gun):obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(O/'SK_QBZ191_Manny.fbx'),use_selection=True,
    object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',
    add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ191_SurfacePolish.blend'))
print('QBZ_SURFACE_EXPORT_COMPLETE')
