import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent;OUT=P/'UE';OUT.mkdir(exist_ok=True);manifest={}
for asset in ['hp_potion','mp_potion','ammo_556','ammo_762']:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(P/(asset+'_candidate_v02.glb')))
 objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
 for o in objs:
  matrix=o.matrix_world.copy();o.parent=None;o.matrix_world=Matrix.Identity(4);o.data.transform(matrix)
 mats={}
 for o in objs:
  for m in o.data.materials:
   if not m or m.name in mats:continue
   n=m.node_tree.nodes.get('Principled BSDF');entry={k:list(n.inputs[k].default_value) if k=='Base Color' else float(n.inputs[k].default_value) for k in ['Base Color','Metallic','Roughness','Transmission Weight']}
   if n.inputs['Base Color'].is_linked:
    tn=n.inputs['Base Color'].links[0].from_node
    if tn.type=='TEX_IMAGE':
     name=asset+'_'+str(len(mats))+'_base.png';tn.image.filepath_raw=str(OUT/name);tn.image.file_format='PNG';tn.image.save();entry['texture']=name
   mats[m.name]=entry
 bpy.ops.object.select_all(action='DESELECT')
 for o in objs:o.select_set(True)
 bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.join();o=bpy.context.object
 bpy.ops.export_scene.fbx(filepath=str(OUT/(asset+'.fbx')),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z')
 manifest[asset]={'materials':mats,'slots':[m.name for m in o.data.materials]}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
