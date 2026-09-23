"""Produce actual-model transparent UI icons and editable part material scenes."""
import bpy,bmesh,json,math,shutil
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;I=O/'Icons';I.mkdir(exist_ok=True)
DEST=O.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'
src=json.loads((O/'sources.json').read_text());geo=json.loads((O/'authoring.json').read_text());inputs=json.loads((O/'geometry_inputs.json').read_text())
records=json.loads((O/'icons.json').read_text()) if (O/'icons.json').exists() else {}
bpy.context.preferences.filepaths.save_version=0
def image(path,srgb):
 a=bpy.data.images.load(str(path),check_existing=True);a.colorspace_settings.name='sRGB' if srgb else 'Non-Color';return a
def texpath(key,role):
 prefix={'holographic':'Holographic_low_Holosight','panoramic_red_dot':'T_Panoramic','prism_scope_2x':'T_Scope2X','lpvo_1_6x':'T_LPVO','lpvo_ring':'T_LPVO','vertical':'Body','canted':'Body','tactical_vertical':'T_TacticalVerticalForegrip','laser':'T_laser','flashlight':'T_flashlight','suppressor':'Flash_Hider','brake':'Flash_Hider','titanium_brake':'Flash_Hider','tactical_suppressor':'T_TacticalSuppressor'}.get(key)
 if not prefix:return None
 for name,record in src['textures'].items():
  short=name.rsplit('.',1)[-1]
  if short==prefix+'_'+role:
   for path in record['source']:
    if Path(path).exists():return Path(path)
 return None
def working(key,mat,index):
 # Runtime materials retain the source UE graphs. This editable Blender
 # translation uses the same original maps/region masks and SVD coating inputs.
 label=src['meshes'][key]['materials'][index]['slot'].lower();m=mat;m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
 p=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');l.new(p.outputs[0],out.inputs[0]);p.inputs['Base Color'].default_value=(.027,.034,.041,1);p.inputs['Roughness'].default_value=.31;p.inputs['Metallic'].default_value=.84
 if 'glass' in label:
  p.inputs['Base Color'].default_value=(.022,.044,.048,1);p.inputs['Metallic'].default_value=.05;p.inputs['Roughness'].default_value=.08;p.inputs['Transmission Weight'].default_value=.8;p.inputs['Alpha'].default_value=.12
  return
 if 'reticle' in label or 'red_dot' in label:
  p.inputs['Base Color'].default_value=(.004,.001,.001,1);p.inputs['Emission Color'].default_value=(.8,.012,.006,1);p.inputs['Emission Strength'].default_value=.6;p.inputs['Alpha'].default_value=.02
  return
 uv=n.new('ShaderNodeUVMap');uv.uv_map=bpy.context.object.data.uv_layers[0].name if bpy.context.object and bpy.context.object.type=='MESH' else 'UVmap_0'
 def texture(path,srgb,uvindex=0):
  t=n.new('ShaderNodeTexImage');t.image=image(path,srgb)
  coord=n.new('ShaderNodeUVMap');coord.uv_map=uv.uv_map if uvindex==0 else bpy.context.object.data.uv_layers[2].name
  l.new(coord.outputs[0],t.inputs[0]);return t.outputs['Color']
 def scalar(op,a,b):
  q=n.new('ShaderNodeMath');q.operation=op
  for v,s in zip([a,b],q.inputs):
   if hasattr(v,'node'):l.new(v,s)
   else:s.default_value=v
  return q.outputs[0]
 def mix(a,b,w):
  q=n.new('ShaderNodeMixRGB');q.blend_type='MIX'
  for i,(v,s) in enumerate(zip([w,a,b],q.inputs)):
   if hasattr(v,'node'):l.new(v,s)
   else:s.default_value=(v,v,v,1) if i>0 and isinstance(v,(int,float)) else v
  return q.outputs[0]
 def wire(v,pin):
  if hasattr(v,'node'):l.new(v,p.inputs[pin])
  else:p.inputs[pin].default_value=v
 sourcebase=texpath(key,'BaseColor');normal=texpath(key,'Normal');metal=texpath(key,'Metallic');rough=texpath(key,'Roughness');packed=texpath(key,'MetalRough')
 oldbc=texture(sourcebase,True) if sourcebase else (.016,.019,.022,1)
 oldrough=texture(rough,False) if rough else .5;oldmetal=texture(metal,False) if metal else 0.
 if packed:
  sep=n.new('ShaderNodeSeparateColor');l.new(texture(packed,False),sep.inputs[0]);oldrough=sep.outputs['Green'];oldmetal=sep.outputs['Blue']
 if key=='holographic':
  orm=O.parents[1]/'Content/holographicpacked.fbm/Holographic_low_Holosight_OcclusionRoughnessMetallic.png'
  if orm.exists():
   sep=n.new('ShaderNodeSeparateColor');l.new(texture(orm,False),sep.inputs[0]);oldrough=sep.outputs['Green'];oldmetal=sep.outputs['Blue']
 if normal:
  nm=n.new('ShaderNodeNormalMap');nm.uv_map=uv.uv_map;l.new(texture(normal,False),nm.inputs['Color']);l.new(nm.outputs[0],p.inputs['Normal'])
 protected=any(w in label for w in ['polymer','rubber','recess','titanium']) or (key in ['vertical','canted'] and index==0)
 if protected:
  if 'titanium' in label:wire((.19,.22,.25,1),'Base Color');wire(.92,'Metallic');wire(.28,'Roughness')
  elif 'recess' in label:wire((.006,.008,.010,1),'Base Color');wire(.72,'Metallic');wire(.42,'Roughness')
  else:wire(oldbc,'Base Color');wire(oldrough,'Roughness');wire(0.,'Metallic')
  return
 coat=texture(O/'Textures/T_SVD_AttachmentCoat_BaseColor.png',True,2)
 coatpack=n.new('ShaderNodeSeparateColor');l.new(texture(O/'Textures/T_SVD_AttachmentCoat_ORM.png',False,2),coatpack.inputs[0])
 w=1.
 if key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring','laser','flashlight','tactical_vertical'] and index==0 or key in ['panoramic_red_dot','prism_scope_2x','lpvo_1_6x'] and index==2:
  w=scalar('MINIMUM',1,scalar('MAXIMUM',0,scalar('MULTIPLY',scalar('SUBTRACT',oldmetal,.2),1/.35)))
  if sourcebase:
   bw=n.new('ShaderNodeRGBToBW');l.new(oldbc,bw.inputs[0]);w=scalar('MULTIPLY',w,scalar('LESS_THAN',bw.outputs[0],.65))
  if key in ['prism_scope_2x','lpvo_1_6x','lpvo_ring','laser','flashlight'] and len(bpy.context.object.data.color_attributes):
   region=n.new('ShaderNodeVertexColor');region.layer_name=bpy.context.object.data.color_attributes[0].name;w=scalar('MULTIPLY',w,region.outputs['Color'])
 wire(mix(oldbc,coat,w),'Base Color')
 wire(mix(oldrough,coatpack.outputs['Green'],w),'Roughness');wire(mix(oldmetal,coatpack.outputs['Blue'],w),'Metallic')
def steel(m,ob):
 m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.027,.034,.041,1);p.inputs['Roughness'].default_value=.31;p.inputs['Metallic'].default_value=.84
def render(obs,name,source):
 scene=bpy.context.scene
 for ob in scene.objects:
  if ob.type=='MESH':ob.hide_render=ob not in obs
 points=[o.matrix_world@v.co for o in obs for v in o.data.vertices]
 lo=Vector([min(p[k] for p in points) for k in range(3)]);hi=Vector([max(p[k] for p in points) for k in range(3)]);center=(lo+hi)*.5;size=hi-lo
 c=bpy.data.cameras.new('SVD_IconCamera');camera=bpy.data.objects.new('SVD_IconCamera',c);scene.collection.objects.link(camera)
 camera.location=center+Vector((0,1.5,0));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();c.type='ORTHO';c.ortho_scale=max(size.x,size.z)/.82;c.clip_start=.001;scene.camera=camera
 for label,offset,energy,width in [('Key',(.05,.40,.45),32,.40),('Fill',(-.30,.2,.18),18,.35),('Rim',(.12,-.28,.28),35,.30)]:
  data=bpy.data.lights.new(label,'AREA');data.energy=energy;data.shape='DISK';data.size=width;lamp=bpy.data.objects.new(label,data);scene.collection.objects.link(lamp);lamp.location=center+Vector(offset);lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
 scene.world=bpy.data.worlds.new('NeutralIconWorld');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.18,.18,.18,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
 scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
 scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100;scene.render.film_transparent=True
 scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
 scene.render.filepath=str(I/(name+'.png'));bpy.ops.wm.save_as_mainfile(filepath=str(I/(name+'.blend')));bpy.ops.render.render(write_still=True)
 shutil.copy2(I/(name+'.png'),DEST/(name+'.png'))
 records[name]={'source':str(source),'output':str(DEST/(name+'.png')),'dimensions':[1024,1024],'frame':'+X forward / orthographic +Y camera / muzzle left','purpose':'production UI icon, no game acceptance render'}
 (O/'icons.json').write_text(json.dumps(records,indent=2));print('SVD_ATTACH_ICON_SAVED',name,flush=True)
ids={'holographic':('optic','holographic'),'panoramic_red_dot':('optic','panoramic_red_dot'),'prism_scope_2x':('optic','prism_scope_2x'),'lpvo_1_6x':('optic','lpvo_1_6x'),
 'suppressor':('muzzle','true'),'tactical_suppressor':('muzzle','tactical_suppressor'),'brake':('muzzle','brake'),'titanium_brake':('muzzle','titanium_brake'),
 'vertical':('underbarrel','vertical_foregrip'),'tactical_vertical':('underbarrel','tactical_vertical_foregrip'),'canted':('underbarrel','canted_foregrip'),'prism':('underbarrel','prism_handstop'),'angled':('underbarrel','angled_foregrip'),
 'laser':('tactical','laser'),'flashlight':('tactical','flashlight')}
for key,(slot,variant) in ids.items():
 name='ue_svd_'+slot+'_'+variant
 if name in records:continue
 path=O/('SM_SVD_'+key+'.blend');bpy.ops.wm.open_mainfile(filepath=str(path));obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
 for ob in obs:
  bpy.context.view_layer.objects.active=ob
  for mat in ob.data.materials:
   if mat.name=='SVD_InterfaceSteel':steel(mat,ob)
   else:working(key,mat,geo['meshes'][key]['source_slot_indices'][mat.name])
 bpy.ops.wm.save_as_mainfile(filepath=str(path))
 if key=='lpvo_1_6x':
  with bpy.data.libraries.load(str(O/'SM_SVD_lpvo_ring.blend')) as (a,b):b.objects=[n for n in a.objects if 'LPVO' in n or 'lpvo' in n]
  for ob in b.objects:
   if ob.type!='MESH':continue
   bpy.context.scene.collection.objects.link(ob);obs.append(ob);bpy.context.view_layer.objects.active=ob
   for m in ob.data.materials:working('lpvo_ring',m,0)
   ob.data.transform(Matrix.Translation((-.071,0,.04)))
 # Source optic +X forward; source muzzle +Y forward; fitted root -Y forward.
 xf=Matrix.Identity(4) if slot=='optic' else Matrix.Rotation(-math.pi/2,4,'Z') if slot=='muzzle' else Matrix.Rotation(math.pi/2,4,'Z')
 for ob in obs:ob.data.transform(xf)
 render(obs,name,path)
for slot in ['optic','muzzle','barrel']:
 name='ue_svd_'+slot+'_false'
 if name in records:continue
 bpy.ops.wm.open_mainfile(filepath=str(O/'SVD_Modular_Editable.blend'));r=bpy.data.objects[inputs['rig']];inv=(r.matrix_world@r.data.bones['WPN_root'].matrix_local).inverted();obs=[]
 original=[bpy.data.objects['SM_SVD_'+p] for p in ['ScopeBody','ScopeMount','ScopeLens']] if slot=='optic' else [bpy.data.objects['SM_SVD_Body']]
 for old in original:
  ob=bpy.data.objects.new('SVD_Icon_'+old.name,old.data.copy());bpy.context.scene.collection.objects.link(ob);ob.data.transform(inv@old.matrix_world)
  if slot!='optic':
   bm=bmesh.new();bm.from_mesh(ob.data)
   if slot=='muzzle':remove=[f for f in bm.faces if ob.data.materials[f.material_index].name!='SVD_FactoryMuzzle']
   else:
    ids={i for a in inputs['islands'] if a['min'][1]<-.79 and a['max'][1]>-.63 and a['max'][2]<.052 for i in a['indices']}
    remove=[f for f in bm.faces if not all(v.index in ids for v in f.verts)]
   bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(ob.data);bm.free()
  ob.data.transform(Matrix.Rotation(math.pi/2,4,'Z'));obs.append(ob)
 render(obs,name,O/'SVD_Modular_Editable.blend')
for target,source in {'ue_svd_category_optic':'ue_svd_optic_false','ue_svd_category_muzzle':'ue_svd_muzzle_true','ue_svd_category_underbarrel':'ue_svd_underbarrel_vertical_foregrip','ue_svd_category_tactical':'ue_svd_tactical_laser','ue_svd_category_barrel':'ue_svd_barrel_false','ue_svd_barrel_short':'ue_svd_barrel_false','ue_svd_barrel_long':'ue_svd_barrel_false'}.items():
 shutil.copy2(I/(source+'.png'),DEST/(target+'.png'));records[target]={'reuse':source,'output':str(DEST/(target+'.png')),'reason':'same actual component; barrel choices are numeric only' if 'barrel' in target else 'category representative'}
(O/'icons.json').write_text(json.dumps(records,indent=2));print('SVD_ATTACH_ICONS_COMPLETE',len(records),flush=True)
