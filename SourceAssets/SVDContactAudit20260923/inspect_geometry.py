"""Read-only evaluated-skin contact inspection. All color overrides are in memory."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent/'SVDAttachments20260923';OUT=O/'frames';OUT.mkdir(exist_ok=True)
families=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['base']
allreport={}
def mat(name,c):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True
 m.node_tree.nodes.clear();b=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');output=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(b.outputs['BSDF'],output.inputs['Surface']);b.inputs['Base Color'].default_value=(*c,1);b.inputs['Roughness'].default_value=.68
 return m
def verts(o):
 e=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh()
 vs=[o.matrix_world@v.co for v in me.vertices];ps=[list(p.vertices) for p in me.polygons];e.to_mesh_clear()
 return vs,ps
def metric(vs,indices,tree):
 rows=[]
 for i in indices:
  h,n,face,d=tree.find_nearest(vs[i]);rows.append((d,(vs[i]-h).dot(n)))
 ds=sorted(d for d,_ in rows)
 return {'vertices':len(ds),'nearest_surface_mm':1000*ds[0], 'p10_surface_mm':1000*ds[len(ds)//10], 'within_2mm_vertices':sum(d<.002 for d in ds),'min_signed_normal_mm':min(x[1] for x in rows)*1000}
for family in families:
 path=S/('SVD_Modular_Editable.blend' if family=='base' else 'SVD_'+family+'_Editable.blend')
 bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=next(o for o in s.objects if o.type=='ARMATURE');arms=bpy.data.objects['SK_Manny_Arms_Export'];extras=[]
 if family!='base':
  with bpy.data.libraries.load(str(S/('SM_SVD_'+family+'.blend'))) as (a,b):b.objects=list(a.objects)
  for o in b.objects:
   if o and o.type=='MESH':s.collection.objects.link(o);extras.append((o,o.matrix_world.copy()))
  bpy.ops.object.select_all(action='DESELECT')
  for ob,_ in extras:ob.select_set(True)
  bpy.context.view_layer.objects.active=extras[0][0];bpy.ops.object.join();ob=bpy.context.object;ob.name='Audit_FittedGrip';extras=[(ob,ob.matrix_world.copy())]
 for o in list(s.objects):
  if o.type in ['CAMERA','LIGHT']:bpy.data.objects.remove(o,do_unlink=True)
 blue=mat('Audit_Left_Glove',(.06,.38,.56));orange=mat('Audit_Right_Glove',(.7,.27,.07));bodymat=mat('Audit_Gun',(.21,.235,.255));magmat=mat('Audit_Mag',(.48,.48,.33));handle=mat('Audit_Handle',(.7,.08,.07));gripmat=mat('Audit_Grip',(.22,.24,.17))
 groups={g.index:g.name for g in arms.vertex_groups};vside={v.index:sum(g.weight for g in v.groups if groups[g.group].endswith('_l'))>.5 for v in arms.data.vertices}
 indices={side:{part:[v.index for v in arms.data.vertices if sum(g.weight for g in v.groups if groups[g.group].endswith('_'+side) and (groups[g.group].startswith(part+'_') if part!='palm' else groups[g.group]=='hand_'+side))>.5] for part in ['palm','thumb','index','middle','ring','pinky']} for side in ['l','r']}
 for o in s.objects:
  if o.type!='MESH':continue
  o.hide_render=False;o.hide_set(False);o.data.materials.clear()
  if o==arms:
   o.data.materials.append(blue);o.data.materials.append(orange)
   for p in o.data.polygons:p.material_index=0 if vside[p.vertices[0]] else 1
  else:
   o.data.materials.append(magmat if 'Magazine' in o.name else handle if 'ChargingHandle' in o.name else gripmat if any(o==x[0] for x in extras) else bodymat)
   for p in o.data.polygons:p.material_index=0
 s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True;s.render.resolution_x=720;s.render.resolution_y=620;s.render.resolution_percentage=100
 s.render.image_settings.file_format='PNG';s.world=bpy.data.worlds.new('AuditWorld');s.world.use_nodes=True;wn=s.world.node_tree.nodes;wn.clear();bg=wn.new('ShaderNodeBackground');wo=wn.new('ShaderNodeOutputWorld');s.world.node_tree.links.new(bg.outputs[0],wo.inputs[0]);bg.inputs[0].default_value=(.52,.52,.52,1);bg.inputs[1].default_value=.8
 s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=0;s.view_settings.gamma=1;s.render.use_compositing=False;s.render.use_sequencer=False
 cam=bpy.data.objects.new('AuditCamera',bpy.data.cameras.new('AuditCamera'));s.collection.objects.link(cam);s.camera=cam;cam.data.type='ORTHO';cam.data.lens=55
 light=bpy.data.objects.new('AuditLight',bpy.data.lights.new('AuditLight','AREA'));s.collection.objects.link(light);light.data.energy=12;light.data.shape='DISK';light.data.size=.7
 def sample(clip,f):
  a=bpy.data.actions['A_SVD_'+('' if family=='base' else family+'_')+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
  W=r.matrix_world@r.pose.bones['WPN_root'].matrix
  for o,M in extras:o.matrix_world=W@M
  bpy.context.view_layer.update();return W
 def render(clip,f,view,target,delta,scale):
  W=sample(clip,f)
  if isinstance(target,str):
   vs,ps=verts(bpy.data.objects[target]);center=(Vector(map(min,zip(*vs)))+Vector(map(max,zip(*vs))))*.5
  else:center=W@Vector(target)
  cam.location=center+W.to_3x3()@Vector(delta);cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
  light.location=cam.location+W.to_3x3()@Vector((.1,.05,.15));light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
  s.render.filepath=str(OUT/f'{family}_{clip}_{f}_{view}.png');bpy.ops.render.render(write_still=True);print('AUDIT_RENDER',s.render.filepath,flush=True)
 if family=='base':
  for v,d in [('left',(.55,.16,.12)),('right',(-.55,.06,.1)),('under',(.35,.12,-.45))]:render('idle',0,v,(0,-.28,0),d,.35)
  for f in [52,128,180,220,240,252,264,280]:render('reload',f,'mag', 'SM_SVD_Magazine',(.5,.22,-.12),.30)
  for f in [64,80,94,100,116]:render('equip',f,'handle','SM_SVD_ChargingHandle',(-.5,.25,.25),.23)
  render('reload_empty',310,'handle','SM_SVD_ChargingHandle',(-.5,.25,.25),.23)
 else:
  render('idle',0,'left',(0,-.32,-.05),(.55,.12,-.1),.34)
  render('idle',0,'right',(0,-.32,-.05),(-.55,.06,-.1),.34)
 rows=[]
 for clip,frames in {'idle':[0,2.5,5], 'aim':[0], 'fire':[4,12], 'equip':[64,80,94], 'reload':[52,90,110,128,180,220,240,244,252,260,264,272,280,298,400], 'reload_empty':[128,220,240,268,310,326,344,350,366,432,515]}.items():
  for f in frames:
   W=sample(clip,f);vs,ps=verts(arms)
   targets=['SM_SVD_ChargingHandle'] if clip=='equip' or clip=='reload_empty' and 310<=f<=366 else ['SM_SVD_Magazine'] if clip.startswith('reload') and 52<=f<=272 else [extras[0][0].name if extras else 'SM_SVD_Body']
   side='r' if targets[0]=='SM_SVD_ChargingHandle' else 'l'
   for target in targets:
    tv,tp=verts(bpy.data.objects[target]);tree=BVHTree.FromPolygons(tv,tp,all_triangles=False)
    contact={part:metric(vs,ids,tree) for part,ids in indices[side].items() if ids}
    handindices=set(sum(indices[side].values(),[]));handpolys=[p for p in ps if all(i in handindices for i in p)];ht=BVHTree.FromPolygons(vs,handpolys,all_triangles=False)
    rows.append({'clip':clip,'frame':f,'side':side,'target':target,'contact':contact,'surface_triangle_intersections':len(ht.overlap(tree)), 'hand_in_root_m':list((W.inverted()@r.matrix_world@r.pose.bones['hand_'+side].matrix).translation)})
 allreport[family]=rows;(O/('geometry_'+family+'.json')).write_text(json.dumps(rows,indent=2));print('AUDIT_GEOMETRY_DONE',family,len(rows),flush=True)
print('SVD_AUDIT_RENDER_AND_GEOMETRY_DONE',flush=True)
