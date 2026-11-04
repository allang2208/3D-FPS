"""Read current Blender inputs and sample baked UV0 masks on the actual surfaces."""
import bpy,bmesh,json
import numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
S=P.parents[1]/'SourceAssets/OneHandAxe20261101/CommonRunes20261104'
source=json.loads((S/'sources.json').read_text('utf-8'))
out={'heads':[],'errors':[],'rendered':False}
for head in source['heads']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(head['blend'],link=False) as (a,b):b.objects=[head['object']]
    obj=b.objects[0];mesh=obj.data;mesh.calc_loop_triangles()
    bm=bmesh.new();bm.from_mesh(mesh)
    row={'id':head['id'],'triangles':len(mesh.loop_triangles),'boundary_edges':sum(e.is_boundary for e in bm.edges),
         'nonmanifold_nonboundary':sum(not e.is_manifold and not e.is_boundary for e in bm.edges),
         'tiny_faces_below_1e14_m2':sum(f.calc_area()<1e-14 for f in bm.faces),
         'zero_area_faces':sum(f.calc_area()==0 for f in bm.faces),
         'minimum_triangle_area_m2':min(f.calc_area() for f in bm.faces),'masks':[]}
    bm.free()
    triangles=list(mesh.loop_triangles)
    xyz=np.array([[mesh.vertices[v].co[:] for v in t.vertices] for t in triangles]).mean(axis=1)
    uv=np.array([[mesh.uv_layers[0].data[li].uv[:] for li in t.loops] for t in triangles]).mean(axis=1)
    normals=np.array([t.normal[:] for t in triangles])
    plan=json.loads((S/(head['kind']+'.json')).read_text('utf-8'))
    for rune in plan['placements']:
        img=bpy.data.images.load(rune['mask']);w,h=img.size
        pixels=np.empty(w*h*4,dtype=np.float32);img.pixels.foreach_get(pixels)
        pixels=pixels.reshape(h,w,4)
        coords=np.clip((uv*np.array([w,h])).astype(int),[0,0],[w-1,h-1])
        ink=pixels[coords[:,1],coords[:,0],0]>.5
        record={'rune':rune['id'],'ink_triangles':int(ink.sum()),'sides':[]}
        x,z=rune['center_m'];width,height=rune['width_m'],rune['height_m']
        for side in (-1,1):
            points=xyz[ink&(normals[:,1]*side>.9)]
            if len(points):
                bounds=[points[:,[0,2]].min(axis=0).tolist(),points[:,[0,2]].max(axis=0).tolist()]
                within=bool(np.all(np.abs(points[:,0]-x)<width/2+.002) and np.all(np.abs(points[:,2]-z)<height/2+.002))
                record['sides'].append({'side':side,'samples':len(points),'bounds_xz_m':bounds,'inside_authored_body_window':within})
                if not within:out['errors'].append(head['id']+'/'+rune['id']+': ink outside body window')
            else:out['errors'].append(head['id']+'/'+rune['id']+': empty face '+str(side))
        row['masks'].append(record)
    if row['zero_area_faces'] or row['nonmanifold_nonboundary']:out['errors'].append(head['id']+': invalid topology')
    out['heads'].append(row)
out['passed']=not out['errors']
(P/'geometry.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('HATCHET_GEOMETRY_AUDIT '+str(out['passed'])+' '+str(out['errors']),flush=True)
