import bpy
from pathlib import Path
P=Path(__file__).parent;S=Path('D:/FPS3D/FPSGAME/SourceAssets');bpy.context.preferences.filepaths.save_version=0
for family in ['M4','AKM','QBZ191']:
 path=P/family/'ResonanceGrip_Surface_Editable.blend';bpy.ops.wm.open_mainfile(filepath=str(path));ob=bpy.data.objects['SM_ResonanceGrip']
 for m in ob.data.materials:
  n=m.node_tree.nodes;l=m.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');uv=n.new('ShaderNodeUVMap');uv.uv_map=ob.data.uv_layers[1].name
  def sample(file,noncolor=False,scale=None):
   t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(file),check_existing=False);t.image.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
   socket=uv.outputs['UV']
   if scale:
    v=n.new('ShaderNodeVectorMath');v.operation='MULTIPLY';v.inputs[1].default_value=(*scale,1);l.new(socket,v.inputs[0]);socket=v.outputs[0]
   l.new(socket,t.inputs['Vector']);return t
  if 'Polymer' in m.name:
   scale={'M4':(12,5),'AKM':(12,2.5),'QBZ191':(10,10)}[family]
   norm=sample(P/'T_Resonance_Polymer_Normal.png',True,scale);nm=n.new('ShaderNodeNormalMap');l.new(norm.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs['Normal'])
   rough=sample(P/'T_Resonance_Polymer_Roughness.png',True,scale);l.new(rough.outputs['Color'],bs.inputs['Roughness'])
  elif family=='M4':
   t=sample(S/'WeaponAttachmentFinish20260913/Textures/T_M4_Receiver_BaseColor.png');l.new(t.outputs['Color'],bs.inputs['Base Color'])
   # Blender working copy retains a representative roughness. UE uses the original Phong function.
   bs.inputs['Roughness'].default_value=.38
  elif family=='AKM':
   for key,pin in [('Base_color','Base Color'),('Roughness','Roughness'),('Metallic','Metallic')]:
    t=sample(S/'AKMArmSupport20260911/Metal'/('T_AKM_Mount_'+key+'.png'),key!='Base_color');l.new(t.outputs['Color'],bs.inputs[pin])
  else:
   folder=S/'StableAntiSlipRearGrip20260913/Selected91727/Textures';t=sample(folder/'T_QBZ191_StableCollar_BaseColor.png');l.new(t.outputs['Color'],bs.inputs['Base Color'])
   t=sample(folder/'T_QBZ191_StableCollar_ORM.png',True);sep=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sep.inputs[0]);l.new(sep.outputs[1],bs.inputs['Roughness']);l.new(sep.outputs[2],bs.inputs['Metallic'])
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(path))
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 bpy.ops.export_scene.gltf(filepath=str(P/family/'ResonanceGrip_Surface.glb'),use_selection=True,export_format='GLB')
