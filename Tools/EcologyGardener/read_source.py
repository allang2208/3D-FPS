"""Read the existing researcher authoring mesh for garment construction."""
import bpy,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/EcologyGardener20261014/V01')
ROOT.mkdir(parents=True,exist_ok=True)
source='D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V05/Authoring/FacelessResearcher_V05.blend'
bpy.ops.wm.open_mainfile(filepath=source)
report={'source':source,'objects':[]}
for o in bpy.context.scene.objects:
    if o.type not in ('MESH','ARMATURE'):continue
    record={'name':o.name,'type':o.type,'hidden':o.hide_get()}
    if o.type=='MESH':
        p=[v.co for v in o.data.vertices]
        record.update(vertices=len(p),materials=[m.name if m else None for m in o.data.materials],
            bounds=[[min(v[i] for v in p),max(v[i] for v in p)] for i in range(3)],
            keys=len(o.data.shape_keys.key_blocks) if o.data.shape_keys else 0,
            outer_vertices=o.get('outer_vertex_count'))
    else:record['bones']=len(o.data.bones)
    report['objects'].append(record)
coat=bpy.data.objects['Researcher_LabCoat_Continuous'];outer=int(coat['outer_vertex_count'])
front=[p for p in coat.data.polygons if max(p.vertices)<outer and .81<p.center.z<1.40 and abs(p.center.x)<.1 and p.center.y<-.045]
report['coat_front']={'faces':len(front),'samples':[[list(p.center),list(p.normal),list(p.vertices)] for p in front[::max(1,len(front)//4)]]}
(ROOT/'source.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('GARDENER_SOURCE_READ '+json.dumps(report),flush=True)
