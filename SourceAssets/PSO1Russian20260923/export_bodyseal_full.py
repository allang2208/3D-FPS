"""Export sealed AKM/A762 PSO with adapters, in the same canonical space as the shipped FBX.

The editable blend keeps an inverse yaw so it still sits on the receiver. The
game mesh was exported before that inverse was applied, so this export
temporarily uses identity matrices and does not save the blend.
"""
import bpy
from pathlib import Path
from mathutils import Matrix

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
EXP = O / 'Exports'
for host in ('A762', 'AKM'):
    bpy.ops.wm.open_mainfile(filepath=str(O / ('PSO1_%s_Editable.blend' % host)))
    objs = [ob for ob in bpy.context.scene.objects if ob.type == 'MESH' and not ob.hide_render]
    names = sorted(ob.name for ob in objs)
    if not any('Dovetail' in n or 'Pad' in n for n in names):
        raise RuntimeError('adapter missing from ' + host + ' ' + str(names))
    if 'PSO_ScopeBody' not in names or 'PSO_ScopeLens' not in names:
        raise RuntimeError('scope body missing ' + host)
    saved = {ob: ob.matrix_world.copy() for ob in objs}
    for ob in objs:
        ob.matrix_world = Matrix.Identity(4)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs:
        ob.hide_set(False)
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    fbx = EXP / ('SM_PSO1_%s_BodySealFull.fbx' % host)
    bpy.ops.export_scene.fbx(
        filepath=str(fbx), use_selection=True, object_types={'MESH'},
        axis_forward='-Y', axis_up='Z', bake_anim=False,
        mesh_smooth_type='FACE', use_tspace=True)
    for ob, mat in saved.items():
        ob.matrix_world = mat
    print('PSO_BODYSEAL_EXPORTED', host, len(objs), names, flush=True)
print('PSO_BODYSEAL_EXPORT_DONE', flush=True)
