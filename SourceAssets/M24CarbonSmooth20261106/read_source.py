from pathlib import Path
import bpy,numpy as np,json,bmesh
O=Path(__file__).resolve().parent
rows={}
for folder,filename in [('M24StockJunctionR2_20261105','M24_Meshy_JunctionR2.blend'),('M24CarbonFlush20261106','M24_Carbon_DirectFlush.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(O.parent/folder/filename),use_scripts=False)
    report=[]
    for ob in bpy.data.collections['Native | fitted to M24'].objects:
        me=ob.data;item={'object':ob.name,'uv':[],'materials':[m.name for m in me.materials]}
        mids=np.empty(len(me.loops),int)
        for p in me.polygons:mids[p.loop_indices]=p.material_index
        for uv in me.uv_layers:
            a=np.array([d.uv[:] for d in uv.data])
            item['uv'].append({'name':uv.name,'active':uv==me.uv_layers.active,'by_material':{me.materials[i].name:{'min':a[mids==i].min(0).tolist(),'max':a[mids==i].max(0).tolist(),'zero_fraction':float(np.mean(np.linalg.norm(a[mids==i],axis=1)<1e-7))} for i in np.unique(mids)}})
        if 'Meshy carbon' in ob.name:
            me.calc_loop_triangles()
            for y in (-.110,-.120,-.130):
                bm=bmesh.new();bm.from_mesh(me)
                bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,y,0),plane_no=(0,1,0),dist=1e-8,clear_outer=True)
                vv=[v for v in bm.verts if abs(v.co.y-y)<2e-7];bmesh.ops.remove_doubles(bm,verts=vv,dist=3e-6)
                edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y-y)<2e-7 for v in e.verts)]
                pool=set(v for e in edges for v in e.verts);parts=[]
                while pool:
                    todo=[next(iter(pool))];part=[]
                    while todo:
                        v=todo.pop()
                        if v not in pool:continue
                        pool.remove(v);part.append(v.co[:]);todo.extend(e.other_vert(v) for e in v.link_edges if e in edges)
                    p=np.array(part);parts.append({'count':len(p),'min':p.min(0).tolist(),'max':p.max(0).tolist()})
                item[str(y)]=parts;bm.free()
        report.append(item)
    rows[folder]=report
(O/'source_read.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
