import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(r'D:/FPS3D/FPSGAME/SourceAssets/BenelliM4Super9020261006');P=O.parents[1];X=O/'Exports';X.mkdir(exist_ok=True);(X/'Animations').mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'BenelliM4_Original_Editable.blend'));s=bpy.context.scene;src=bpy.data.objects['Rig'];s.render.fps=60
A=Matrix.Translation((0,0,-.8))@Matrix.Rotation(math.pi,4,'Z')@Matrix.Diagonal((.0213,.0213,.0213,1))
def normalized(m):
 p,q,_=m.decompose();return Matrix.LocRotScale(p,q,Vector((1,1,1)))
def name(n):
 direct={'pose_controller':'root','body':'spine_03','Main':'WPN_root','Slider':'WPN_bolt','Load':'WPN_Load','Trigger':'WPN_Trigger','Shell':'WPN_Shell'}
 if n in direct:return direct[n]
 n=n.replace('shoulder_','clavicle_').replace('pink_','pinky_').lower()
 if n.startswith('twist_arm_'):
  seg,side=n.split('_')[-2:];return {'1':'lowerarm_aux','2':'lowerarm_twist_02','3':'lowerarm_twist_01'}[seg]+'_'+side
 for digit in ('thumb','index','middle','ring','pinky'):
  if n.startswith(digit+'_'):
   bits=n.split('_');return digit+('_0'+bits[1]+'_'+bits[2] if len(bits)==3 else '_metacarpal_'+bits[1])
 return n
mapping={b.name:name(b.name) for b in src.data.bones};rest={mapping[b.name]:normalized(A@src.matrix_world@b.matrix_local) for b in src.data.bones};parents={mapping[b.name]:mapping[b.parent.name] if b.parent else 'VM_Root' for b in src.data.bones}
clips={};rawclips={}
for a in list(bpy.data.actions):
 if '|M4_' not in a.name:continue
 label=a.name.rsplit('|',1)[1];src.animation_data.action=a;src.animation_data.action_slot=a.slots[0];rows=[]
 for f in range(int(a.frame_range[0]),int(a.frame_range[1])+1):
  s.frame_set(f);bpy.context.view_layer.update();rows.append({mapping[b.name]:normalized(A@src.matrix_world@b.matrix) for b in src.pose.bones})
 rawclips[label]=rows
# Give the semantic gun root a physical up axis without changing its deformation.
old_main=rest['WPN_root'].copy();rest['WPN_root']=Matrix.Translation(old_main.translation)
for rows in rawclips.values():
 for row in rows:row['WPN_root']=row['WPN_root']@old_main.inverted()@rest['WPN_root']
# Preserve source UVs, surface slots and exact mechanical weights in normalized centimetre export.
objects={}
for ob in list(s.objects):
 if ob.type!='MESH':continue
 ob.data.transform(A@ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear()
 for g in ob.vertex_groups:g.name=mapping[g.name]
 objects[ob.name]=ob
bpy.data.objects.remove(src,do_unlink=True)
arm=bpy.data.armatures.new('Super90_Native');r=bpy.data.objects.new('SK_Super90',arm);s.collection.objects.link(r);bpy.context.view_layer.objects.active=r;r.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
eb=arm.edit_bones.new('VM_Root');eb.head=(0,0,0);eb.tail=(0,0,.025)
for n,m in rest.items():
 b=arm.edit_bones.new(n);b.matrix=m;b.length=.025
for n,p in parents.items():arm.edit_bones[n].parent=arm.edit_bones[p]
# Author socket positions are defined in the original FBX complete gun surface frame.
# Barrel runs toward negative Y in that frame; normalize once with the complete rig.
markers={'WPN_SOCKET_Muzzle':(0,-23.40,2.04),'WPN_SOCKET_Eject':(-.7,3.9,2.1),'WPN_RearSight':(0,7.55,4.34),'WPN_FrontSight':(0,-19.93,3.78),'WPN_ChargingHandle':(-1.15,3.95,2.18),'WPN_BoltCatch':(-.85,5.1,1.1),'WPN_SOCKET_Magazine':(0,5.0,.4)}
for n,p in markers.items():
 b=arm.edit_bones.new(n);m=rest['WPN_root'].copy();m.translation=A@Vector(p);b.matrix=m;b.length=.01;b.parent=arm.edit_bones['WPN_root'];rest[n]=m;parents[n]='WPN_root'
bpy.ops.object.mode_set(mode='OBJECT');rest['VM_Root']=Matrix.Identity(4);parents['VM_Root']=None
# The saved native bind is authoritative. EditBone.matrix on a newly created
# zero-length bone can retain a different roll; transport the source deformation
# into that actual bind instead of baking against the requested matrix alone.
binding_rest={b.name:b.matrix_local.copy() for b in arm.bones}
binding_correction={n:rest[n].inverted()@binding_rest[n] for n in rest}
for ob in objects.values():
 ob.parent=r;mod=ob.modifiers.new('Super90 Native Skin','ARMATURE');mod.object=r
# Reconnect author texture files, including the source OpenGL normal convention.
T=O/'Original/Source/textures';groups={'TTI_Benelli_M4':('TTI_Benelli_M4_BaseColor_brand_friendly','TTI_Benelli_M4_Normal_brand_friendly','TTI_Benelli_M4_Roughness_brand_friendly','TTI_Benelli_M4_Metallic_brand_friendly','TTI_Benelli_M4_AO'),'12gauge':('12gauge_BaseColor_red','12gauge_Normal_brand_friendly','12gauge_Roughness','12gauge_Metallic','12gauge_AO'),'matchsaverz':('matchsaverz_BaseColor_black_brand_friendly','matchsaverz_Normal','matchsaverz_Roughness','matchsaverz_Metallic',None),'glove_hardknuckle':('glove_hardknuckle_Base_color','glove_hardknuckle_Normal_OpenGL',None,'glove_hardknuckle_Metallic',None),'sleeve_st6_generalist':('sleeve_st6_generalist_Base_color','sleeve_st6_generalist_Normal_OpenGL',None,'sleeve_st6_generalist_Metallic',None)}
for m in bpy.data.materials:
 if m.name not in groups:continue
 m.use_nodes=True;bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Roughness'].default_value=.72
 for key,stem in zip(('Base Color','Normal','Roughness','Metallic','AO'),groups[m.name]):
  if not stem:continue
  tx=m.node_tree.nodes.new('ShaderNodeTexImage');tx.image=bpy.data.images.load(str(T/(stem+'.png')),check_existing=True);tx.image.colorspace_settings.name='sRGB' if key=='Base Color' else 'Non-Color'
  if key=='Normal':
   nm=m.node_tree.nodes.new('ShaderNodeNormalMap');m.node_tree.links.new(tx.outputs['Color'],nm.inputs['Color']);m.node_tree.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
  elif key!='AO':m.node_tree.links.new(tx.outputs['Color'],bs.inputs[key])
# V7 geometry is transported by anatomical segment frames, never by incompatible FBX bone axes.
with bpy.data.libraries.load(str(P/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/M4_BareArmsV7.blend'),link=False) as (available,loaded):loaded.objects=list(available.objects)
bare_rig=next(o for o in loaded.objects if o and o.type=='ARMATURE');oldrest={b.name:b.matrix_local.copy() for b in bare_rig.data.bones}
def mapped(n):
 if n.startswith('upperarm_twist'):return 'upperarm_'+n[-1]
 if n in ('lowerarm_l','lowerarm_r'):return 'lowerarm_aux_'+n[-1]
 return n if n in rest else 'lowerarm_'+n[-1] if n.startswith('lowerarm_twist') else n
def frame(data,n):
 side=n[-1];p=data[n].translation
 nxt=('lowerarm_'+side if n.startswith('upperarm') else 'hand_'+side if n.startswith('lowerarm') else 'middle_01_'+side if n.startswith('hand_') else None)
 if '_metacarpal_' in n:nxt=n.split('_')[0]+'_01_'+side
 elif any(n.startswith(d+'_') for d in ('thumb','index','middle','ring','pinky')):
  bits=n.split('_');k=int(bits[1]);nxt=bits[0]+'_%02d_'%(k+1)+side if k<3 else None
 if nxt and nxt in data:x=data[nxt].translation-p
 elif n.endswith(('_l','_r')) and '_03_' in n:x=p-data[n.replace('_03_','_02_')].translation
 else:x=data[n].to_3x3().col[0].normalized()*.025
 width=data['index_01_'+side].translation-data['pinky_01_'+side].translation
 forward=data['middle_01_'+side].translation-data['hand_'+side].translation
 z=forward.cross(width).normalized();length=max(x.length,.005);x.normalize();y=z.cross(x).normalized();z=x.cross(y).normalized()
 m=Matrix((x,y,z)).transposed().to_4x4();m.translation=p;return m,length,width.length
warp={}
for n in oldrest:
 target=mapped(n)
 if target not in rest or not n.endswith(('_l','_r')):continue
 # Collapsed upper-arm helpers share the whole segment's geometry transform;
 # their fractional head position must not be stretched back to the shoulder.
 source='upperarm_'+n[-1] if n.startswith('upperarm_twist') else n
 a,la,wa=frame(oldrest,source);b,lb,wb=frame(rest,target)
 radial=wb/max(wa,1e-6);warp[n]=b@Matrix.Diagonal((lb/la,radial,radial,1))@a.inverted()
arms=[]
for ob in loaded.objects:
 if not ob or ob.type!='MESH':continue
 s.collection.objects.link(ob);original_groups={g.index:g.name for g in ob.vertex_groups}
 for v in ob.data.vertices:
  inf=[(g.weight,warp[original_groups[g.group]]) for g in v.groups if original_groups[g.group] in warp];total=sum(w for w,m in inf)
  if total:v.co=sum((m@v.co*w for w,m in inf),Vector())/total
 weights=[{} for v in ob.data.vertices]
 for v in ob.data.vertices:
  for g in v.groups:
   n=mapped(original_groups[g.group])
   if n in rest:weights[v.index][n]=weights[v.index].get(n,0)+g.weight
 ob.vertex_groups.clear()
 for n in set(n for row in weights for n in row):ob.vertex_groups.new(name=n)
 for i,row in enumerate(weights):
  total=sum(row.values())
  for n,w in row.items():ob.vertex_groups[n].add([i],w/total,'REPLACE')
 ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4);ob.modifiers.clear();ob.modifiers.new('Native V7 Binding','ARMATURE').object=r;ob.name='Super90_V7_'+ob.name;arms.append(ob)
bpy.data.objects.remove(bare_rig,do_unlink=True)
# Keep source outfit separately; it never replaces the unequipped V7 base.
glove=objects['hardknuckle'];sleeve=objects['sleeve'];gun=objects['benelli_m4_TTI_Benelli_M4_0'];shell=objects['12g_12gauge_0']
# Separate the gun's existing mechanical regions and material islands without cutting faces.
import bmesh
parts=[];roles={}
for label,bone in [('body','WPN_root'),('bolt','WPN_bolt'),('loading_gate','WPN_Load'),('trigger','WPN_Trigger')]:
 ob=gun.copy();ob.data=gun.data.copy();s.collection.objects.link(ob);ob.name='Super90_'+label
 ids={v.index for v in ob.data.vertices if any(ob.vertex_groups[g.group].name==bone and g.weight>.5 for g in v.groups)}
 bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in ids],context='VERTS');bm.to_mesh(ob.data);bm.free();parts.append(ob);roles[label]={'bone':bone,'vertices':len(ob.data.vertices)}
bpy.data.objects.remove(gun,do_unlink=True)
# Keep the native gun's curve shading repair in a full source rebuild.
import sys
sys.path.insert(0,str(P/'SourceAssets/Super90SurfaceRepair20261007'))
from surface_normals import repair_gun_normals
repair_gun_normals(parts)
sys.path.insert(0,str(P/'SourceAssets/Super90Optics20261007'))
from factory_sights import tag_factory_sights
tag_factory_sights(parts)
# Keep the user's shared WS1 surface choice when rebuilding the original rig.
sys.path.insert(0,str(P/'SourceAssets/Super90WS1Surface20261007'))
from surface_regions import apply_surface_regions
apply_surface_regions(parts)
sys.path.insert(0,str(P/'SourceAssets/Super90ShellMechanics20261008'))
from shell_sections import separate_mounted_shell
separate_mounted_shell(parts)
from mapping import correct_weapon_uv
correct_weapon_uv([shell])
for surface in bpy.data.materials:
 if surface.name=='TTI_Benelli_M4':
  for node in surface.node_tree.nodes:
   if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.5
# Export all source clips on one normalized native skeleton; ADS shares idle/fire.
import sys
sys.path.insert(0,str(P/'SourceAssets/M1911RevolverInspect20260927'));import author_support as support
r.animation_data_create()
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=r

def complete(row):
 row=dict(row);row['VM_Root']=Matrix.Identity(4)
 for n in markers:row[n]=row['WPN_root']@rest['WPN_root'].inverted()@rest[n]
 return {n:row[n]@binding_correction[n] for n in rest}

def bake(label,rows):
 local=[]
 for raw in rows:
  row=complete(raw);entry={}
  for n in rest:
   p=parents[n];rp=binding_rest[p] if p else Matrix.Identity(4);pp=row[p] if p else Matrix.Identity(4)
   mat=(rp.inverted()@binding_rest[n]).inverted()@(pp.inverted()@row[n]);entry[n]=mat.decompose()
  local.append(entry)
 support.DURATION=(len(rows)-1)/60;action=support.bake_action(r,s,'A_Super90_'+label,local,list(range(len(rows))))
 select([r]+parts+[shell]+arms);file=X/'Animations'/('A_Super90_'+label+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
 clips[label]={'fbx':str(file),'duration':support.DURATION,'action':action.name};return action
labels={'M4_Idle':'idle','M4_Walk':'walk','M4_Run':'run','M4_Fire':'fire','M4_Fire_LastRoundCheck':'fire_last','M4_ReloadOne_type1':'reload_one','M4_ReloadFull_type1':'reload_full','M4_ReloadOne_type2':'reload_empty'}
for source,label in labels.items():bake(label,rawclips[source])
# Equip raises the rig into idle. Reuse the look-over motion for inspect,
# with the idle closed bolt rather than the donor's last-round open chamber.
idle=rawclips['M4_Idle'][0]
rows=[]
for f in range(37):
 t=f/36;w=1-t*t*(3-2*t);delta=Matrix.Translation((0,-.12*w,-.20*w))@Matrix.Rotation(.25*w,4,'X');rows.append({n:delta@m for n,m in idle.items()})
bake('equip',rows)
inspect_rows=[]
bolt_in_gun=idle['WPN_root'].inverted()@idle['WPN_bolt']
for source_row in rawclips['M4_Fire_LastRoundCheck'][22:]:
 row=dict(source_row);row['WPN_bolt']=row['WPN_root']@bolt_in_gun;inspect_rows.append(row)
bake('inspect',inspect_rows)
rows=[]
for f in range(43):
 t=f/42;pulse=math.sin(math.pi*t)**2;delta=Matrix.Translation((0,.23*pulse,.03*pulse))@Matrix.Rotation(-.13*pulse,4,'X');rows.append({n:delta@m for n,m in idle.items()})
bake('quick_melee',rows)
# Export reference geometry, source outfit and a hand-free world/preview mesh.
r.animation_data.action=None
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
s.frame_set(0)
def mesh_export(label,obs,skeletal=True):
 select(([r] if skeletal else [])+obs);file=X/(label+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','ARMATURE'} if skeletal else {'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 return str(file)
mesh=mesh_export('SK_Super90_V7',parts+[shell]+arms)
outfit={'gloves':mesh_export('SK_Super90_HardKnuckle', [glove]),'shirt':mesh_export('SK_Super90_ST6Sleeves',[sleeve]),'bare':mesh_export('SK_Super90_BareArmsV7',arms)}
# Save editable geometry with every clip and the source outfit, visibility controlled by equipment.
glove.hide_render=True;glove.hide_set(True);sleeve.hide_render=True;sleeve.hide_set(True)
r.animation_data.action=bpy.data.actions['A_Super90_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_end=179;s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_Gameplay_Editable.blend'))
report={'mesh':mesh,'outfit':outfit,'clips':clips,'parts':roles,'material_groups':groups,'uniform_source_scale':.0213,'markers_source':markers,'bone_mapping':mapping,'native_rest':{n:[list(x) for x in m] for n,m in rest.items()},'parents':parents,'v7_to_native_warp':{n:[list(x) for x in m] for n,m in warp.items()},'runtime_tested':False}
report['bake_binding_rest']={n:[list(x) for x in m] for n,m in binding_rest.items()}
report['pose_basis']='Source deformation transported from native_rest to bake_binding_rest'
(O/'authoring.json').write_text(json.dumps(report,indent=2));print('SUPER90_AUTHORING_SAVED',len(clips),flush=True)
