import bpy,numpy as np,json
from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\SourceAssets\TacticalDevices20260913')
bpy.ops.wm.open_mainfile(filepath=str(p/'M4/laser/Editable.blend'));o=bpy.data.objects['SM_TacticalDevice'];m=o.data.materials[0];bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');im=next(n.image for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and any(l.to_socket==bs.inputs['Base Color'] for l in n.outputs['Color'].links));w,h=im.size;px=np.empty(w*h*4,np.float32);im.pixels.foreach_get(px);px=px.reshape(h,w,4);points=[]
for f in o.data.polygons:
 if f.material_index:continue
 for li in f.loop_indices:
  uv=o.data.uv_layers[0].data[li].uv;c=px[min(h-1,max(0,int(uv.y*h))),min(w-1,max(0,int(uv.x*w)))]
  if c[0]>.15 and c[0]>c[1]*1.8 and c[0]>c[2]*1.8:points.append(list(o.data.vertices[o.data.loops[li].vertex_index].co))
r={'red_center':np.mean(points,axis=0).tolist(),'red_count':len(points),'emitter':list(bpy.data.objects['SOCKET_Emitter'].location)};(p/'laser_axis_source.json').write_text(json.dumps(r,indent=2));print(r,flush=True)
