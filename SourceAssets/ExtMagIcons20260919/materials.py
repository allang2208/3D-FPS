"""Mirror local seam colour/normal blending in the editable icon scene."""
import bpy
def restore_runtime_finish(ob,row,P):
 # The nested M4 shell self-occludes in Cycles on the required viewing side.
 # Disable self-shadowing for this icon copy, retaining geometry and normals.
 if row['gun']=='M4':
  ob.visible_shadow=False
 for index,old in enumerate(ob.data.materials):
  if not old:continue
  mat=old.copy();ob.data.materials[index]=mat;mat.use_nodes=True;n=mat.node_tree.nodes;links=mat.node_tree.links
  baseuv=n.new('ShaderNodeUVMap');baseuv.uv_map=ob.data.uv_layers[0].name
  for tex in [x for x in n if x.type=='TEX_IMAGE']:links.new(baseuv.outputs['UV'],tex.inputs['Vector'])
  for nm in [x for x in n if x.type=='NORMAL_MAP']:nm.uv_map=ob.data.uv_layers[0].name
  if 'Mouth' in mat.name:
   # New interior uses the same native steel crop as the UE mouth material.
   bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
   for kind,pin in [('Base_color','Base Color'),('Roughness','Roughness'),('Metallic','Metallic')]:
    t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(P.parent/'AKMSoviet20260911/Source/ak47fbx_extracted/textures'/('AK_'+kind+'.png')),check_existing=True)
    if kind!='Base_color':t.image.colorspace_settings.name='Non-Color'
    links.new(t.outputs['Color'],bs.inputs[pin])
   continue
  if row['gun']=='QBZ':continue
  uv=n.new('ShaderNodeUVMap');uv.uv_map='SeamUV';packed=n.new('ShaderNodeUVMap');packed.uv_map='SeamBasis0';sep=n.new('ShaderNodeSeparateXYZ');links.new(packed.outputs['UV'],sep.inputs[0]);weight=sep.outputs['X']
  for tex in [x for x in n if x.type=='TEX_IMAGE' and x.image]:
   consumers=list(tex.outputs['Color'].links)
   if not consumers:continue
   alt=n.new('ShaderNodeTexImage');alt.image=tex.image;alt.interpolation=tex.interpolation;alt.extension=tex.extension;links.new(uv.outputs['UV'],alt.inputs['Vector'])
   other=alt.outputs['Color']
   if any(l.to_node.type=='NORMAL_MAP' for l in consumers):
    # Decode alternate normal, rotate by the stored Blender-space matrix,
    # then encode into the UV0 Normal Map node's expected colour range.
    decode=n.new('ShaderNodeVectorMath');decode.operation='MULTIPLY_ADD';decode.inputs[1].default_value=(2,2,2);decode.inputs[2].default_value=(-1,-1,-1);links.new(other,decode.inputs[0])
    components=[]
    for k in range(5):
     q=n.new('ShaderNodeUVMap');q.uv_map='SeamBasis'+str(k);ss=n.new('ShaderNodeSeparateXYZ');links.new(q.outputs[0],ss.inputs[0]);inv=n.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;links.new(ss.outputs['Y'],inv.inputs[1]);components.extend([ss.outputs['X'],inv.outputs[0]])
    matrix=components[1:];combine=n.new('ShaderNodeCombineXYZ')
    for k in range(3):
     r=n.new('ShaderNodeCombineXYZ')
     for j in range(3):links.new(matrix[3*k+j],r.inputs[j])
     dot=n.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';links.new(decode.outputs[0],dot.inputs[0]);links.new(r.outputs[0],dot.inputs[1]);links.new(dot.outputs['Value'],combine.inputs[k])
    encode=n.new('ShaderNodeVectorMath');encode.operation='MULTIPLY_ADD';encode.inputs[1].default_value=(.5,.5,.5);encode.inputs[2].default_value=(.5,.5,.5);links.new(combine.outputs[0],encode.inputs[0]);other=encode.outputs[0]
   mix=n.new('ShaderNodeMixRGB');mix.blend_type='MIX';links.new(weight,mix.inputs[0]);links.new(tex.outputs['Color'],mix.inputs[1]);links.new(other,mix.inputs[2])
   for link in consumers:links.new(mix.outputs[0],link.to_socket)
