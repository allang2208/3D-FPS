"""Keep UVs intact; supply an adjacent-face basis where Mikk returns zero.

Only the FBX writer in this Blender process is wrapped, and restored on return.
No installed Blender code, textures or UV islands are modified.
"""
import bpy,numpy as np
from io_scene_fbx import export_fbx_bin as fbx

def export(mesh,path):
 mesh.calc_tangents(uvmap='UVMap')
 broken={l.index for l in mesh.loops if l.tangent.length<.5 or l.bitangent.length<.5}
 signs=np.array([l.bitangent_sign for l in mesh.loops])
 neighbours={}
 for l in mesh.loops:neighbours.setdefault(l.vertex_index,[]).append(l.index)
 state={};float_writer=fbx.elem_data_single_float64_array;int_writer=fbx.elem_data_single_int32_array
 def integers(parent,name,data):
  if name==b'NormalsIndex':state['indices']=np.asarray(data).copy()
  return int_writer(parent,name,data)
 def floats(parent,name,data):
  values=np.asarray(data).reshape(-1,3).copy() if name in (b'Normals',b'Binormals',b'Tangents') else data
  if name==b'Normals':state['normals']=values
  if name in (b'Binormals',b'Tangents'):
   normals=state['normals'][state['indices']]
   if name==b'Binormals':
    for i in broken:
     n=normals[i];n=n/max(np.linalg.norm(n),1e-12)
     choices=[j for j in neighbours[mesh.loops[i].vertex_index] if j not in broken]
     if not choices:choices=[j for j in range(i//3*3,i//3*3+3) if j not in broken]
     b=values[choices[0]].copy() if choices else np.eye(3)[np.argmin(np.abs(n))]
     b-=n*np.dot(n,b)
     if np.linalg.norm(b)<1e-6:
      b=np.eye(3)[np.argmin(np.abs(n))];b-=n*np.dot(n,b)
     values[i]=b/np.linalg.norm(b)
    state['binormals']=values.copy()
   else:
    for i in broken:
     t=np.cross(state['binormals'][i],normals[i])*(signs[i] or 1)
     values[i]=t/max(np.linalg.norm(t),1e-12)
   data=values.reshape(-1)
  return float_writer(parent,name,data)
 fbx.elem_data_single_float64_array=floats;fbx.elem_data_single_int32_array=integers
 try:
  bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 finally:
  fbx.elem_data_single_float64_array=float_writer;fbx.elem_data_single_int32_array=int_writer
 return len(broken)
