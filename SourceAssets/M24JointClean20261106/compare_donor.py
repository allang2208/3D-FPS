from pathlib import Path
import bpy,bmesh,numpy as np,json
O=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(O.parent/'M24CarbonSpineGame20261104/M24_CarbonSpine_Fitted.blend')) as (av,ld):
    ld.objects=[n for n in av.objects if n.startswith('Donor receiver | ')]
old={o.name.split(' | ')[-1]:o for o in ld.objects}
with bpy.data.libraries.load(str(O.parent/'M24HorizontalStock20261106/M24_HorizontalStock.blend')) as (av,ld):
    ld.objects=[n for n in av.objects if n.startswith('SM_M24_CarbonSpine_')]
current={o.name.split('_')[-1]:o for o in ld.objects}
def triangles(ob,metal=None):
    me=ob.data;me.calc_loop_triangles();ns=np.array([n.vector[:] for n in me.corner_normals]);ps=np.array([ob.matrix_world@v.co for v in me.vertices]);rows={}
    for t in me.loop_triangles:
        if metal is not None and t.material_index!=metal:continue
        p=ps[t.vertices];keys=[tuple(q) for q in np.round(p,6)];key=tuple(sorted(keys));rows[key]={k:n for k,n in zip(keys,ns[t.loops])}
    return rows
report={}
for kind in ('Native','Advanced'):
    before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs'/(kind+'.fbx')),use_custom_normals=True)
    ob=next(o for o in set(bpy.data.objects)-before if o.type=='MESH')
    metal=next(i for i,m in enumerate(ob.data.materials) if 'MI_M24_metal_' in m.name)
    src=triangles(ob,metal);prior=triangles(old[kind]);angles=[]
    cur=triangles(current[kind],0);final_angles=[]
    for key,row in cur.items():
        if key in src and min(v[1] for v in key)>.03:
            for k,n in row.items():final_angles.append(float(np.degrees(np.arccos(np.clip(np.dot(n,src[key][k]),-1,1)))))
    for key,row in prior.items():
        if key in src:
            for k,n in row.items():angles.append(float(np.degrees(np.arccos(np.clip(np.dot(n,src[key][k]),-1,1)))))
    # Measure whether the previously used polar order follows real rim edges.
    bm=bmesh.new();bm.from_mesh(old[kind].data)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,0),plane_no=(0,1,0),clear_inner=True,dist=1e-8)
    bmesh.ops.remove_doubles(bm,verts=[v for v in bm.verts if abs(v.co.y)<2e-7],dist=3e-7)
    edges={e for e in bm.edges if e.is_boundary and all(abs(v.co.y)<2e-7 for v in e.verts)};pool={v for e in edges for v in e.verts};groups=[]
    while pool:
        todo=[next(iter(pool))];g=[]
        while todo:
            v=todo.pop()
            if v not in pool:continue
            pool.remove(v);g.append(v);todo.extend(e.other_vert(v) for e in v.link_edges if e in edges)
        groups.append(g)
    g=max(groups,key=lambda vs:np.prod(np.ptp(np.array([v.co[:] for v in vs])[:,[0,2]],axis=0)))
    p=np.array([v.co[:] for v in g])[:,[0,2]];center=(p.min(0)+p.max(0))/2;theta=np.arctan2(p[:,1]-center[1],p[:,0]-center[0]);order=np.argsort(theta);ordered=[g[i] for i in order]
    bad=sum(not any(e.other_vert(a)==b for e in a.link_edges if e in edges) for a,b in zip(ordered,ordered[1:]+ordered[:1]))
    report[kind]={'unchanged_source_triangle_matches':len(set(src)&set(prior)),'donor_triangles':len(prior),'corner_normal_difference_deg_percentiles':np.percentile(angles,[50,90,99,100]).tolist(),'corners_over_20deg':sum(a>20 for a in angles),'cut_components':[len(x) for x in groups],'polar_order_non_edges':bad,'outer_ring_vertices':len(g)}
    report[kind]['current_front_normal_difference_deg_percentiles']=np.percentile(final_angles,[50,90,99,100]).tolist()
    bm.free()
(O/'donor_diagnosis.json').write_text(json.dumps(report,indent=2));print('M24_DONOR_DIAGNOSIS',report)
