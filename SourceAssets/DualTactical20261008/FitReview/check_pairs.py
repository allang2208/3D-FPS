"""Requested static assembly checks, with both actual slot transforms applied."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
manifest=json.loads((O/'Repaired/manifest.json').read_text())
geometry={};report={'body_crossings':{},'pair_crossings':{}}
for key,e in manifest.items():
    bpy.ops.wm.open_mainfile(filepath=str(O/'Repaired'/(key+'.blend')))
    ob=next(ob for ob in bpy.context.scene.objects if ob.type=='MESH')
    old=json.loads((O/'Cache'/(e['family']+'-'+e['kind']+'.json')).read_text())
    h=json.loads((O/'Cache'/(key+'-host.json')).read_text())
    to_host=Matrix(h['host_to_canonical']).inverted()@Matrix(old['canonical'])@Matrix(e['canonical']).inverted()
    verts=[to_host@v.co for v in ob.data.vertices];faces=[list(p.vertices) for p in ob.data.polygons]
    body_faces=[list(p.vertices) for p in ob.data.polygons if not any(w in ob.data.materials[p.material_index].name.lower() for w in ('bearing','collar','mount','gripmetal'))]
    host=json.loads((O/'Cache'/(e['family']+'-host.json')).read_text())
    hosttree=BVHTree.FromPolygons([Vector(v) for v in host['vertices']],host['faces'])
    bodytree=BVHTree.FromPolygons(verts,body_faces)
    hits=bodytree.overlap(hosttree)
    report['body_crossings'][key]={'triangle_pairs':len(hits),'body_faces':len(body_faces)}
    geometry[key]=BVHTree.FromPolygons(verts,faces)
for family in sorted({e['family'] for e in manifest.values()}):
    for a in ('laser','flashlight','blessed_laser'):
        for b in ('laser','flashlight','blessed_laser'):
            one=f'{family}-{a}-1';two=f'{family}-{b}-2'
            hits=geometry[one].overlap(geometry[two])
            report['pair_crossings'][one+'__'+two]=len(hits)
(O/'After/intersection-report.json').write_text(json.dumps(report,indent=2))
print('BODY_CROSSINGS',json.dumps({k:v['triangle_pairs'] for k,v in report['body_crossings'].items() if v['triangle_pairs']}))
print('PAIR_CROSSINGS',json.dumps({k:v for k,v in report['pair_crossings'].items() if v}))
