"""PKM Belt08: density, articulated links, private rig tracks and exports.

All dimensions are visual asset parameters, not firearm construction data.
The preceding weapon/arms animation channels are retained without rewriting.
"""
import bpy,bmesh,json,math,ast,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;R=O.parent;PRE=R/'Bipod07';E=O/'Exports';T=O/'Textures'
E.mkdir(exist_ok=True);T.mkdir(exist_ok=True);sys.path.insert(0,str(O))
from belt_dynamics import BeltDynamics,project,smooth
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(PRE/'PKM_Gameplay_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['PKM_Manny_Rig'];s.render.fps=60
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
B=r.data.bones['WPN_root'].matrix_local@fit;Binv=B.inverted()
old=[Vector(x['center']) for x in json.loads((R/'mechanics_inputs.json').read_text())['cartridges']]
clips=json.loads((PRE/'authoring.json').read_text())['clips']
with bpy.data.libraries.load(str(PRE/'PKM_Manny_Reload_Editable.blend'),link=False) as (src,dst):
 dst.actions=[n for n in ['PKM_Idle','PKM_Reload_Normal','PKM_Reload_Empty'] if n not in bpy.data.actions]
names={k:('PKM_Reload_Empty' if k=='reload_empty' else 'PKM_Reload_Normal' if k=='reload' else 'PKM_Game_'+k) for k in clips}
names['source_idle']='PKM_Idle'
def action(a):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def activate(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
def trx(v):return Matrix.Translation(v)
def frame_matrix(center,direction):
 x=direction.normalized();y=Vector((0,1,0));z=x.cross(y).normalized();y=z.cross(x).normalized()
 m=Matrix((x,y,z)).transposed().to_4x4();m.translation=center;return m

def spline(points):
 out=[]
 for i in range(len(points)-1):
  a=points[max(0,i-1)];b=points[i];c=points[i+1];d=points[min(len(points)-1,i+2)]
  for j in range(64):
   u=j/64;out.append((2*b+(-a+c)*u+(2*a-5*b+4*c-d)*u*u+(-a+3*b-3*c+d)*u*u*u)*.5)
 out.append(points[-1].copy());return out
def resample(points,segments):
 lengths=[0.0]
 for a,b in zip(points,points[1:]):lengths.append(lengths[-1]+(b-a).length)
 out=[];j=0
 for i in range(segments+1):
  d=lengths[-1]*i/segments
  while j<len(lengths)-2 and lengths[j+1]<d:j+=1
  out.append(points[j].lerp(points[j+1],(d-lengths[j])/(lengths[j+1]-lengths[j])))
 return out,lengths[-1]
exposed,arc=resample(spline(old[:6]),8)
inside_dense=spline(old[5:]);inside_arc=sum((b-a).length for a,b in zip(inside_dense,inside_dense[1:]))
inside,_=resample(inside_dense,round(inside_arc/(arc/8)))
centers=exposed+inside[1:];N=len(centers);end=len(exposed)-1
lengths=[(b-a).length for a,b in zip(centers,centers[1:])]
frames=[frame_matrix(p,(centers[min(i+1,N-1)]-centers[max(0,i-1)])) for i,p in enumerate(centers)]
layout={'centers':[list(c) for c in centers],'count':N,'exposed_count':end+1,'inlet_index':end,'exposed_arc_mm':arc*1000,'center_distances_mm':[d*1000 for d in lengths], 'single_round_dimensions_unchanged':True,'source':'Bipod07','visual_parameters_only':True}
(O/'belt_layout.json').write_text(json.dumps(layout,indent=2))
print('BELT08_LAYOUT',N,end+1,arc*1000,flush=True)

# Cache original parent motion and handled endpoints before changing belt rest poses.
samples={};oldrest={b.name:b.matrix_local.copy() for b in r.data.bones}
for key,name in names.items():
 a=bpy.data.actions[name];action(a);a.use_fake_user=True;samples[key]=[]
 for f in range(round(float(a.frame_range[1]))+1):
  s.frame_set(f);bpy.context.view_layer.update();W=r.pose.bones['WPN_root'].matrix@fit
  row={'W':W.copy()}
  for prefix in ['', 'New_']:
   root=prefix+'PKM_BeltRoot';box=prefix+'PKM_Box'
   row[prefix]={'root':r.pose.bones[root].matrix.copy(),'box':W.inverted()@r.pose.bones[box].matrix@oldrest[box].inverted()@B,
                'tip':W.inverted()@r.pose.bones[prefix+'PKM_Belt_00'].matrix.translation}
  samples[key].append(row)
 print('BELT08_CAPTURE',key,len(samples[key]),flush=True)

# Copy the original cartridge parts with their existing UVs and custom normals.
prototypes=[]
for i in range(3):
 original=bpy.data.objects[f'PKM_Part_{i:03}'];prototypes.append(original.copy());prototypes[-1].data=original.data.copy()
for ob in list(s.objects):
 bone=ob.get('mechanical_bone','').removeprefix('New_')
 if ob.type=='MESH' and bone.startswith('PKM_Belt_'):bpy.data.objects.remove(ob,do_unlink=True)

# Two slim C-clips, edge thickness, rear tie and articulated bridge strips.
# Their source shape is made around a rigid cartridge axis, not stretched over it.
def geometry(name,vertices,faces):
 me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update()
 ob=bpy.data.objects.new(name,me);s.collection.objects.link(ob)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
 for p in me.polygons:p.use_smooth=True
 bevel=ob.modifiers.new('Thin edge roll','BEVEL');bevel.width=.00016;bevel.segments=2
 bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(35)
 normal=ob.modifiers.new('Weighted surface normals','WEIGHTED_NORMAL');normal.keep_sharp=True
 activate([ob])
 for mod in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
 return ob
def box(v,f,c,size):
 base=len(v)
 for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]:v.append((c[0]+x*size[0]/2,c[1]+y*size[1]/2,c[2]+z*size[2]/2))
 f.extend(tuple(base+i for i in face) for face in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
v=[];f=[]
for y,radius in [(-.011,.0059),(.011,.00625)]:
 start=len(v);steps=32
 for j in range(steps+1):
  theta=math.radians(-45+270*j/steps)
  for rr,yy in [(radius,y-.0036),(radius+.0006,y-.0036),(radius+.0006,y+.0036),(radius,y+.0036)]:v.append((rr*math.cos(theta),yy,rr*math.sin(theta)))
 for j in range(steps):
  for k in range(4):f.append((start+j*4+k,start+j*4+(k+1)%4,start+(j+1)*4+(k+1)%4,start+(j+1)*4+k))
 f.extend([(start+3,start+2,start+1,start),(start+steps*4,start+steps*4+1,start+steps*4+2,start+steps*4+3)])
box(v,f,(0,0,.00635),(.0042,.029,.00065))
clip=geometry('Belt08_ClipPrototype',v,f)
v=[];f=[];pitch=arc/8
for y in [-.011,.011]:box(v,f,(0,y,-.0048),(pitch+.001,.0042,.00075))
box(v,f,(0,0,-.0048),(.0034,.0262,.00075))
bridge=geometry('Belt08_BridgePrototype',v,f)

# Bake the same QBZ coating recipe on dedicated link UVs. Existing cartridges
# retain their original UVs, and the weapon's completed atlas remains untouched.
source=ast.parse((R.parent/'QBZ191Hero20260913/build.py').read_text())
fn=next(x for x in source.body if isinstance(x,ast.FunctionDef) and x.name=='material')
env={'bpy':bpy};exec(compile(ast.Module(body=[fn],type_ignores=[]),'qbz_material','exec'),env)
mat=env['material']('AUTH_Belt08_Link',(.025,.029,.033),.72,.30)
for ob in [clip,bridge]:
 ob.data.materials.append(mat);ob.data.uv_layers.new(name='PKM_QBZ_SurfaceUV')
activate([clip,bridge]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.018,scale_to_bounds=True);bpy.ops.object.mode_set(mode='OBJECT')
activate([clip,bridge]);bpy.ops.object.duplicate();bpy.ops.object.join();baker=bpy.context.object
s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.use_clear=True;s.render.bake.margin=8
s.render.bake.use_selected_to_active=False;s.render.bake.normal_space='TANGENT'
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='OPTIX'
if any(d.use for d in prefs.devices):s.cycles.device='GPU'
nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
emit=nodes.new('ShaderNodeEmission');target=nodes.new('ShaderNodeTexImage');nodes.active=target;maps={}
for channel,socket in [('BaseColor',shader.inputs['Base Color'].links[0].from_socket),('ORM',nodes[mat['bake_orm_node']].outputs[0]),('Normal',None)]:
 im=bpy.data.images.new('T_PKM_Belt08_'+channel,width=1024,height=1024,alpha=False);im.colorspace_settings.name='sRGB' if channel=='BaseColor' else 'Non-Color';target.image=im
 if socket:links.new(socket,emit.inputs[0]);links.new(emit.outputs[0],out.inputs[0])
 else:links.new(shader.outputs[0],out.inputs[0])
 bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'EMIT')
 im.filepath_raw=str(T/(im.name+'.png'));im.file_format='PNG';im.save();maps[channel]=im
 print('BELT08_BAKE',channel,flush=True)
bpy.data.objects.remove(baker,do_unlink=True)
run=bpy.data.materials['PKM_QBZ_Body'].copy();run.name='PKM_BeltLinkSteel'
for node in run.node_tree.nodes:
 if node.type=='TEX_IMAGE' and node.image:
  channel=next((c for c in maps if node.image.name.endswith('_'+c)),None)
  if channel:node.image=maps[channel]
linkmats={}
for group in ['OldBelt','NewBelt']:
 m=run.copy();m.name=run.name+'__'+group;linkmats[group]=m
for ob in [clip,bridge]:ob.data.materials.clear();ob.data.materials.append(run)

activate([r]);bpy.ops.object.mode_set(mode='EDIT')
for prefix in ['', 'New_']:
 for i,c in enumerate(centers):
  name=prefix+f'PKM_Belt_{i:02}';bone=r.data.edit_bones.get(name) or r.data.edit_bones.new(name)
  bone.head=(0,0,0);bone.tail=(0,.025,0);bone.matrix=B@trx(c);bone.parent=r.data.edit_bones[prefix+'PKM_BeltRoot']
 for i in range(N-1):
  bone=r.data.edit_bones.new(prefix+f'PKM_Belt_Link_{i:02}');bone.head=(0,0,0);bone.tail=(0,.01,0)
  bone.matrix=B@frame_matrix((centers[i]+centers[i+1])*.5,centers[i+1]-centers[i]);bone.parent=r.data.edit_bones[prefix+'PKM_BeltRoot']
bpy.ops.object.mode_set(mode='OBJECT')

def bind(ob,name,bone):
 ob.name=name;ob['mechanical_bone']=bone;ob['belt_stage']='Belt08'
 ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
 ob.vertex_groups.clear();ob.vertex_groups.new(name=bone).add(list(range(len(ob.data.vertices))),1,'REPLACE')
 for mod in list(ob.modifiers):
  if mod.type=='ARMATURE':ob.modifiers.remove(mod)
 ob.modifiers.new('Rigid belt unit','ARMATURE').object=r
 for k in ['source_part_id','source_name','source_parent']:
  if k in ob:del ob[k]
 ob.hide_set(False);ob.hide_render=bone.startswith('New_')

for prefix,group in [('', 'OldBelt'),('New_','NewBelt')]:
 for i,c in enumerate(centers):
  bone=prefix+f'PKM_Belt_{i:02}'
  for j,proto in enumerate(prototypes):
   ob=proto.copy();ob.data=proto.data.copy();s.collection.objects.link(ob)
   ob.data.transform(B@trx(c-old[0])@Binv)
   for slot in ob.material_slots:
    base=slot.material.name.split('__')[0];slot.material=bpy.data.materials[base+'__'+group]
   bind(ob,prefix+f'PKM_Belt08_Round_{i:02}_{j}',bone)
  ob=clip.copy();ob.data=clip.data.copy();s.collection.objects.link(ob);ob.data.transform(B@frames[i]);ob.data.materials[0]=linkmats[group]
  bind(ob,prefix+f'PKM_Belt08_Clip_{i:02}',bone)
 for i in range(N-1):
  ob=bridge.copy();ob.data=bridge.data.copy();s.collection.objects.link(ob)
  # Each bridge has its own fixed authored length and one rigid transform.
  scale=Matrix.Diagonal(Vector((lengths[i]/pitch,1,1,1)))
  ob.data.transform(B@frame_matrix((centers[i]+centers[i+1])*.5,centers[i+1]-centers[i])@scale);ob.data.materials[0]=linkmats[group]
  bind(ob,prefix+f'PKM_Belt08_Link_{i:02}',prefix+f'PKM_Belt_Link_{i:02}')
for ob in [clip,bridge]+prototypes:bpy.data.objects.remove(ob,do_unlink=True)
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
bone_names=[n for n in rest if n.removeprefix('New_').startswith('PKM_Belt_')]
for n in bone_names:r.pose.bones[n].rotation_mode='QUATERNION'

def export(name,mesh=False):
 if mesh:
  from mesh_export import export_mesh
  export_mesh(r,E/(name+'.fbx'));return
 obs=[r]+[o for o in s.objects if o.type=='MESH' and (o.name=='SK_Manny_Arms_Export' or 'mechanical_bone' in o)] if mesh else [r]
 activate(obs)
 bpy.ops.export_scene.fbx(filepath=str(E/(name+'.fbx')),use_selection=True,object_types={'ARMATURE','MESH'} if mesh else {'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=not mesh,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,bake_anim_step=1,use_mesh_modifiers=True,mesh_smooth_type='FACE',path_mode='AUTO')

for key,name in names.items():
 a=bpy.data.actions[name];action(a)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in list(bag.fcurves):
     if any(curve.data_path.startswith('pose.bones["'+n+'"]') for n in bone_names):bag.fcurves.remove(curve)
 dynamics={p:BeltDynamics(lengths[:end]) for p in ['', 'New_']};previous={}
 for f,row in enumerate(samples[key]):
  s.frame_set(f);t=f/60;W=row['W'];desired={}
  for prefix in ['', 'New_']:
   inp=row[prefix];boxM=inp['box'];pts=[boxM@p for p in centers];tip=inp['tip']
   if key.startswith('reload'):
    exposed=project([p.copy() for p in pts[:end+1]],lengths[:end],tip,pts[end],80)
    activation=smooth((t-.45)/.3)*(1-smooth((t-5.1)/.35))
    exposed=dynamics[prefix].step(exposed,W,activation);pts[:end+1]=exposed
   else:
    offset=tip-pts[0];pts=[p+offset for p in pts]
   axis=boxM.to_3x3()@Vector((0,1,0))
   for i,p in enumerate(pts):
    tangent=pts[min(i+1,N-1)]-pts[max(i-1,0)]
    # Constrain cartridge axes to the rigid box axis; local link roll follows
    # the chain tangent while the brass body cannot bend or shear.
    tangent-=axis*tangent.dot(axis);tangent.normalize();z=tangent.cross(axis).normalized()
    orient=Matrix((tangent,axis,z)).transposed().to_4x4()
    delta=orient@frames[i].to_3x3().transposed().to_4x4();delta.translation=p
    desired[prefix+f'PKM_Belt_{i:02}']=W@delta
   for i in range(N-1):
    tangent=(pts[i+1]-pts[i]).normalized();y=(axis-tangent*axis.dot(tangent)).normalized();z=tangent.cross(y).normalized()
    m=Matrix((tangent,y,z)).transposed().to_4x4();m.translation=(pts[i]+pts[i+1])*.5
    desired[prefix+f'PKM_Belt_Link_{i:02}']=W@m
  for n,m in desired.items():
   parent=r.data.bones[n].parent.name;prefix='New_' if n.startswith('New_') else ''
   local_rest=rest[parent].inverted()@rest[n];local_pose=row[prefix]['root'].inverted()@m
   loc,q,scale=(local_rest.inverted()@local_pose).decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();bone=r.pose.bones[n];bone.location=loc;bone.rotation_quaternion=q;bone.scale=(1,1,1)
   for prop in ['location','rotation_quaternion','scale']:bone.keyframe_insert(prop,frame=f,group=n)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     if any(curve.data_path.startswith('pose.bones["'+n+'"]') for n in bone_names):
      for point in curve.keyframe_points:point.interpolation='LINEAR'
 s.frame_start=0;s.frame_end=len(samples[key])-1;s.frame_set(0)
 if key!='source_idle':export('A_PKM_'+key)
 print('BELT08_MOTION',key,flush=True)
action(bpy.data.actions['PKM_Game_idle']);s.frame_start=0;s.frame_end=60;s.frame_set(0)
export('SK_PKM_Manny',True)
for o in s.objects:
 if o.type=='MESH' and o.get('mechanical_bone','').startswith('New_'):o.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_Gameplay_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'clips':clips,'fps':60,'mesh':'SK_PKM_Manny','source':'Bipod07','belt':layout,'preserved':'All non-belt animation channels and gun/arms geometry','motion':'240 Hz offline inertia and gravity; projected rigid link lengths; 4 mm guide clearance corridor','runtime_tested':False},indent=2))
(O/'surface_manifest.json').write_text(json.dumps({'material':'PKM_BeltLinkSteel','textures':{c:str(T/(im.name+'.png')) for c,im in maps.items()}},indent=2))
print('BELT08_AUTHORING_COMPLETE',flush=True)
