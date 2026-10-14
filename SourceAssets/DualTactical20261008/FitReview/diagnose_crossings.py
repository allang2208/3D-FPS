import bpy,bmesh,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;m=json.loads((O/'Repaired/manifest.json').read_text())
def geometry(key):
    e=m[key];bpy.ops.wm.open_mainfile(filepath=str(O/'Repaired'/(key+'.blend')));ob=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    old=json.loads((O/'Cache'/(e['family']+'-'+e['kind']+'.json')).read_text());h=json.loads((O/'Cache'/(key+'-host.json')).read_text());to_host=Matrix(h['host_to_canonical']).inverted()@Matrix(old['canonical'])@Matrix(e['canonical']).inverted()
    verts=[to_host@v.co for v in ob.data.vertices];faces=[list(p.vertices) for p in ob.data.polygons]
    return ob,verts,faces,BVHTree.FromPolygons(verts,faces),to_host
out={}
for key in ['HK416-laser-1','HK416-flashlight-1','HK416-flashlight-2']:
    ob,verts,faces,t,transform=geometry(key);h=json.loads((O/'Cache/HK416-host.json').read_text());ht=BVHTree.FromPolygons([Vector(v) for v in h['vertices']],h['faces']);cross={a for a,b in t.overlap(ht)}
    bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table();seen=set();groups=[]
    for v in bm.verts:
        if v in seen:continue
        seen.add(v);q=[v];vs=[];fs=set()
        while q:
            a=q.pop();vs.append(a);fs.update(f.index for f in a.link_faces)
            for edge in a.link_edges:
                b=edge.other_vert(a)
                if b not in seen:seen.add(b);q.append(b)
        if fs.intersection(cross):groups.append({'vertices':len(vs),'crossed_faces':len(fs.intersection(cross)),'materials':list({ob.data.materials[bm.faces[f].material_index].name for f in fs}),'bounds_mm':[[round(min(v.co[a] for v in vs)*1000,2) for a in range(3)],[round(max(v.co[a] for v in vs)*1000,2) for a in range(3)]]})
    out[key]=groups;bm.free()
ob,verts,faces,t,transform=geometry('M16-laser-1');names=[ob.data.materials[p.material_index].name for p in ob.data.polygons]
ob2,v2,f2,t2,tr2=geometry('M16-laser-2');hits=t.overlap(t2);idx={i for a,b in hits for i in faces[a]};idx2={i for a,b in hits for i in f2[b]}
out['M16']={'crossed_materials':list({names[a] for a,b in hits}),'bounds_slot1':[[round(min((transform.inverted()@verts[i])[a] for i in idx)*1000,2) for a in range(3)],[round(max((transform.inverted()@verts[i])[a] for i in idx)*1000,2) for a in range(3)]],'bounds_slot2':[[round(min(ob2.data.vertices[i].co[a] for i in idx2)*1000,2) for a in range(3)],[round(max(ob2.data.vertices[i].co[a] for i in idx2)*1000,2) for a in range(3)]]}
(O/'After/crossing-diagnosis.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
