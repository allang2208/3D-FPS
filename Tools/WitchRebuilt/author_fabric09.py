"""Update only Blender garment shaders to the shared Fabric09 source material."""
import bpy,json,sys,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from fabric09_settings import *
source=json.loads((OUT/'fabric_sources.json').read_text(encoding='utf-8'))
settings={part:parameters(part,source) for part in PARTS}
(OUT/'fabric09_parameters.json').write_text(json.dumps(settings,indent=2),encoding='utf-8')
before=OUT/'Before/Authoring';before.mkdir(parents=True,exist_ok=True)
textures=ROOT/'Refinement20260922/Textures'
for role in ROLES:
 path=ROOT/f'Authoring/WitchRebuilt_{role}.blend'
 if not (before/path.name).exists():shutil.copy2(path,before/path.name)
 bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.preferences.filepaths.save_version=0
 for part,(name,_,_) in PARTS.items():
  obj=bpy.data.objects[name];mat=obj.data.materials[0];p=settings[part]
  mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
  def node(kind):return nodes.new(kind)
  def link(a,b):links.new(a,b)
  def mathnode(op,a,b):
   n=node('ShaderNodeMath');n.operation=op
   for i,v in enumerate((a,b)):
    if isinstance(v,(int,float)):n.inputs[i].default_value=v
    else:link(v,n.inputs[i])
   return n.outputs[0]
  uv=node('ShaderNodeUVMap');uv.uv_map=obj.data.uv_layers[0].name
  if part=='UpperRobe':
   color=node('ShaderNodeVertexColor');color.layer_name='SeamRepair'
   repeat=mathnode('ADD',p['WeaveTiling'],mathnode('MULTIPLY',color.outputs['Alpha'],p['RepairWeaveTiling']-p['WeaveTiling']))
  else:repeat=p['WeaveTiling']
  scaled=node('ShaderNodeVectorMath');scaled.operation='SCALE';link(uv.outputs['UV'],scaled.inputs[0])
  if isinstance(repeat,(int,float)):scaled.inputs['Scale'].default_value=repeat
  else:link(repeat,scaled.inputs['Scale'])
  images=[]
  for suffix in ('N','R'):
   tex=node('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(textures/f'T_Witch_FabricDetail_{suffix}.png'),check_existing=True)
   tex.image.colorspace_settings.name='Non-Color';tex.extension='REPEAT';link(scaled.outputs['Vector'],tex.inputs['Vector']);images.append(tex)
  ntex,rtex=images
  # Stored normals use DirectX Y. Flip that channel in the authoring shader only.
  sep=node('ShaderNodeSeparateColor');link(ntex.outputs['Color'],sep.inputs['Color'])
  combine=node('ShaderNodeCombineColor');link(sep.outputs['Red'],combine.inputs['Red']);link(sep.outputs['Blue'],combine.inputs['Blue'])
  link(mathnode('SUBTRACT',1.,sep.outputs['Green']),combine.inputs['Green'])
  normal=node('ShaderNodeNormalMap');normal.uv_map=uv.uv_map;normal.inputs['Strength'].default_value=p['NormalStrength'];link(combine.outputs['Color'],normal.inputs['Color'])
  detail=mathnode('SUBTRACT',rtex.outputs['Color'],.75)
  col=node('ShaderNodeVectorMath');col.operation='SCALE';col.inputs[0].default_value=p['ClothColor']
  link(mathnode('ADD',1.,mathnode('MULTIPLY',detail,p['ColorDetail'])),col.inputs['Scale'])
  bs=node('ShaderNodeBsdfPrincipled');link(col.outputs['Vector'],bs.inputs['Base Color'])
  link(mathnode('ADD',p['Roughness'],mathnode('MULTIPLY',detail,p['RoughnessDetail'])),bs.inputs['Roughness'])
  bs.inputs['Specular IOR Level'].default_value=p['Specular'];link(normal.outputs['Normal'],bs.inputs['Normal'])
  output=node('ShaderNodeOutputMaterial');link(bs.outputs['BSDF'],output.inputs['Surface'])
  mat['surface_revision']='Fabric09';mat['surface_parameters']=json.dumps(p)
 bpy.ops.wm.save_as_mainfile(filepath=str(path));print('Saved Fabric09 source '+role,flush=True)
(OUT/'source_delivery.json').write_text(json.dumps({'roles':ROLES,'parameters':settings,'changed':'three garment shaders only','mesh_animation_export_required':False,'rendered':False},indent=2),encoding='utf-8')
