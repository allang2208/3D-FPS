"""Prepare the selected, unmounted game-model candidates from their frozen masters."""
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parents[1]
CACHE = ASSETS.parent/'Saved/M249RearGrip44'
MODELS = {
    'phantom_reargrip': ('PhantomRearGripMultiview_20260913/seed_91627', 50000),
    'stable_antislip_reargrip': ('StableAntiSlipRearGrip20260913/seed_91727', 30000),
    'balanced_reargrip': ('BalancedRearGrip20260913/seed_91703', 50000),
}


def prepare(key):
    folder, budget = MODELS[key]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.import_scene.gltf(filepath=str(ASSETS/folder/'textured_master_00001_.glb'))
    obj, = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    # Match the archived game candidates' canonical axes and triangle budgets.
    obj.data.transform(Matrix.Rotation(-np.pi/2, 4, 'Z') @ obj.matrix_world)
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.objects.active = obj
    obj.data.calc_loop_triangles()
    lod = obj.modifiers.new('Original game LOD', 'DECIMATE')
    lod.ratio = min(1, budget/len(obj.data.loop_triangles))
    lod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=lod.name)
    for other in list(bpy.context.scene.objects):
        if other != obj:
            bpy.data.objects.remove(other, do_unlink=True)
    obj.name = 'SM_M249_'+key
    obj.data.calc_loop_triangles()
    points = np.array([v.co[:] for v in obj.data.vertices])
    triangles = np.array([t.vertices[:] for t in obj.data.loop_triangles])
    np.savez(CACHE/(key+'.npz'), points=points, triangles=triangles)
    bpy.ops.wm.save_as_mainfile(filepath=str(CACHE/(key+'.blend')))


if __name__ == '__main__':
    CACHE.mkdir(parents=True, exist_ok=True)
    for model in MODELS:
        prepare(model)
