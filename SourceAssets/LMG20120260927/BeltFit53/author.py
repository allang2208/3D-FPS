"""Keep B52 cartridges; add articulated connecting links and a buried pouch tail."""
import bpy,json,gzip,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
raw=json.loads((O/'source.json').read_text())
def unpack(v):return {'p':v[:3],'q':v[3:7],'s':v[7:]}
S={**raw,'bones':[{'name':b['name'],'index':b['index'],'rest':unpack(b['rest']),'idle':unpack(raw['idle'][b['name']])} for b in raw['bones']],'triangles_by_slot':raw['counts']}
(O/'source_compat.json').write_text(json.dumps(S,indent=2))
src=(O.parent/'BeltRebuild52/author.py').read_text().split('buffers=[];')[0]
src=src.replace("S=json.loads((O/'source.json').read_text())","S=json.loads((O/'source_compat.json').read_text())")
exec(compile(src,str(O/'author.py'),'exec'),globals())
for ob in list(templates):
 if ob.name.startswith('Template_LinkBridge'):templates.remove(ob);bpy.data.objects.remove(ob,do_unlink=True)
# Keep the buried run inside the actual pouch, rather than extrapolating the
# exposed curve forward until cartridge bases puncture the cloth wall.
for c in centers:c.y=centers[0].y
step=Vector((0,0,centers[6].z-centers[5].z));centers[6].x=.040
centers.extend([centers[6]+step,centers[6]+5*step,centers[6]+2*step,centers[6]+3*step,centers[6]+4*step])
guide=[entry,centers[8],centers[7]]+centers[:7]+[centers[i] for i in [9,11,12,13,10]]
slots=[0,1,2,3,4,5,6,-1,-2,7,11,8,9,10]
order=[8,7,0,1,2,3,4,5,6,9,11,12,13,10]
pairs=list(zip(order,order[1:]+order[:1]))
def tangent(i):
 k=slots[i]+3;return (guide[min(k+1,len(guide)-1)]-guide[max(k-1,0)]).normalized()
def frame(i):
 y=Vector((0,1,0));z=tangent(i);z=(z-y*z.dot(y)).normalized();return Matrix((y.cross(z),y,z)).transposed().to_4x4()
def connector(length):
 vs=[];fs=[]
 # Two thick side links meet the cartridge clamps, including through bends.
 for y in [-.013,.001]:
  base=len(vs)
  for z in [-length/2-.00065,length/2+.00065]:
   for x,dy in [(.0047,-.0013),(.0061,-.0013),(.0061,.0013),(.0047,.0013)]:vs.append((x,y+dy,z))
  fs.extend([tuple(base+j for j in f) for f in [(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])
 return mesh_object('Connector',vs,fs,'Link')
buffers=[];bonecenters=[[],[]];locals_=[[],[]];axes=[[],[]];linkcenters=[[],[]];linklocals=[[],[]];linkframes=[];linklengths=[]
def tr(m):
 p,q,s=m.decompose();return {'p':list(p),'q':[q.x,q.y,q.z,q.w],'s':list(s)}
def export(ob,xf,bone,slot,role,color=[1,1,1,1]):
 torest=rest[bone]@idle[bone].inverted()@gun@xf;normalxf=torest.to_3x3().inverted().transposed()
 ob.matrix_world=xf;me=ob.data;me.calc_loop_triangles();row={'bone':bone,'role':role,'slot':slot,'p':[],'n':[],'uv':[],'t':[],'color':color};lookup={}
 for t in me.loop_triangles:
  inds=[]
  for li in t.loops:
   v=me.vertices[me.loops[li].vertex_index].co;n=me.corner_normals[li].vector;uv=me.uv_layers.active.data[li].uv
   key=(me.loops[li].vertex_index,*[round(x,6) for x in n],*[round(x,6) for x in uv])
   if key not in lookup:
    lookup[key]=len(row['p']);row['p'].append(list(torest@v));row['n'].append(list((normalxf@n).normalized()));row['uv'].append(list(uv))
   inds.append(lookup[key])
  row['t'].append(inds)
 buffers.append(row)
for side,prefix in enumerate(['','New_']):
 label='New' if side else 'Old';slot='M_LMG201_Cloth33__'+label+'Belt_B53_'
 for i in range(14):
  bone=prefix+'LMG201_Belt_%02d'%i
  bonecenters[side].append(list(idle[bone].inverted()@(gun@centers[i])))
  locals_[side].append(tr(gun.inverted()@idle[bone]))
  axes[side].append(list((idle[bone].to_3x3().inverted()@gun.to_3x3()@Vector((0,1,0))).normalized()))
  if side and i==10:continue
  xf=Matrix.Translation(centers[i])@frame(i)
  for template in templates:
   ob=template.copy();ob.data=template.data.copy();bpy.context.collection.objects.link(ob);ob.name=label+'_%02d_'%i+template.name.removeprefix('Template_')
   role='Case' if template==primer else template.data.materials[0].name.removeprefix('B52_')
   export(ob,xf,bone,slot+role,role,[.62,.67,.8,1] if template==primer else [1,1,1,1])
 for k,(a,b) in enumerate(pairs):
  bone=prefix+'LMG201_Belt_Link_%02d'%k
  center=(centers[a]+centers[b])/2;z=(centers[b]-centers[a]).normalized();y=Vector((0,1,0));z=(z-y*z.dot(y)).normalized();rot=Matrix((y.cross(z),y,z)).transposed().to_4x4();xf=Matrix.Translation(center)@rot
  length=(centers[b]-centers[a]).length if k<13 else (centers[4]-centers[5]).length
  linkcenters[side].append(list(idle[bone].inverted()@(gun@center)));linklocals[side].append(tr(gun.inverted()@idle[bone]))
  if not side:linkframes.append(tr(rot)['q']);linklengths.append(length)
  if side and k>=12:continue
  ob=connector(length);ob.name=label+'_Joint_%02d'%k
  export(ob,xf,bone,slot+'Link','Link')
  if k==13:ob.hide_render=True;ob.hide_set(True)
for ob in templates:bpy.data.objects.remove(ob,do_unlink=True)
with gzip.open(O/'mesh_buffers.json.gz','wt') as f:json.dump(buffers,f)
layout={'centers_root_m':[list(x) for x in centers],'guide_root_m':[list(x) for x in guide],'centers_bone_local':bonecenters,'idle_bone_local':locals_,'axis_bone_local':axes,'slot_by_cell':slots,'pairs':pairs,'link_centers_bone_local':linkcenters,'link_idle_bone_local':linklocals,'link_frames_root':linkframes,'link_lengths_root':linklengths,'source_sha256':S['sha256'],'triangles':sum(len(b['t']) for b in buffers)}
(O/'layout.json').write_text(json.dumps(layout,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_BeltFit53.blend'))
print('B53_MODEL',layout['triangles'],flush=True)
