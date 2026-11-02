"""Use the accepted V7 surface with this animation's original native binding."""
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

BARE = Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/RuneSword_BareArmsV7.blend')

def attach(rig):
    with bpy.data.libraries.load(str(BARE), link=False) as (src, dst):
        dst.objects = list(src.objects)
    native = next(o for o in dst.objects if o and o.type == 'ARMATURE')
    mesh = next(o for o in dst.objects if o and o.type == 'MESH')
    bpy.context.scene.collection.objects.link(mesh)
    # Native export positions are already in the source rig's bind space (m,
    # Y reflected from UE). Keep them verbatim. The standalone editable rig's
    # display axes are not FBX inverse-bind matrices and must not remap skin.
    mesh.parent = rig
    mesh.matrix_parent_inverse = Matrix.Identity(4)
    mesh.matrix_basis = Matrix.Identity(4)
    for modifier in mesh.modifiers:
        if modifier.type == 'ARMATURE':
            modifier.object = rig
    mesh.name = 'V7_BareArms_AnimationSurface'
    mesh.hide_render = False
    mesh.hide_set(False)
    mesh.hide_viewport = False
    mesh.color = (0.64, 0.39, 0.27, 1)
    for p in mesh.data.polygons:
        p.use_smooth = True
    bpy.data.objects.remove(native, do_unlink=True)
    return mesh
