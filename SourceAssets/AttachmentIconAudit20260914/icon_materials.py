"""Restore explicit runtime coatings lost by intermediate FBX material export.

Sources: import_m4_drum.py, M1911Attachments/import_assets.py,
RearGripFinish/import_finish.py, StableAntiSlipRearGrip/import_assets.py.
These are icon-scene materials only; engine meshes and PBR maps are untouched.
"""
import bpy
def restore_runtime_finish(ob,row,P):
 key=row['key'];S=P.parent
 def const(bs,pin,value,links):
  for link in list(bs.inputs[pin].links):links.remove(link)
  bs.inputs[pin].default_value=value
 for i,old in enumerate(ob.data.materials):
  if not old:continue
  label=old.name.lower()
  collar=any(s in label for s in ['collar','adaptersteel'])
  drum='magazine_large_drum' in key and ('polymer' in label or 'index' in label)
  prism='prism_handstop' in key and 'polymer' in label
  pistol=key.startswith('ue_m1911_') and row['frame'] in ['X','Y'] and 'tactical_suppressor' not in key and not any(s in label for s in ['glass','reticle','recess'])
  if not (collar or drum or prism or pistol):continue
  mat=old.copy();ob.data.materials[i]=mat;mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;bs=next((x for x in n if x.type=='BSDF_PRINCIPLED'),None)
  if not bs:continue
  if drum:
   if 'index' in label:
    const(bs,'Base Color',(.34,.21,.07,1),l);const(bs,'Metallic',0,l);const(bs,'Roughness',.7,l)
   else:
    base=n.new('ShaderNodeTexImage');base.image=bpy.data.images.load(str(S/'M4Infima/SK_M4_Infima.fbm/Magazine Light_BaseColor.png'),check_existing=True)
    mul=n.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=(.7,.7,.7,1);l.new(base.outputs[0],mul.inputs[1]);l.new(mul.outputs[0],bs.inputs['Base Color'])
    r=n.new('ShaderNodeTexImage');r.image=bpy.data.images.load(str(S/'M4Infima/SK_M4_Infima.fbm/Magazine Light_Roughness.png'),check_existing=True);r.image.colorspace_settings.name='Non-Color'
    rm=n.new('ShaderNodeMath');rm.operation='MULTIPLY_ADD';rm.inputs[1].default_value=.25;rm.inputs[2].default_value=.55;l.new(r.outputs[0],rm.inputs[0]);l.new(rm.outputs[0],bs.inputs['Roughness']);const(bs,'Metallic',0,l)
   continue
  if prism:
   # Runtime handstop polymer is non-metal; FBX translated its untextured graph as white metal.
   const(bs,'Base Color',(.026,.028,.032,1),l);const(bs,'Metallic',0,l);const(bs,'Roughness',.62,l);continue
  if key.startswith('ue_m1911_') or key.startswith('ue_dan_wesson715_'):
   family='DW715' if key.startswith('ue_dan_wesson715_') else 'M1911'
   folder=S/('DanWesson715Attachments20260914' if family=='DW715' else 'M1911Attachments20260913')/'Textures'
   # Match the current mesh's explicit coating channel, never its original atlas UV.
   layers=[uv for uv in ob.data.uv_layers if 'Coating' in uv.name or 'Finish' in uv.name]
   uv=n.new('ShaderNodeUVMap');uv.uv_map=layers[-1].name if layers else ob.data.uv_layers[-1].name
   samples={}
   for kind in ['BaseColor','ORM']:
    tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(folder/f'T_{family}_Attachment_{kind}.png'),check_existing=True);tex.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';l.new(uv.outputs[0],tex.inputs['Vector']);samples[kind]=tex
   sep=n.new('ShaderNodeSeparateColor');l.new(samples['ORM'].outputs[0],sep.inputs[0]);l.new(samples['BaseColor'].outputs[0],bs.inputs['Base Color']);l.new(sep.outputs[1],bs.inputs['Roughness']);l.new(sep.outputs[2],bs.inputs['Metallic'])
  elif collar:
   # Same M4 receiver coating bitmap used by the runtime Phong-conversion material.
   tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(S/'WeaponAttachmentFinish20260913/Textures/T_M4_Receiver_BaseColor.png'),check_existing=True)
   uv=n.new('ShaderNodeUVMap');uv.uv_map=ob.data.uv_layers[1].name if len(ob.data.uv_layers)>1 else ob.data.uv_layers[0].name;l.new(uv.outputs[0],tex.inputs['Vector']);l.new(tex.outputs[0],bs.inputs['Base Color']);const(bs,'Metallic',.8,l);const(bs,'Roughness',.38,l)
