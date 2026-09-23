"""Create production stock option icons; no gameplay or acceptance rendering."""
import bpy,json,ast,math,shutil
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;I=O/'Icons';I.mkdir(exist_ok=True)
DEST=O.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'
geo=json.loads((O/'authoring.json').read_text());records={}
renderer=(O.parent/'SVDAttachments20260923/author_icons.py').read_text().replace("scene.world.node_tree.nodes['Background']","next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')")
tree=ast.parse(renderer)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='render'],type_ignores=[]),'<production icon renderer>','exec'))
bpy.context.preferences.filepaths.save_version=0
for key in [*geo['meshes'],'false']:
 if key=='false':
  bpy.ops.wm.read_factory_settings(use_empty=True);path=O/'Exports/SM_SVD_factory_stock.fbx';bpy.ops.import_scene.fbx(filepath=str(path))
 else:
  path=O/('SM_SVD_'+key+'.blend');bpy.ops.wm.open_mainfile(filepath=str(path))
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
 for ob in obs:
  if key!='false':
   for mat in ob.data.materials:
    info=geo['meshes'][key]['materials'][mat.name];label=info['source_slot'].lower()
    if any(k in label for k in ['polymer','rubber']):continue
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map=ob.data.uv_layers[2].name
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(O.parent/'SVDAttachments20260923/Textures/T_SVD_AttachmentCoat_BaseColor.png'),check_existing=True)
    tex.image.colorspace_settings.name='sRGB';links.new(uv.outputs[0],tex.inputs[0]);links.new(tex.outputs['Color'],p.inputs['Base Color'])
    for pin,value in [('Roughness',.64),('Metallic',.84)]:
     for link in list(p.inputs[pin].links):links.remove(link)
     p.inputs[pin].default_value=value
  ob.data.transform(Matrix.Rotation(math.pi/2,4,'Z')@ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
 render(obs,'ue_svd_stock_'+key,path)
# A weapon-specific category icon uses the original detached shoulder stock.
name='ue_svd_category_stock';source=I/'ue_svd_stock_false.png';shutil.copy2(source,DEST/(name+'.png'))
records[name]={'source':str(source),'output':str(DEST/(name+'.png')),'purpose':'production category icon'}
(O/'icons.json').write_text(json.dumps(records,indent=2))
print('SVD_STOCK_ICONS_AUTHORED',len(records),flush=True)
