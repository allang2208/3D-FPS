"""Rebuild cuffs, a continuous waist yoke, and the ground-facing robe hem.

Starts from the saved Drape06 source; arm animation and object units are retained.
"""
import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921');OUT=ROOT/'Revision07'
sys.path.insert(0,str(Path(__file__).parent))
from author_drape04 import export
from garment_polish import smooth,mix,sleeve_weights
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Before/Authoring/WitchRebuilt_Master.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');rig.data.pose_position='REST'
rest={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
upper=bpy.data.objects['Witch_UpperRobe'];lower=bpy.data.objects['Witch_OriginalRobe_Render']
report={}

def frame(axis):
 axis=axis.normalized();x=Vector((0,0,1));x=(x-axis*x.dot(axis)).normalized();return x,axis.cross(x).normalized()

def path(side,d):
 a,b,c=[rest[n+'_'+side].translation for n in ('upperarm','lowerarm','hand')]
 l1=(b-a).length;l2=(c-b).length
 if d<l1:return a.lerp(b,d/l1),(b-a).normalized()
 return b.lerp(c,(d-l1)/l2),(c-b).normalized()

def along(p,side):
 a,b,c=[rest[n+'_'+side].translation for n in ('upperarm','lowerarm','hand')]
 candidates=[]
 for start,end,offset in ((a,b,0),(b,c,(b-a).length)):
  axis=end-start;t=max(0,min(1,(p-start).dot(axis)/axis.length_squared));center=start+axis*t
  candidates.append(((p-center).length,offset+t*axis.length))
 return min(candidates)[1]

# Remove the shredded distal sleeves at an anatomical seam. New cloth extends
# 4.5 cm under the retained upper sleeve; it does not cover an unremoved shell.
bm=bmesh.new();bm.from_mesh(upper.data);deform=bm.verts.layers.deform.verify()
groups={g.index:g.name for g in upper.vertex_groups};removed=[]
for v in bm.verts:
 side='l' if v.co.x>0 else 'r';a=rest['upperarm_'+side].translation;b=rest['lowerarm_'+side].translation
 arm=sum(w for i,w in v[deform].items() if groups.get(i,'').endswith('_'+side) and any(k in groups.get(i,'') for k in ('upperarm','lowerarm','hand')))
 if arm>.65 and abs(v.co.x)>.235 and along(v.co,side)>(b-a).length*.33+.045:removed.append(v)
report['removed_distal_sleeve_vertices']=len(removed)
bmesh.ops.delete(bm,geom=removed,context='VERTS')
# Remove isolated remnants created by the cut, not connected cape/hood details.
todo=set(bm.verts);pieces=[]
while todo:
 v=todo.pop();part={v};stack=[v]
 while stack:
  for e in stack.pop().link_edges:
   for n in e.verts:
    if n in todo:todo.remove(n);part.add(n);stack.append(n)
 pieces.append(part)
loose=[v for part in pieces if len(part)<32 for v in part]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bm.to_mesh(upper.data);bm.free()
mask=upper.data.color_attributes.get('SeamRepair') or upper.data.color_attributes.new(name='SeamRepair',type='FLOAT_COLOR',domain='CORNER')
for x in mask.data:x.color=(1,1,1,0)

def make_piece(name,verts,faces,uvs,weights):
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
 o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o)
 o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted()
 mesh.materials.append(upper.data.materials[0])
 for n in set(k for ws in weights for k in ws):o.vertex_groups.new(name=n)
 for i,ws in enumerate(weights):
  total=sum(ws.values())
  for n,w in ws.items():
   if w>1e-6:o.vertex_groups[n].add([i],w/total,'REPLACE')
 for name,mult in (('UVMap',1),('DetailUV',32)):
  layer=mesh.uv_layers.new(name=name)
  for poly in mesh.polygons:
   vals=[uvs[mesh.loops[j].vertex_index] for j in poly.loop_indices]
   wrap=max(u for u,v in vals)-min(u for u,v in vals)>.5
   for j,(u,v) in zip(poly.loop_indices,vals):layer.data[j].uv=((u+1 if wrap and u<.5 else u)*mult,v*mult)
 color=mesh.color_attributes.new(name='SeamRepair',type='FLOAT_COLOR',domain='CORNER')
 for x in color.data:x.color=(1,1,1,1)
 for p in mesh.polygons:p.use_smooth=True
 mod=o.modifiers.new('WitchRig','ARMATURE');mod.object=rig
 return o

def arm_weights(p,side):
 a=rest['lowerarm_'+side].translation;c=rest['hand_'+side].translation
 d=along(p,side);l1=(a-rest['upperarm_'+side].translation).length
 elbow=smooth((d-l1+.085)/.17);t=max(0,min(1,(p-a).dot(c-a)/(c-a).length_squared))
 helper=.65*t;blend=smooth((t-.25)/.5);cuff=.22*smooth((t-.8)/.2)
 return {'upperarm_'+side:1-elbow,'lowerarm_'+side:elbow*(1-cuff)*(1-helper),
         'lowerarm_twist_02_'+side:elbow*(1-cuff)*helper*(1-blend),
         'lowerarm_twist_01_'+side:elbow*(1-cuff)*helper*blend,'hand_'+side:elbow*cuff}

pieces=[]
for side in ('l','r'):
 a,b,c=[rest[n+'_'+side].translation for n in ('upperarm','lowerarm','hand')]
 start=(b-a).length*.20;end=(b-a).length+(c-b).length-.022
 n=48;rows=21;vv=[];ff=[];uv=[];ww=[]
 for j in range(rows+3):
  t=min(j,rows-1)/(rows-1);d=start+(end-start)*t
  if j>=rows:d=end-(j-rows)*.006
  center,axis=path(side,d);x,y=frame(axis)
  radius=.051+.019*math.sin(math.pi*t)-.003*smooth((t-.58)/.42)
  if j>=rows:radius-=.0025
  for i in range(n):
   angle=2*math.pi*i/n;direction=x*math.cos(angle)+y*math.sin(angle)
   fold=(.0035*math.sin(6*angle+.8*t)+.0018*math.sin(11*angle-1.3*t))*(.5+.5*math.sin(math.pi*t))
   drop=.012*(1-smooth((t-.65)/.35))*max(0,-direction.z)
   p=center+direction*(radius+fold+drop);vv.append(p);uv.append((i/n,t*.8));ww.append(arm_weights(p,side))
 for j in range(rows+2):
  for i in range(n):
   aa=j*n+i;bb=j*n+(i+1)%n;ff.append((aa,bb,bb+n,aa+n))
 pieces.append(make_piece('Witch_Cuff07_'+side,vv,ff,uv,ww))

# A folded inner yoke spans the actual missing waist interval. Its lower band
# and the skirt use the same pelvis support, with gradual spine blending above.
n=64;rows=23;vv=[];ff=[];uv=[];ww=[]
profile=[(.845,.208,.106,.13),(.955,.218,.120,.14),(1.055,.170,.118,.10),(1.155,.130,.126,.085),(1.255,.120,.077,.083),(1.355,.130,.060,.07)]
def waist_profile(z):
 for a,b in zip(profile,profile[1:]):
  if z<=b[0]:
   t=smooth((z-a[0])/(b[0]-a[0]));return [a[k]*(1-t)+b[k]*t for k in range(1,4)]
 return list(profile[-1][1:])
for j in range(rows):
 t=j/(rows-1);z=.845+.510*t;rx,front,back=waist_profile(z)
 for i in range(n):
  ang=2*math.pi*i/n;fold=(.014*math.sin(9*ang+.7*t)+.004*math.sin(17*ang-.5*t))*math.sin(math.pi*t)
  ry=front if math.sin(ang)<0 else back
  p=Vector(((rx+fold)*math.cos(ang),-.022+(ry+fold*.7)*math.sin(ang),z+.009*math.sin(3*ang)*math.sin(math.pi*t)))
  vv.append(p);uv.append((i/n,t))
  spine=smooth((p.z-1.025)/.24);ww.append({'pelvis':1-spine,'spine_02':spine*.45,'spine_03':spine*.55})
for j in range(rows-1):
 for i in range(n):
  aa=j*n+i;bb=j*n+(i+1)%n;ff.append((aa,bb,bb+n,aa+n))
pieces.append(make_piece('Witch_WaistYoke07',vv,ff,uv,ww))

# Blend retained central upper-cloth weights into the same waist anchor.
for v in upper.data.vertices:
 if abs(v.co.x)<.245 and v.co.z<1.15:
  strength=(1-smooth((v.co.z-1.00)/.15))*(1-smooth((abs(v.co.x)-.20)/.045))
  ws={upper.vertex_groups[g.group].name:g.weight for g in v.groups};ws=mix(ws,{'pelvis':1},strength)
  for g in upper.vertex_groups:g.remove([v.index])
  for name,w in ws.items():
   if name not in upper.vertex_groups:upper.vertex_groups.new(name=name)
   if w>1e-6:upper.vertex_groups[name].add([v.index],w,'REPLACE')
bpy.ops.object.select_all(action='DESELECT');upper.hide_set(False);upper.select_set(True)
for o in pieces:o.select_set(True)
bpy.context.view_layer.objects.active=upper;bpy.ops.object.join()
if upper.data.has_custom_normals:upper.data.normals_split_custom_set([(0,0,0)]*len(upper.data.loops))
upper.data.color_attributes.active_color=upper.data.color_attributes['SeamRepair']
upper.data.color_attributes.render_color_index=list(upper.data.color_attributes).index(upper.data.color_attributes['SeamRepair'])

# Replace the short torso lining in the area now covered by the continuous
# yoke. Merely moving it inward leaves the straight shirt edge visible in bends.
lining=bpy.data.objects['WitchRebuilt_Lining']
bm=bmesh.new();bm.from_mesh(lining.data)
oldshirt=[v for v in bm.verts if abs(v.co.x)<.18 and 1.06<v.co.z<1.34]
bmesh.ops.delete(bm,geom=oldshirt,context='VERTS');bm.to_mesh(lining.data);bm.free()

# Trim only the ground-facing ends. Keep broad worn panels, remove dragging
# needles, and form a thin turned edge rather than solidifying the whole robe.
bm=bmesh.new();bm.from_mesh(lower.data)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=Vector((0,0,.113)),plane_no=Vector((0,0,1)),clear_inner=True,clear_outer=False)
hem=[e for e in bm.edges if e.is_boundary and max(v.co.z for v in e.verts)<.1131]
report['trimmed_hem_edges']=len(hem)
if hem:
 result=bmesh.ops.extrude_edge_only(bm,edges=hem)
 for v in result['geom']:
  if isinstance(v,bmesh.types.BMVert):
   radial=Vector((v.co.x,v.co.y+.015,0));v.co-=radial.normalized()*.002;v.co.z+=.004
for v in bm.verts:
 if v.co.z<.27:
  blend=1-smooth((v.co.z-.113)/.157);ang=math.atan2(v.co.y+.015,v.co.x)
  v.co.z+=blend*(.007*math.sin(3*ang)+.003*math.sin(7*ang))
  radial=Vector((v.co.x,v.co.y+.015,0))
  if radial.length>.32:v.co-=radial.normalized()*(radial.length-.32)*blend
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(lower.data);bm.free()
for p in lower.data.polygons:p.use_smooth=True
if lower.data.has_custom_normals:lower.data.normals_split_custom_set([(0,0,0)]*len(lower.data.loops))

# Match the already inexpensive 1704-point proxies to the new cloth boundaries.
proxy=bpy.data.objects['WitchRebuilt_SimulationProxy']
for v in proxy.data.vertices:
 if v.co.z<.27:v.co.z+=(.113-.078)*(1-smooth((v.co.z-.078)/.192))
up=bpy.data.objects['WitchRebuilt_UpperSimulationProxy']
for v in up.data.vertices:
 if v.index<480:
  row=v.index//32;t=row/14;old=v.co.copy();v.co.z=.845+(.735)*t
  if v.co.z<1.355:
   rx,front,back=waist_profile(v.co.z);ang=math.atan2(old.y-.015,old.x)
   v.co.x=rx*math.cos(ang);v.co.y=-.022+(front if math.sin(ang)<0 else back)*math.sin(ang)
  spine=smooth((v.co.z-1.025)/.24)
  if v.co.z<1.355:
   for g in up.vertex_groups:g.remove([v.index])
   for name,w in {'pelvis':1-spine,'spine_02':spine*.45,'spine_03':spine*.55}.items():
    if name not in up.vertex_groups:up.vertex_groups.new(name=name)
    if w>1e-6:up.vertex_groups[name].add([v.index],w,'REPLACE')
 else:
  side='l' if v.index<820 else 'r';idx=v.index-(480 if side=='l' else 820);j=idx//20;i=idx%20
  a,b,c=[rest[n+'_'+side].translation for n in ('upperarm','lowerarm','hand')]
  end=(b-a).length+(c-b).length-.022;d=end*j/16;center,axis=path(side,d);x,y=frame(axis)
  t=max(0,min(1,(d-(b-a).length*.20)/(end-(b-a).length*.20)))
  radius=.051+.019*math.sin(math.pi*t)-.003*smooth((t-.58)/.42)
  direction=x*math.cos(2*math.pi*i/20)+y*math.sin(2*math.pi*i/20);v.co=center+direction*radius
  for g in up.vertex_groups:g.remove([v.index])
  for name,w in arm_weights(v.co,side).items():
   if name not in up.vertex_groups:up.vertex_groups.new(name=name)
   if w>1e-6:up.vertex_groups[name].add([v.index],w,'REPLACE')

# Mirror the repair-mask material in the editable source. Engine Surface07 uses
# the same mask to avoid sampling old torn albedo/normal charts on new panels.
mat=upper.data.materials[0];nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
attr=nodes.new('ShaderNodeVertexColor');attr.layer_name='SeamRepair'
source=bs.inputs['Base Color'].links[0].from_socket
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=9.;noise.inputs['Detail'].default_value=2.
mixcolor=nodes.new('ShaderNodeMixRGB');mixcolor.inputs[1].default_value=(.060,.052,.040,1);mixcolor.inputs[2].default_value=(.090,.078,.061,1);links.new(noise.outputs['Fac'],mixcolor.inputs[0])
blend=nodes.new('ShaderNodeMixRGB');links.new(attr.outputs['Alpha'],blend.inputs[0]);links.new(source,blend.inputs[1]);links.new(mixcolor.outputs[0],blend.inputs[2]);links.new(blend.outputs[0],bs.inputs['Base Color'])
if bs.inputs['Normal'].is_linked:
 normal=bs.inputs['Normal'].links[0].from_node
 if normal.type=='NORMAL_MAP':
  inv=nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1.;links.new(attr.outputs['Alpha'],inv.inputs[1])
  scale=nodes.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=.24;links.new(inv.outputs[0],scale.inputs[0]);links.new(scale.outputs[0],normal.inputs['Strength'])
  clothnoise=nodes.new('ShaderNodeTexNoise');clothnoise.inputs['Scale'].default_value=140.;clothnoise.inputs['Detail'].default_value=2.
  bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.17;bump.inputs['Distance'].default_value=.0012
  links.new(clothnoise.outputs['Fac'],bump.inputs['Height']);links.new(normal.outputs['Normal'],bump.inputs['Normal']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
rig['surface_revision']='Seams07';rig['drape_revision']='Drape07'
report.update(upper_vertices=len(upper.data.vertices),lower_vertices=len(lower.data.vertices),proxy_vertices=len(proxy.data.vertices)+len(up.data.vertices),actor_scale_changed=False,animation_changed=False)
export(rig,vertex_colors=True);rig.data.pose_position='POSE';bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/WitchRebuilt_Master.blend'))
(OUT/'authoring_result.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
