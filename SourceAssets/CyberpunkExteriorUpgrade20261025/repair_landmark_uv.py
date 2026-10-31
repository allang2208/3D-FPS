"""Re-export the five manufactured shells after the importer's UV tangent diagnostic."""
import bpy,ast,json,math
from pathlib import Path
R=Path(__file__).resolve().parent;PROJECT=R.parents[1];OLD=PROJECT/'SourceAssets/CyberpunkApartmentRebuild20261022'
bpy.ops.wm.open_mainfile(filepath=str(OLD/'RefinementV19/LuminousSkyline_Source.blend'));scene=bpy.context.scene
manifest=json.loads((R/'remainder.json').read_text());records=[r for r in manifest['meshes'] if not r['key'].startswith('Landmark_')]
out=R/'Meshes/RefinedUV';out.mkdir(parents=True,exist_ok=True)
tree=ast.parse((R/'author_remainder.py').read_text())
loop=next(n for n in tree.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='index')
exec(compile(ast.Module(body=[loop],type_ignores=[]),'landmark_fabrication_uv_repair','exec'),globals())
manifest['meshes']=records
(R/'remainder.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
(R/'landmark_uv_repair.json').write_text(json.dumps(dict(stage='source_repaired',reason='Non-degenerate UVs on new bevel faces')),encoding='utf8')
print('EXTERIOR_LANDMARK_UV_SOURCE_REPAIRED',flush=True)
