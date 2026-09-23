"""Game-animation exterior/interior approximation; not a functional mechanical model."""
import bpy,json,math,pathlib
from mathutils import Vector,Matrix
ROOT=pathlib.Path(__file__).parent;OUT=ROOT/'Mechanics02';OUT.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Refinement01/PKM_Lowpoly_Refined.blend'))
parts={int(o['source_part_id']):o for o in bpy.context.scene.objects if o.type=='MESH'}
steel=bpy.data.materials['PKM_BluedSteel']
inside=steel.copy();inside.name='PKM_InteriorSteel'
bs=next(n for n in inside.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
for link in list(bs.inputs['Roughness'].links):inside.node_tree.links.remove(link)
bs.inputs['Roughness'].default_value=.52
made=[];assignment={i:'WPN_root' for i in parts}
groups={
 'PKM_Cover':[43,48,50,54,55,58,94,95,98,99,100,101,102],
 'PKM_Box':[47,62,63,64,105,106,107,108,109,110,111],
 'PKM_BoxLid':[61], 'PKM_Charge':[139], 'PKM_Trigger':[138], 'PKM_Latch':[137]
}
for bone,ids in groups.items():
 for i in ids:assignment[i]=bone
inp=json.loads((ROOT/'mechanics_inputs.json').read_text())
carts=[Vector(c['center']) for c in inp['cartridges']]
for n in range(14):
 for i in range(3*n,3*n+3):assignment[i]=f'PKM_Belt_{n:02}'
for link in inp['links']:
 center=Vector(link['center']);n=min(range(14),key=lambda i:(center-carts[i]).length)
 assignment[link['id']]=f'PKM_Belt_{n:02}'
# The short empty outgoing link stays on its own control; do not pull it with a distant cartridge.
assignment[113]='PKM_EmptyLink'

def mesh(name,verts,faces,bone,bevel=.00035):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(inside)
 uv=me.uv_layers.new(name='UVMap')
 for p in me.polygons:
  axis=max(range(3),key=lambda a:abs(p.normal[a]));axes=[a for a in range(3) if a!=axis]
  for li in p.loop_indices:
   v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]*8,v[axes[1]]*8)
 if bevel:
  m=ob.modifiers.new('Interior_EdgeRadius','BEVEL');m.width=bevel;m.segments=3;m.limit_method='ANGLE';m.angle_limit=math.radians(35);m.use_clamp_overlap=True
  w=ob.modifiers.new('Interior_WeightedNormals','WEIGHTED_NORMAL');w.keep_sharp=True
 ob['mechanical_bone']=bone;ob['authorship']='New visual approximation from open-cover photographs';made.append(ob);return ob

def plate(name,outline,z,depth,bone,bevel=.0003):
 n=len(outline);v=[(x,y,z) for x,y in outline]+[(x,y,z+depth) for x,y in outline]
 faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
 faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return mesh(name,v,faces,bone,bevel)

def box(name,c,d,bone,bevel=.0003):
 x,y,z=c;a,b,h=[v*.5 for v in d]
 return plate(name,[(x-a,y-b),(x+a,y-b),(x+a,y+b),(x-a,y+b)],z-h,d[2],bone,bevel)

def pin(name,center,length,radius,bone,axis='X'):
 n=20;c=Vector(center);v=[]
 for t in [-length*.5,length*.5]:
  for i in range(n):
   a=i*math.tau/n;p={'X':(t,math.cos(a)*radius,math.sin(a)*radius),'Y':(math.cos(a)*radius,t,math.sin(a)*radius),'Z':(math.cos(a)*radius,math.sin(a)*radius,t)}[axis];v.append(tuple(c+Vector(p)))
 faces=[tuple(reversed(range(n))),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return mesh(name,v,faces,bone,.00015)

# Open receiver: retain the source floor and walls, add the long channel and side guide strips.
for side in [-1,1]:
 x=side*.0145
 plate('PKM_InnerGuide_'+str(side),[(x-.0018,.09),(x+.0018,.09),(x+.0018,.274),(x,.283),(x-.0018,.278)],.044,.007,'WPN_root')
 box('PKM_InnerGuideSeat_'+str(side),(x,.185,.0445),(.008,.193,.002),'WPN_root')
plate('PKM_VisibleInnerCarrier',[(-.009,.083),(.009,.083),(.011,.099),(.009,.218),(.006,.227),(-.006,.227),(-.009,.218),(-.011,.099)],.0445,.0055,'PKM_InnerCarrier')
box('PKM_RearChannelBridge',(0,.275,.048),(.022,.010,.008),'WPN_root')

# A shallow open-center tray, kept under the source cartridge line.
outer=[(-.029,.008),(.025,.008),(.031,.017),(.031,.078),(.022,.084),(-.026,.084),(-.033,.074),(-.033,.018)]
inner=[(-.013,.019),(.011,.019),(.015,.024),(.015,.067),(.01,.073),(-.011,.073),(-.017,.066),(-.017,.026)]
verts=[]
for z in [.054,.057]:verts.extend((x,y,z) for x,y in outer+inner)
faces=[];n=8
for i in range(n):
 j=(i+1)%n
 faces += [(i,j,j+16,i+16),(i+8,i+24,j+24,j+8),(i+16,j+16,j+24,i+24),(i+8,j+8,j,i)]
mesh('PKM_FeedTray_OpenFrame',verts,faces,'PKM_Tray',.00035)
for x in [-.03,.028]:box('PKM_TraySideGuide_'+str(x),(x,.044,.059),(.003,.058,.005),'PKM_Tray')
box('PKM_TrayFrontRim',(0,.011,.060),(.049,.004,.007),'PKM_Tray')
pin('PKM_TrayHinge_Visual',(0,-.006,.057),.042,.0025,'PKM_Tray')

# Under-cover profile follows the actual underside heights measured from the source mesh.
ys=[.014,.103,.13,.159,.19,.267]
zs=[.094,.094,.091,.083,.078,.078]
for side in [-1,1]:
 v=[]
 for y,z in zip(ys,zs):
  x=side*.016;v += [(x-.0015,y,z-.0002),(x+.0015,y,z-.0002),(x+.0015,y,z-.0027),(x-.0015,y,z-.0027)]
 f=[(3,2,1,0),tuple(range(len(v)-4,len(v)))]
 for k in range(len(ys)-1):
  for j in range(4):f.append((k*4+j,k*4+(j+1)%4,(k+1)*4+(j+1)%4,(k+1)*4+j))
 mesh('PKM_CoverPressedRib_'+str(side),v,f,'PKM_Cover',.0003)
plate('PKM_CoverInnerLever',[(-.009,.096),(-.006,.076),(.005,.076),(.009,.096),(.006,.136),(.003,.142),(-.004,.142),(-.008,.128)],.087,.0025,'PKM_Cover')
pin('PKM_CoverInnerCrossPin',(0,.09,.089),.03,.002,'PKM_Cover')
for x in [-.008,.008]:
 box('PKM_CoverGuidePad_'+str(x),(x,.179,.078),(.005,.018,.003),'PKM_Cover')
pin('PKM_CoverRearFastener',(0,.264,.076),.005,.002,'PKM_Cover',axis='Z')

# Separate rigid weights keep intact objects on mechanical controls.
arm=bpy.data.armatures.new('PKM_MechanicalSkeleton');rig=bpy.data.objects.new('PKM_MechanicalRig',arm);bpy.context.collection.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
specs={
 'WPN_root':((0,0,0),None), 'PKM_Cover':((0,-.021,.07),'WPN_root'),
 'PKM_Tray':((0,-.006,.057),'WPN_root'), 'PKM_Box':((0,.04,-.065),'WPN_root'),
 'PKM_BoxLid':((-.108,.04,-.048),'PKM_Box'), 'PKM_Charge':((-.040,.115,.019),'WPN_root'),
 'PKM_Trigger':((0,.192,-.012),'WPN_root'), 'PKM_Latch':((0,.288,.067),'WPN_root'),
 'PKM_InnerCarrier':((0,.105,.049),'WPN_root'), 'PKM_BeltRoot':((0,.038,.073),'WPN_root'),
 'PKM_EmptyLink':((.039,.039,.064),'WPN_root')
}
for i,c in enumerate(carts):specs[f'PKM_Belt_{i:02}']=(tuple(c),'PKM_BeltRoot')
for name,(pos,parent) in specs.items():
 b=arm.edit_bones.new(name);b.head=pos;b.tail=Vector(pos)+Vector((0,.025,0));b.use_deform=True
 if parent:b.parent=arm.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
for i,ob in parts.items():ob['mechanical_bone']=assignment[i]
for ob in list(parts.values())+made:
 world=ob.matrix_world.copy();ob.parent=None;ob.data.transform(world);ob.matrix_world=Matrix.Identity(4)
 ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
 vg=ob.vertex_groups.new(name=ob['mechanical_bone']);vg.add(list(range(len(ob.data.vertices))),1,'REPLACE')
 mod=ob.modifiers.new('PKM_RigidBinding','ARMATURE');mod.object=rig
for o in list(bpy.context.scene.objects):
 if o.type=='EMPTY':bpy.data.objects.remove(o,do_unlink=True)
for b in rig.pose.bones:b.rotation_mode='QUATERNION'
rig['authoring_note']='Cover rotates about its local X; belt pieces have independent controls. No animation or game integration in this file.'
bpy.context.scene.frame_start=0;bpy.context.scene.frame_end=450;bpy.context.scene.render.fps=60
bpy.ops.object.select_all(action='DESELECT')
for o in list(parts.values())+made+[rig]:o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'PKM_Mechanics_Editable.blend'))
bpy.ops.export_scene.fbx(filepath=str(OUT/'SK_PKM_Mechanics.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='COPY',embed_textures=True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'PKM_Mechanics.glb'),export_format='GLB',use_selection=True,export_apply=True,export_animations=False,export_extras=True)
report={'source_meshes_kept':len(parts),'new_meshes':len(made),'bones':list(specs),'bindings':{str(i):v for i,v in assignment.items()},'new_parts':[{ 'name':o.name,'bone':o['mechanical_bone']} for o in made],'visual_approximation':True,'tested':False,'game_integrated':False}
(OUT/'mechanics_manifest.json').write_text(json.dumps(report,indent=2))
print('MECHANICS_COMPLETE',json.dumps({'source_meshes':len(parts),'new_meshes':len(made),'bones':len(specs)}),flush=True)
