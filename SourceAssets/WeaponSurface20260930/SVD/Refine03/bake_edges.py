"""Bake small manufactured edge normals from captured runtime geometry, UV0.
Asset production only: no beauty renders, preview, game, or validation pass.
"""
import json,sys,hashlib
from pathlib import Path
import bpy,numpy as np
O=Path(__file__).parent
sys.path.insert(0,str(O.parents[1]/'A762'))
import bake_a762 as B
B.GEO=O/'Input'
OUT=O/'Bake';OUT.mkdir(exist_ok=True)
JOBS=[
 ('SVD','SM_SVD_Body_001','Body',4096,.018),
 ('SVD','SVD_FactoryMuzzle','Muzzle',1024,.016),
 ('SVD','M_SVD_BoltCarrier','Bolt',1024,.012),
 ('SVD','SM_SVD_Magazine_001','Magazine',2048,.012),
 ('SVD','SM_SVD_ScopeBody_001','PSO',2048,.012),
 ('SVD','SM_SVD_ScopeMount_001','PSOMount',2048,.016),
 ('tactical_vertical','SVD_tactical_vertical_0','TacticalGrip',2048,.015),
 ('core_stock','SVD_Stock_core_stock_0','CoreStock',2048,.018),
 ('tactical_telescopic','SVD_Stock_tactical_telescopic_0','Telescopic',2048,.018),
]
rp=OUT/'bake_receipt.json'
receipt=json.loads(rp.read_text()) if rp.exists() else {'textures':{},'tested':False}
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=B.setup_cycles();scene.cycles.samples=32
scene.render.bake.normal_space='TANGENT'
scene.render.bake.normal_r='POS_X';scene.render.bake.normal_g='POS_Y';scene.render.bake.normal_b='POS_Z'
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
for key,slot,label,res,radius in JOBS:
 name='T_SVD_R03_'+label+'_N'
 if name in receipt['textures'] and (OUT/(name+'.png')).exists():continue
 ob,h,order=B.build_object(key,np.zeros(3))
 # Isolate this material section in the production copy. Rigid part offsets
 # do not affect tangent-space normals; no arm geometry participates.
 selected=h['slots'].index(slot)
 B.select_only(ob)
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
 ids=np.empty(len(ob.data.polygons),np.int32);ob.data.polygons.foreach_get('material_index',ids)
 ob.data.polygons.foreach_set('select',ids!=selected)
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.delete(type='FACE');bpy.ops.object.mode_set(mode='OBJECT')
 image=bpy.data.images.new(name,width=res,height=res,alpha=False,float_buffer=False)
 image.colorspace_settings.name='Non-Color';image.generated_color=(.5,.5,1,1)
 for mat in ob.data.materials:
  mat.use_nodes=True;nt=mat.node_tree;nt.nodes.clear()
  output=nt.nodes.new('ShaderNodeOutputMaterial');bsdf=nt.nodes.new('ShaderNodeBsdfPrincipled')
  bevel=nt.nodes.new('ShaderNodeBevel');bevel.samples=8;bevel.inputs['Radius'].default_value=radius
  nt.links.new(bevel.outputs['Normal'],bsdf.inputs['Normal']);nt.links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])
  target=nt.nodes.new('ShaderNodeTexImage');target.image=image;nt.nodes.active=target
 bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',margin=12,margin_type='EXTEND',use_clear=True)
 image.filepath_raw=str(OUT/(name+'.png'));image.file_format='PNG';image.save()
 receipt['textures'][name]={'mesh':key,'slot':slot,'resolution':res,'radius_cm':radius,'uv':0,
 'normal_convention':'OpenGL; UE import flip_green_channel=True','combine':'RNM over source detail before wetness',
 'source':str(image.filepath_raw),'sha256':hashlib.sha256(Path(image.filepath_raw).read_bytes()).hexdigest()}
 rp.write_text(json.dumps(receipt,indent=1))
 print('SVD_R03_EDGE_BAKED',name,flush=True)
 bpy.data.objects.remove(ob,do_unlink=True);bpy.data.images.remove(image)
receipt['complete']=True;rp.write_text(json.dumps(receipt,indent=1))
print('SVD_R03_EDGE_PRODUCTION_COMPLETE',len(receipt['textures']),flush=True)
