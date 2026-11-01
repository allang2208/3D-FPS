import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent;S=P.parent/'ModulesV1'
bpy.ops.wm.open_mainfile(filepath=str(S/'ThunderGodHammer_Modular_Editable.blend'))
rows=[]
for o in bpy.data.objects:
 if o.type!='MESH':continue
 rows.append(dict(name=o.name,location=list(o.location),bounds=[[min(v.co[a] for v in o.data.vertices) for a in range(3)],[max(v.co[a] for v in o.data.vertices) for a in range(3)]],materials=[dict(name=m.name,images=[n.image.filepath for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]) for m in o.data.materials]))
interfaces=json.loads((S/'interfaces.json').read_text(encoding='utf-8'))['parts']['head_mount']['interfaces']
summary=[]
for row in interfaces:
 pts=[p for e in row['segments_m'] for p in e]
 summary.append(dict(cut=row['cut'],segments=len(row['segments_m']),bounds=[[min(p[a] for p in pts) for a in range(3)],[max(p[a] for p in pts) for a in range(3)]]))
(P/'source_measurements.json').write_text(json.dumps(dict(meshes=rows,interfaces=summary),indent=2),encoding='utf-8')
print('SOURCE_READY',flush=True)
