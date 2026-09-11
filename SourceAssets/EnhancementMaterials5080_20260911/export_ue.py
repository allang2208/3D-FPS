import bpy,json
from pathlib import Path
from mathutils import Matrix
P=Path(__file__).parent; OUT=P/'UE'; OUT.mkdir(exist_ok=True); manifest={}
for asset in ['enhancement_stone','magic_dust']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.gltf(filepath=str(P/'Delivery'/(asset+'.glb')))
 objs=[o for o in bpy.context.scene.objects if o.type=='MESH']; mats={}
 for o in objs:
  matrix=o.matrix_world.copy(); o.parent=None; o.matrix_world=Matrix.Identity(4); o.data.transform(matrix)
  for m in o.data.materials:
   if not m or m.name in mats: continue
   n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
   entry={k:list(n.inputs[k].default_value) if k=='Base Color' else float(n.inputs[k].default_value) for k in ['Base Color','Metallic','Roughness','Transmission Weight']}
   entry['maps']={}
   def trace(socket,channel='RGB'):
    if not socket.is_linked:return None
    link=socket.links[0]; node=link.from_node
    if node.type=='TEX_IMAGE':return node.image,channel,1.0
    if node.type=='MATH' and node.operation=='MULTIPLY':
     linked=next(s for s in node.inputs[:2] if s.is_linked)
     scalar=next(s.default_value for s in node.inputs[:2] if not s.is_linked)
     img,ch,factor=trace(linked,channel);return img,ch,factor*scalar
    if node.type in ['SEPARATE_COLOR','SEPRGB']:
     return trace(node.inputs[0],{'Red':'R','Green':'G','Blue':'B','R':'R','G':'G','B':'B'}[link.from_socket.name])
    if node.type=='NORMAL_MAP':return trace(node.inputs['Color'])
    raise RuntimeError('Unsupported texture chain '+node.type)
   for key in ['Base Color','Metallic','Roughness','Normal']:
    result=trace(n.inputs[key])
    if result:
     img,channel,factor=result; name=asset+'_'+str(len(mats))+'_'+key.replace(' ','_')+'.png'
     img.filepath_raw=str(OUT/name); img.file_format='PNG'; img.save()
     entry['maps'][key]={'file':name,'channel':channel,'factor':factor}
   mats[m.name]=entry
 bpy.ops.object.select_all(action='DESELECT')
 for o in objs:o.select_set(True)
 bpy.context.view_layer.objects.active=objs[0]; bpy.ops.object.join()
 bpy.ops.export_scene.fbx(filepath=str(OUT/(asset+'.fbx')),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z')
 manifest[asset]={'materials':mats}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
