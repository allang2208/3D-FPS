from pathlib import Path
import bpy,numpy as np,json,gzip
O=Path(__file__).resolve().parent
R={}
def rays(p,f,m,slots):
    tri=p[f];a=tri[:,0];b=tri[:,1]-a;c=tri[:,2]-a
    den=b[:,0]*c[:,1]-b[:,1]*c[:,0];usable=np.abs(den)>1e-12
    out={}
    for y in (.110,.125,.150,.175,.200,.225,.250,.275):
        for x in (0.,.008,-.008):
            d=np.array([x,y])-a[:,:2]
            u=np.divide(d[:,0]*c[:,1]-d[:,1]*c[:,0],den,out=np.zeros(len(den)),where=usable)
            v=np.divide(b[:,0]*d[:,1]-b[:,1]*d[:,0],den,out=np.zeros(len(den)),where=usable)
            use=np.where(usable&(u>=-1e-5)&(v>=-1e-5)&(u+v<=1.00001))[0]
            z=a[use,2]+u[use]*b[use,2]+v[use]*c[use,2]
            out[f'{x*1000:.0f},{y*1000:.0f}']=[[round(zz*1000,3),slots[int(m[i])]] for i,zz in sorted(zip(use,z),key=lambda k:k[1],reverse=True) if .09<zz<.146]
    return out
bpy.ops.wm.read_factory_settings(use_empty=True)
for name in ('advanced_action','advanced_front'):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.fbx(filepath=str(O/'Inputs'/(name+'.fbx')))
    ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=ob.data;me.calc_loop_triangles()
    p=np.array([ob.matrix_world@v.co for v in me.vertices]);f=np.array([t.vertices for t in me.loop_triangles]);m=np.array([t.material_index for t in me.loop_triangles])
    R[name]=rays(p,f,m,[x.name for x in me.materials])
h=json.load(gzip.open(O/'Inputs/host.json.gz','rt'))
R['host']=rays(np.array(h['positions'])*[.01,-.01,.01],np.array(h['triangles']),np.array(h['material_ids']),[m['slot'] for m in h['materials']])
(O/'rail_profiles.json').write_text(json.dumps(R,indent=2))
for k,r in R.items():print(k,{p:r[p] for p in ('0,125','8,125','0,175','8,175','0,250','8,250')})
