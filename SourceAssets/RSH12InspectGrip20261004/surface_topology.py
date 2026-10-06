import sys,json,bmesh
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O))
from grip_scene import *
rig,D,profile,meta=load();p=pose(rig,D,profile,'inspect',D['clips']['inspect']['samples'][72]);skin=Skin(rig,'r')
_,points,dd=report(skin,p,meta,grip_trees()[0][1])
for f in ('hand','thumb','index','middle','ring','pinky'):
    mask=np.char.startswith(skin.labels,f);ids=np.flatnonzero(mask);i=ids[np.argmin(dd[mask])]
    print('DEEPEST',f,dd[i],points[i].tolist(),skin.labels[i],flush=True)
raw=json.loads((O.parent/'RSH12Integration20261003/canonical_parts.json').read_text())
for part in raw:
    if part['name'] not in ('9_l','7_l','11_l'):continue
    mesh=bpy.data.meshes.new('Solid');mesh.from_pydata(part['verts'],[],part['faces']);bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    boundary=[e for e in bm.edges if e.is_boundary]
    print('TOPOLOGY',part['name'],'boundary',len(boundary),'verts',len(bm.verts),'faces',len(bm.faces),flush=True)
    bmesh.ops.holes_fill(bm,edges=boundary,sides=0);bm.verts.ensure_lookup_table();bm.verts.index_update()
    (O/('solid_'+part['name']+'.json')).write_text(json.dumps(dict(verts=[list(v.co) for v in bm.verts],faces=[[v.index for v in f.verts] for f in bm.faces])))
