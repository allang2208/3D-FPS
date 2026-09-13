"""Bake restrained geometric edge wear and sparse hairline scratches."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent;T=O/'Textures';T.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ191Hero20260913/QBZ191_Hero_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];r.data.pose_position='REST'
manifest=json.loads((S/'QBZ191Hero20260913/textures.json').read_text())
low=bpy.data.collections['QBZ_LOW'];s.render.engine='CYCLES';s.cycles.samples=16
s.render.bake.use_selected_to_active=False;s.render.bake.use_clear=False;s.render.bake.margin=16
s.render.bake.normal_space='TANGENT';s.render.bake.normal_r='POS_X';s.render.bake.normal_g='POS_Y';s.render.bake.normal_b='POS_Z'
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for d in prefs.devices:d.use=d.type=='OPTIX'
 if any(d.use for d in prefs.devices):s.cycles.device='GPU'
except Exception:pass
for ob in s.objects:
 if ob.type=='MESH':ob.hide_render=True
for group,info in manifest.items():
 objects=[bpy.data.objects[name] for name in info['objects']]
 mat=objects[0].data.materials[0].copy();mat.name='AUTH_QBZ191_Wear_'+group
 n=mat.node_tree.nodes;l=mat.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');out=next(x for x in n if x.type=='OUTPUT_MATERIAL')
 base=bs.inputs['Base Color'].links[0].from_socket;rough=bs.inputs['Roughness'].links[0].from_socket;metal=bs.inputs['Metallic'].links[0].from_socket;normal=bs.inputs['Normal'].links[0].from_socket
 def mathnode(op,a,b=0):
  x=n.new('ShaderNodeMath');x.operation=op
  for i,val in enumerate([a,b]):
   if isinstance(val,(int,float)):x.inputs[i].default_value=val
   else:l.new(val,x.inputs[i])
  return x.outputs[0]
 def noise(vec,scale):
  x=n.new('ShaderNodeTexNoise');x.inputs['Scale'].default_value=scale;x.inputs['Detail'].default_value=2;l.new(vec,x.inputs['Vector']);return x.outputs['Fac']
 def mixcolor(a,b,w):
  x=n.new('ShaderNodeMixRGB');l.new(w,x.inputs[0]);l.new(a,x.inputs[1]);x.inputs[2].default_value=(*b,1);return x.outputs[0]
 coord=n.new('ShaderNodeTexCoord');pos=coord.outputs['Object'];geo=n.new('ShaderNodeNewGeometry')
 # Convex corners carry intermittent wear; broad faces keep their coating.
 edge=mathnode('MULTIPLY',mathnode('MAXIMUM',mathnode('SUBTRACT',geo.outputs['Pointiness'],.503),0),22)
 edge=mathnode('MINIMUM',edge,1)
 patch=mathnode('MULTIPLY',noise(pos,110),noise(pos,370))
 edge=mathnode('MULTIPLY',edge,patch)
 gain={'Body':.20,'Steel':.26,'Rail':.32,'Sights':.20,'Magazine':.12,'Polymer':.10}[group]
 edge=mathnode('MULTIPLY',edge,gain)
 mapping=n.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(1,14,3);l.new(pos,mapping.inputs[0])
 vor=n.new('ShaderNodeTexVoronoi');vor.feature='DISTANCE_TO_EDGE';vor.inputs['Scale'].default_value=190;l.new(mapping.outputs['Vector'],vor.inputs['Vector'])
 line=mathnode('LESS_THAN',vor.outputs['Distance'],.012)
 sparse=mathnode('GREATER_THAN',noise(pos,245),.68)
 scratch=mathnode('MULTIPLY',line,sparse)
 scratch=mathnode('MULTIPLY',scratch,.11 if group in ['Body','Steel','Rail','Sights'] else .065)
 wear=mathnode('MINIMUM',mathnode('ADD',edge,scratch),.38)
 poly=group in ['Magazine','Polymer']
 color=mixcolor(base,(.045,.049,.053) if poly else (.14,.15,.16),wear)
 # Small hand-polished patches change roughness without broad paint stripping.
 polish=mathnode('MULTIPLY',mathnode('GREATER_THAN',noise(pos,28),.65),.025 if poly else .018)
 newrough=mathnode('SUBTRACT',mathnode('ADD',rough,mathnode('MULTIPLY',scratch,.30)),polish)
 newrough=mathnode('MAXIMUM',newrough,.20)
 newmetal=metal if poly else mathnode('MINIMUM',mathnode('ADD',metal,mathnode('MULTIPLY',edge,.35)),1)
 bump=n.new('ShaderNodeBump');bump.invert=True;bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.000012;l.new(scratch,bump.inputs['Height']);l.new(normal,bump.inputs['Normal'])
 l.new(color,bs.inputs['Base Color']);l.new(newrough,bs.inputs['Roughness']);l.new(newmetal,bs.inputs['Metallic']);l.new(bump.outputs[0],bs.inputs['Normal'])
 orm=n.new('ShaderNodeCombineColor');orm.inputs[0].default_value=1;l.new(newrough,orm.inputs[1]);l.new(newmetal,orm.inputs[2])
 emit=n.new('ShaderNodeEmission');target=n.new('ShaderNodeTexImage');n.active=target
 for ob in objects:ob.data.materials.clear();ob.data.materials.append(mat)
 maps={}
 for kind,socket in [('BaseColor',color),('ORM',orm.outputs[0]),('Normal',None)]:
  size=info['size'];im=bpy.data.images.new('T_QBZ191_Wear_'+group+'_'+kind,width=size,height=size,alpha=False,float_buffer=False)
  im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';target.image=im
  if kind=='Normal':l.new(bs.outputs['BSDF'],out.inputs['Surface'])
  else:l.new(socket,emit.inputs['Color']);l.new(emit.outputs[0],out.inputs['Surface'])
  bpy.ops.object.select_all(action='DESELECT')
  for ob in objects:ob.hide_set(False);ob.hide_render=False;ob.select_set(True)
  bpy.context.view_layer.objects.active=objects[-1]
  bpy.ops.object.bake(type='NORMAL' if kind=='Normal' else 'EMIT')
  suffix='NormalGL' if kind=='Normal' else kind
  im.filepath_raw=str(T/(im.name.replace('_Normal','_NormalGL')+'.png'));im.file_format='PNG';im.save();maps[kind]=im
  print('QBZ_WEAR_BAKED',group,kind,flush=True)
 l.new(bs.outputs['BSDF'],out.inputs['Surface']);target.image=None
 runtime=bpy.data.materials.new('M_QBZ191_Wear_'+group);runtime.use_nodes=True;ns=runtime.node_tree.nodes;ls=runtime.node_tree.links;shader=next(x for x in ns if x.type=='BSDF_PRINCIPLED')
 for kind,im in maps.items():
  node=ns.new('ShaderNodeTexImage');node.image=im
  if kind=='BaseColor':ls.new(node.outputs[0],shader.inputs['Base Color'])
  elif kind=='Normal':nm=ns.new('ShaderNodeNormalMap');nm.uv_map='HeroUV';ls.new(node.outputs[0],nm.inputs['Color']);ls.new(nm.outputs[0],shader.inputs['Normal'])
  else:sep=ns.new('ShaderNodeSeparateColor');ls.new(node.outputs[0],sep.inputs[0]);ls.new(sep.outputs[1],shader.inputs['Roughness']);ls.new(sep.outputs[2],shader.inputs['Metallic'])
 for ob in objects:ob.data.materials.clear();ob.data.materials.append(runtime)
 info['material']=runtime.name;info['textures']={k:im.filepath_raw for k,im in maps.items()}
 (O/'textures.json').write_text(json.dumps(manifest,indent=2))
r.data.pose_position='POSE';s.frame_set(0)
for ob in low.objects:ob.hide_render=False
bpy.data.objects['SK_Manny_Arms_Export'].hide_render=False
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ191_Wear_Editable.blend'))
print('QBZ_WEAR_AUTHORING_COMPLETE',flush=True)
