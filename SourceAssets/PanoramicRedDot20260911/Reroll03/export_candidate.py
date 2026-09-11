import bpy,json,struct,hashlib
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P/'reroll03_candidate.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type=='MESH':o.select_set(True);bpy.context.view_layer.objects.active=o
bpy.ops.export_scene.fbx(filepath=str(P/'reroll03_candidate.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False)
raw=next(P.glob('reroll03_raw*.glb'))
with raw.open('rb') as f:
 f.read(12);length,kind=struct.unpack('<II',f.read(8));d=json.loads(f.read(length))
tri=sum(d['accessors'][p['indices']]['count']//3 for m in d['meshes'] for p in m['primitives'])
report=json.loads((P/'reroll03_mesh_report.json').read_text())
record={'status':'rerolled_reviewed_candidate','prompt_id':'890b097f-68ec-405c-9b40-684e0510732b','raw_triangles':tri,'master_triangles':sum(m['triangles'] for m in report['meshes']),'generation_seconds':220.921,'input':'reference_white.png','visual_findings':['Large side cavities substantially reduced; continuous frame and open window','Base planes substantially cleaner than first result','Inferred buttons and dials differ in placement; small surface waviness remains'],'game_integrated':False,'files':{}}
for f in P.iterdir():
 if f.suffix in ['.glb','.fbx','.blend']:record['files'][f.name]={'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
(P/'review_result.json').write_text(json.dumps(record,indent=2));print('REROLL_EXPORT_PASS',tri,record['master_triangles'])
