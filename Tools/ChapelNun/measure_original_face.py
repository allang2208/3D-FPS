"""Match original source triangle corners by UV and measure adaptation drift."""
import bpy,json,math
import numpy as np
from pathlib import Path
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115');O=N/'FaceDiagnosisR1'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(N/'MeshyHeadR1/Source/NunHead_R1_glb.glb'))
ob=next(o for o in bpy.data.objects if o.type=='MESH');bpy.context.view_layer.objects.active=ob;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);me=ob.data;me.calc_loop_triangles()
zoff=168.0523223876953-.94961101*15.8;raw=np.array([v.co[:] for v in me.vertices])*[15.8,-15.8,15.8]+[0,1.4,zoff]
key=lambda uv:(round(float(uv[0]),7),round(float(uv[1]),7))
loop_vertices=np.empty(len(me.loops),dtype=np.int32);me.loops.foreach_get('vertex_index',loop_vertices)
loop_uv=np.empty((len(me.loops),2),dtype=np.float32);me.uv_layers.active.data.foreach_get('uv',loop_uv.ravel());loop_uv[:,1]=1-loop_uv[:,1]
loop_n=np.empty((len(me.loops),3),dtype=np.float32);me.corner_normals.foreach_get('vector',loop_n.ravel());loop_n*=np.array([1,-1,1])
lookup={};normals={}
for vi,uv,n in zip(loop_vertices,loop_uv,loop_n):
 k=key(uv);lookup.setdefault(k,set()).add(int(vi));normals[k]=n
print('SOURCE_CORNER_LOOKUP_READY',len(lookup),flush=True)
d=json.loads((N/'RefinementR4/Authored/head.json').read_text());p=np.array(d['positions']);matches={}
for t,uv,ns,m in zip(d['triangles'],d['uv'],d['normals'],d['triangle_materials']):
 if m not in (0,2):continue
 for v,tex,n in zip(t,uv,ns):
  if v in matches:continue
  k=key(tex);ids=lookup.get(k,[])
  if not ids:continue
  idx=min(ids,key=lambda i:np.linalg.norm(p[v]-raw[i]));err=float(np.linalg.norm(p[v]-raw[idx]));matches[v]={'original':raw[idx].tolist(),'current':p[v].tolist(),'error_cm':err,'normal_error':float(np.linalg.norm(np.array(n)-normals[k]))}
regions={'mouth':[],'chin':[],'upper_face':[]}
for v,r in matches.items():
 x,y,z=r['original']
 if abs(x)<3.3 and y>6.5 and 149.2<z<153:regions['mouth'].append(r)
 if abs(x)<5.2 and y>4.7 and 145<z<149.2:regions['chin'].append(r)
 if y>3 and z>=153:regions['upper_face'].append(r)
report={}
for name,rows in regions.items():
 report[name]={'vertices':len(rows),'moved_over_0_01mm':sum(r['error_cm']>.001 for r in rows),'max_displacement_cm':max((r['error_cm'] for r in rows),default=0),'max_normal_error':max((r['normal_error'] for r in rows),default=0),'largest_changes':sorted(rows,key=lambda r:-r['error_cm'])[:5]}
report['first_bad_stage']='restore_original_face.py fit_neck modifies all vertices below z=149 cm, including anterior chin; UVs and old normals retained'
(O/'region_displacement.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
