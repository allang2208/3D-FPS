"""Regular game-view cartridges and separate steel links, in the live 201 rig.
Blender background authoring. UE delivery uses explicit native-space buffers,
so FBX armature/unit conversion cannot rescale the belt a second time.
"""
import bpy,bmesh,json,gzip,math,collections
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent
S=json.loads((O/'source.json').read_text())
L=json.loads((O.parent/'BeltMotion49/layout.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
def matrix(t):return Matrix.LocRotScale(Vector(t['p']),Quaternion((t['q'][3],*t['q'][:3])),Vector(t['s']))
rest={b['name']:matrix(b['rest']) for b in S['bones']}
idle={b['name']:matrix(b['idle']) for b in S['bones']}
gun=idle['WPN_root']
start=Vector(L['guide_root'][1]);end=Vector(L['guide_root'][6])
# Keep both authored hand and pouch contacts. Free rounds use a regular arc.
centers=[]
for i in range(6):
 t=i/5;v=start.lerp(end,t)
 v.x-=.0027*math.sin(math.pi*t);v.y+=.0017*math.sin(math.pi*t)
 centers.append(v)
centers.append(end+(end-centers[4]))
# The upper run now goes past the side mouth into the space under the lid.
centers.extend([Vector((start.x-.0135,start.y,start.z-.0007)),Vector((start.x-.027,start.y,start.z-.0014))])
entry=Vector((start.x-.0405,start.y,start.z-.0021))
guide=[entry,centers[8],centers[7]]+centers[:7]
slots=[0,1,2,3,4,5,6,-1,-2]
def tangent(i):
 k=slots[i]+3
 return (guide[min(k+1,9)]-guide[max(k-1,0)]).normalized()
def frame(i):
 y=Vector((0,1,0));z=tangent(i);z=(z-y*z.dot(y)).normalized();x=y.cross(z)
 return Matrix((x,y,z)).transposed().to_4x4()
colors={'Case':(.48,.315,.105),'Copper':(.46,.19,.09),'Link':(.09,.105,.115),'Primer':(.28,.21,.095)}
rough={'Case':.31,'Copper':.3,'Link':.40,'Primer':.37}
mats={}
for name,color in colors.items():
 m=bpy.data.materials.new('B52_'+name);m.diffuse_color=(*color,1);m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=.95;bs.inputs['Roughness'].default_value=rough[name];mats[name]=m
parts=[]
def mesh_object(name,verts,faces,mat):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(mats[mat])
 for p in me.polygons:p.use_smooth=True
 # Smooth turned surfaces, keep the large end planes and stamped edges crisp.
 bm=bmesh.new();bm.from_mesh(me)
 for e in bm.edges:
  if len(e.link_faces)==2 and e.calc_face_angle()>.5:e.smooth=False
 bm.to_mesh(me);bm.free()
 uv=me.uv_layers.new(name='UVMap')
 for poly in me.polygons:
  for li in poly.loop_indices:
   p=me.vertices[me.loops[li].vertex_index].co
   uv.data[li].uv=(math.atan2(p.z,p.x)/(2*math.pi)+.5,(p.y+.03)/.06)
 return ob
def lathe(name,profile,mat,n=48):
 vs=[];rings=[];fs=[]
 for y,r in profile:
  ring=[]
  for k in range(n if r else 1):
   a=k*2*math.pi/n;ring.append(len(vs));vs.append((r*math.cos(a),y,r*math.sin(a)))
  rings.append(ring)
 for a,b in zip(rings,rings[1:]):
  for k in range(n):
   j=(k+1)%n
   if len(a)==1:fs.append((a[0],b[k],b[j]))
   elif len(b)==1:fs.append((a[k],b[0],a[j]))
   else:fs.append((a[k],b[k],b[j],a[j]))
 return mesh_object(name,vs,fs,mat)
case=lathe('Template_Case',[(-.029,0),(-.029,.0048),(-.0287,.00505),(-.0274,.00505),(-.0272,.0040),(-.0259,.0040),(-.0255,.00493),(-.0245,.00495),(.0047,.00455),(.006,.00442),(.0101,.00307),(.011,.003),(.014,.003),(.014,0)],'Case')
tip=lathe('Template_Projectile',[(.011,0),(.011,.00285),(.014,.00295),(.0165,.00293),(.019,.00265),(.0215,.00215),(.024,.00144),(.026,.00079),(.0273,.00031),(.028,0)],'Copper')
primer=lathe('Template_Primer',[(-.02912,0),(-.02912,.0018),(-.02904,.00192),(-.02895,.00192),(-.02895,0)],'Primer',32)
def clamp(y):
 vs=[];fs=[];n=36
 inner=.00487 if y<-.005 else .00463
 # Closed thick C shell, not a texture painted over the brass cartridge.
 for k in range(n+1):
  a=math.radians(38+284*k/n)
  for r,dy in [(inner,-.00135),(inner+.00064,-.00135),(inner+.00064,.00135),(inner,.00135)]:vs.append((r*math.cos(a),y+dy,r*math.sin(a)))
 for k in range(n):
  for j in range(4):fs.append((k*4+j,(k+1)*4+j,(k+1)*4+(j+1)%4,k*4+(j+1)%4))
 fs.extend([(3,2,1,0),(n*4,n*4+1,n*4+2,n*4+3)])
 return mesh_object('Template_LinkClamp',vs,fs,'Link')
templates=[case,tip,primer,clamp(-.013),clamp(.001)]
for y in [-.013,.001]:
 for sign in [-1,1]:
  bpy.ops.mesh.primitive_cube_add(size=1,location=(0,y,sign*.00595));ob=bpy.context.object;ob.name='Template_LinkBridge'
  ob.scale=(.0026,.00265,.0028);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
  bevel=ob.modifiers.new('Stamped edge','BEVEL');bevel.width=.00022;bevel.segments=2
  bpy.ops.object.modifier_apply(modifier=bevel.name);ob.data.materials.append(mats['Link'])
  for p in ob.data.polygons:p.use_smooth=False
  templates.append(ob)
buffers=[];bonecenters=[[],[]];locals_=[[],[]]
for side,prefix in enumerate(['','New_']):
 for i in range(9):
  bone=prefix+'LMG201_Belt_%02d'%i
  bonecenters[side].append(list(idle[bone].inverted()@(gun@centers[i])))
  rel=gun.inverted()@idle[bone];p,q,s=rel.decompose();locals_[side].append({'p':list(p),'q':[q.x,q.y,q.z,q.w],'s':list(s)})
  if side and i==6:continue
  xf=Matrix.Translation(centers[i])@frame(i)
  torest=rest[bone]@idle[bone].inverted()@gun@xf
  normalxf=torest.to_3x3().inverted().transposed()
  for template in templates:
   ob=template.copy();ob.data=template.data.copy();bpy.context.collection.objects.link(ob);ob.name=('New' if side else 'Old')+'_%02d_'%i+template.name.removeprefix('Template_')
   ob.matrix_world=xf;parts.append(ob)
   me=ob.data;me.calc_loop_triangles();role='Case' if template==primer else me.materials[0].name.removeprefix('B52_')
   row={'bone':bone,'role':role,'slot':'M_LMG201_Cloth33__'+('New' if side else 'Old')+'Belt_B52_'+role,'p':[],'n':[],'uv':[],'t':[], 'color':[.62,.67,.8,1] if template==primer else [1,1,1,1]}
   lookup={}
   for tri in me.loop_triangles:
    ids=[]
    for li in tri.loops:
     v=me.vertices[me.loops[li].vertex_index].co;n=me.corner_normals[li].vector
     uv=me.uv_layers.active.data[li].uv if me.uv_layers.active else Vector((v.x*100,v.z*100))
     key=(me.loops[li].vertex_index,*[round(x,6) for x in n],*[round(x,6) for x in uv])
     if key not in lookup:
      lookup[key]=len(row['p']);row['p'].append(list(torest@v));row['n'].append(list((normalxf@n).normalized()));row['uv'].append(list(uv))
     ids.append(lookup[key])
    row['t'].append(ids)
   buffers.append(row)
for ob in templates:bpy.data.objects.remove(ob,do_unlink=True)
with gzip.open(O/'mesh_buffers.json.gz','wt') as f:json.dump(buffers,f)
layout={'centers_root_m':[list(v) for v in centers],'guide_root_m':[list(v) for v in guide],
 'centers_bone_local':bonecenters,'idle_bone_local':locals_,'slot_by_cell':slots,
 'source_sha256':S['sha256'],'triangles':sum(len(b['t']) for b in buffers),'rounds_old':9,'rounds_new':8,
 'materials':{k:{'color':colors[k],'roughness':rough[k]} for k in ['Case','Copper','Link']}}
(O/'layout.json').write_text(json.dumps(layout,indent=2))
# Save only the authored cartridge/link meshes as an editable mother model.
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_BeltRebuild52.blend'))
print('BELT52_AUTHORED',layout['triangles'],len(buffers),flush=True)
