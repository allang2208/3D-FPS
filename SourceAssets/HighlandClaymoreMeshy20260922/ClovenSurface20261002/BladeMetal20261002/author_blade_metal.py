"""Use the current blade's steel maps on the accepted arc-UV cloven wings."""
from pathlib import Path
import json
import shutil
import subprocess
import bpy
import numpy as np

P = Path(__file__).resolve().parent
PREVIOUS = P.parent
BASE = PREVIOUS.parent
P.mkdir(exist_ok=True)
(P / 'Textures').mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(PREVIOUS / 'Highland_ClovenGuard_ArcSurface20261002_Editable.blend'))
guard = bpy.data.objects['SM_Highland_Guard_Cloven_JunctionV5']
with bpy.data.libraries.load(str(BASE / 'JunctionBlendV5_20260927/Highland_ContinuousJunctionV5_Editable.blend'), link=False) as (available, selected):
    selected.objects = ['SM_Highland_Blade_factory_JunctionV5']
blade = selected.objects[0]
mesh = blade.data
mesh.calc_loop_triangles()
uv, points = [], []
for tri in mesh.loop_triangles:
    corners = np.array([mesh.vertices[v].co[:] for v in tri.vertices])
    center = corners.mean(axis=0)
    # Broad steel faces beside the center glyphs; leave bevel and guard out.
    if not (.18 < center[2] < .78 and .006 < abs(center[0]) < .026 and abs(tri.normal.y) > .82):
        continue
    uv.append([mesh.uv_layers[0].data[li].uv[:] for li in tri.loops])
    points.append(corners)
if not uv:
    raise RuntimeError('No blade steel faces available for material transfer')
np.savez_compressed(P / 'blade_steel_transfer.npz', uv=np.array(uv), points=np.array(points))
shutil.copy2(PREVIOUS / 'surface_transfer.npz', P / 'surface_transfer.npz')
subprocess.run(['py', '-3.11', str(P / 'author_textures.py')], check=True)

# Same four PBR inputs as the sword shader. Geometry and accepted continuous
# wing UVs stay exactly as authored in the previous surface revision.
material = next(m for m in guard.data.materials if m and m.name == 'M_ClovenWingSurface20261002')
nt = material.node_tree
nt.nodes.clear()
out = nt.nodes.new('ShaderNodeOutputMaterial')
bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
for key, socket in [('BaseColor', 'Base Color'), ('Normal', 'Normal'), ('Metallic', 'Metallic'), ('Roughness', 'Roughness')]:
    img = bpy.data.images.load(str(P / 'Textures' / ('T_ClovenBladeMetal_'+key+'.png')))
    img.colorspace_settings.name = 'sRGB' if key == 'BaseColor' else 'Non-Color'
    sample = nt.nodes.new('ShaderNodeTexImage')
    sample.image = img
    coords = nt.nodes.new('ShaderNodeUVMap')
    coords.uv_map = guard.data.uv_layers[0].name
    nt.links.new(coords.outputs['UV'], sample.inputs['Vector'])
    if key == 'Normal':
        normal = nt.nodes.new('ShaderNodeNormalMap')
        normal.uv_map = coords.uv_map
        nt.links.new(sample.outputs['Color'], normal.inputs['Color'])
        nt.links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
    else:
        nt.links.new(sample.outputs['Color'], bsdf.inputs[socket])
    img.pack()
guard['ClovenSurfaceRevision'] = 'BladeMetal_20261002'
guard['material_source'] = 'M_HighlandClaymoreSurface: actual blade steel PBR on continuous wing UV0'
bpy.data.objects.remove(blade, do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'Highland_ClovenGuard_BladeMetal20261002_Editable.blend'))
(P / 'author_receipt.json').write_text(json.dumps({'revision': 'BladeMetal_20261002',
    'geometry_and_uv_source': str(PREVIOUS / 'Highland_ClovenGuard_ArcSurface20261002_Editable.blend'),
    'metal_source': 'Highland sword blade native texture_0 BaseColor/Normal/Metallic/Roughness',
    'geometry_modified': False, 'uv_modified': False, 'tested': False}, indent=2), encoding='utf-8')
print('CLOVEN_BLADE_METAL_AUTHORED', flush=True)
