import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/TacticalDevices20260913/HunyuanV3'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
source=(O.parent/'WeaponAttachmentFinish20260913/import_finish.py').read_text();exec(source[source.index('def save('):source.index('def is_target(')])
auth=json.loads((O/'HunyuanV3/authoring.json').read_text())
for family in ['M4','AKM','QBZ191']:
 path=D+'/'+family+'/flashlight/M_'+family+'_flashlight_Body'
 m=u.load_asset(path+'_MetalTail') or E.duplicate_asset(path,path+'_MetalTail')
 if E.get_metadata_tag(m,'MetalTail')!='1':
  world=node(m,u.MaterialExpressionWorldPosition)
  local=node(m,u.MaterialExpressionTransformPosition,transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
  link(world,'',local,'Input')
  y=node(m,u.MaterialExpressionComponentMask,r=False,g=True,b=False,a=False);link(local,'',y,'Input')
  # Only the front optical recess retains the original non-metal texture.
  limit=constant(m,-auth[family+'_flashlight']['emitter_blender_m'][1]*100.-.8)
  vertex=node(m,u.MaterialExpressionVertexColor);mask=node(m,u.MaterialExpressionIf)
  link(y,'',mask,'A');link(limit,'',mask,'B')
  link(vertex,'R',mask,'A > B');link(vertex,'R',mask,'A == B');link(constant(m,1.),'',mask,'A < B')
  for prop in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_ROUGHNESS,u.MaterialProperty.MP_METALLIC,u.MaterialProperty.MP_SPECULAR]:
   blend=L.get_material_property_input_node(m,prop)
   if isinstance(blend,u.MaterialExpressionLinearInterpolate):link(mask,'',blend,'Alpha')
  E.set_metadata_tag(m,'MetalTail','1')
 L.recompile_material(m);save(m)
u.log('FLASHLIGHT_METAL_TAIL_SAVED')
