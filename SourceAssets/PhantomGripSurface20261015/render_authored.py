import bpy,json,numpy as np,sys
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
entry=O/'diagnose.py';exec(compile(entry.read_text(encoding='utf-8').split("for key in ['M4'")[0],str(entry),'exec'))
C=json.loads((O/'production.json').read_text());rp=O/'authored_surface_review.json';report=json.loads(rp.read_text()) if rp.exists() else {};key_arg=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else None
for key,row in C['assets'].items():
 if key_arg and key!=key_arg:continue
 old,scene=setup(key);mat=old.data.materials[0];before=np.array([tuple(old.matrix_world@v.co) for v in old.data.vertices]);old.hide_render=True
 with bpy.data.libraries.load(row['blend'],link=False) as (a,b):b.objects=a.objects
 ob=next(o for o in b.objects if o and o.type=='MESH');bpy.context.collection.objects.link(ob);ob.hide_set(False);ob.hide_render=False;me=ob.data;p=np.array([tuple(ob.matrix_world@v.co) for v in me.vertices]);uvstats={}
 for i,uv in enumerate(me.uv_layers):
  a=np.array([tuple(v.uv) for v in uv.data]).reshape(-1,3,2);cross=(a[:,1,0]-a[:,0,0])*(a[:,2,1]-a[:,0,1])-(a[:,1,1]-a[:,0,1])*(a[:,2,0]-a[:,0,0]);body=np.array([f.material_index==row['body_slot'] for f in me.polygons]);uvstats[i]=int(((abs(cross)<2e-14)&body).sum())
 report[key]={'before_bounds':[before.min(0).tolist(),before.max(0).tolist()],'after_bounds':[p.min(0).tolist(),p.max(0).tolist()],'body_collapsed_uv':uvstats,'zero_normals':int(sum(n.vector.length<.9 for n in me.corner_normals))}
 for i in range(len(me.materials)):me.materials[i]=mat
 scene.cycles.samples=24;scene.render.filepath=str(O/'Preview'/(key+'_authored.png'));bpy.ops.render.render(write_still=True)
 (O/'authored_surface_review.json').write_text(json.dumps(report,indent=2));print('PHANTOM_REVIEWED',key,flush=True)
