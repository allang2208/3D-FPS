"""Reprocess the approved Hunyuan reconstruction, retaining its geometry/UVs."""
from pathlib import Path
P=Path(__file__).parent
source=(P.parent/'prepare_model.py').read_text(encoding='utf-8')
source=source.replace("P/'PrismHandstop_Raw.blend'", "P.parent/'PrismHandstop_Raw.blend'")
source=source.replace("dec=o.modifiers.new", """# Smooth reconstruction noise before collapse, when the mesh is dense.
# The short radius retains the ribs and saddle silhouette.
if o.data.has_custom_normals:
 bpy.ops.mesh.customdata_custom_splitnormals_clear()
smooth=o.modifiers.new('Remove reconstruction ripples','SMOOTH')
smooth.factor=.55;smooth.iterations=8
bpy.ops.object.modifier_apply(modifier=smooth.name)
dec=o.modifiers.new""")
source=source.replace("for p in o.data.polygons:p.use_smooth=True", """for p in o.data.polygons:p.use_smooth=True
# Recalculate shading after reduction instead of retaining high-poly normals.
bm=bmesh.new();bm.from_mesh(o.data)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
for edge in bm.edges:
 edge.smooth=(not edge.is_manifold or edge.calc_face_angle()<math.radians(48))
bm.to_mesh(o.data);bm.free();o.data.update()
normal_mod=o.modifiers.new('Area weighted plane normals','WEIGHTED_NORMAL')
normal_mod.keep_sharp=True;normal_mod.weight=40
bpy.ops.object.modifier_apply(modifier=normal_mod.name)""")
source=source.replace('Separate left reconstruction, uniform scale, orientation, decimation; preserve generated UV and normal, graphite material calibration','Hunyuan left reconstruction; 8 passes local smoothing before 16k collapse; rebuilt sharp edges and area-weighted normals; original UVs; calibrated graphite materials; generated normal map intentionally unused')
source=source.replace('PRISM_PREPARE_PASS','PRISM_POLISH_PASS')
exec(compile(source,str(P/'generated_pipeline.py'),'exec'))
