"""Locate the detached visor/band seam in the accepted cap author mesh."""
import bpy,json,math
from pathlib import Path
from mathutils.bvhtree import BVHTree
from mathutils import Vector
B=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008');R=B/'V14'
for d in ['Authoring','Delivery','Diagnosis','Logs']:(R/d).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(B/'V11/Authoring/SecurityServiceCap_Anatomical_V11.blend'))
cap=bpy.data.objects['SM_SecurityServiceCap_V11'];me=cap.data
adj=[[] for v in me.vertices]
for e in me.edges:
    a,b=e.vertices;adj[a].append(b);adj[b].append(a)
seen=set();groups=[]
for v in me.vertices:
    if v.index in seen:continue
    todo=[v.index];seen.add(v.index);ids=[]
    while todo:
        i=todo.pop();ids.append(i)
        for j in adj[i]:
            if j not in seen:seen.add(j);todo.append(j)
    groups.append(ids)
rows=[]
for ids in groups:
    p=[me.vertices[i].co for i in ids];vs=set(ids);faces=[f for f in me.polygons if f.vertices[0] in vs]
    rows.append({'vertices':len(ids),'faces':len(faces),'bounds':[[min(v[k] for v in p),max(v[k] for v in p)] for k in range(3)],
                 'materials':sorted({me.materials[f.material_index].name for f in faces}),'ids':ids})
rows.sort(key=lambda r:-r['vertices'])
band=next(r for r in rows if r['vertices']==640 and r['materials']==['Security_Leather'])
visor=next(r for r in rows if r['vertices']==1430 and r['materials']==['Security_Leather'])
vs=set(band['ids']);me.calc_loop_triangles();tri=[tuple(t.vertices) for t in me.loop_triangles if t.vertices[0] in vs]
tree=BVHTree.FromPolygons([v.co for v in me.vertices],tri,all_triangles=True)
seam=[]
for i in range(65):
    a=-1.43+2.86*i/64;p=Vector((.087*math.sin(a),-.042-.105*math.cos(a),1.748-.010*math.sin(a)**2));h=tree.find_nearest(p)
    seam.append({'angle':a,'visor_root':list(p),'band_nearest':list(h[0]),'distance_mm':h[3]*1000,
                 'below_band_mm':max(0.,1.745-p.z)*1000})
out={'mesh':cap.name,'islands':rows,'seam_samples':seam,'max_root_below_band_mm':max(s['below_band_mm'] for s in seam),
     'separate_band_and_visor':True,'rendered':False,'game_tested':False}
(R/'Diagnosis/hat_before.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('HAT_JOIN_SOURCE',json.dumps({'large_islands':[{k:v for k,v in r.items() if k!='ids'} for r in rows[:8]],'max_root_below_band_mm':out['max_root_below_band_mm']}),flush=True)
