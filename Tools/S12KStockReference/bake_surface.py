"""Production bake: 4K structural normal, 2K independent WS mask; no grain."""
import bpy,bmesh,json,sys,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/S12KStockReference20261018'
sys.path.insert(0,str(P/'SourceAssets/WeaponSurface20260930/A762'));import bake_a762 as B
bpy.ops.wm.open_mainfile(filepath=str(O/'Authoring/Saiga12K_SpecialStock_Editable.blend'))
scene=B.setup_cycles();scene.cycles.samples=32
for a in bpy.data.objects:a.hide_render=True;a.hide_set(True)
ob=bpy.data.objects['SM_Saiga12K_SpecialStock'];ob.hide_render=False;ob.hide_set(False);B.select_only(ob)
for s in ob.material_slots:s.material=s.material.copy()
im=bpy.data.images.new('T_Saiga12K_SpecialStock_N',4096,4096,alpha=False,float_buffer=False);im.colorspace_settings.name='Non-Color';im.generated_color=(.5,.5,1,1)
for m in ob.data.materials:
    nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');bs=nt.nodes.new('ShaderNodeBsdfPrincipled');bevel=nt.nodes.new('ShaderNodeBevel');bevel.samples=8;bevel.inputs['Radius'].default_value=.012
    nt.links.new(bevel.outputs['Normal'],bs.inputs['Normal']);nt.links.new(bs.outputs[0],out.inputs['Surface']);target=nt.nodes.new('ShaderNodeTexImage');target.image=im;nt.nodes.active=target
ob.data.uv_layers.active_index=0
scene.render.bake.normal_r='POS_X';scene.render.bake.normal_g='POS_Y';scene.render.bake.normal_b='POS_Z'
bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',margin=12,margin_type='EXTEND',use_clear=True)
im.filepath_raw=str(O/'Textures/T_Saiga12K_SpecialStock_N.png');im.file_format='PNG';im.save();print('SAIGA_STOCK_NORMAL_SAVED',flush=True)
sample=ob.copy();sample.data=ob.data.copy();sample.name='DRUM_MASK_BAKE';scene.collection.objects.link(sample);ob.hide_render=True;ob.hide_set(True);B.select_only(sample)
B.EDGE_RADIUS=.045;B.RAYS=24;B.densify(sample,max_edge=.45,rounds=4)
bm=bmesh.new();bm.from_mesh(sample.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(sample.data);bm.free()
sampling=B.vertex_masks(sample)
mask=bpy.data.images.new('T_Saiga12K_SpecialStock_Mask',2048,2048,alpha=True,float_buffer=True);mask.colorspace_settings.name='Non-Color';B.bake(sample,mask,'UV1');metadata=B.finish(mask,O/'Textures/T_Saiga12K_SpecialStock_Mask.png')
receipt={'complete':True,'normal_resolution':4096,'mask_resolution':2048,'normal_convention':'OpenGL source; flip green exactly once in UE','normal_uv':0,'mask_uv':1,'grain':False,'source_sha256':hashlib.sha256((O/'Authoring/stock.json').read_bytes()).hexdigest(),'mask_sampling':sampling,'mask':metadata,'runtime_tested':False}
(O/'Receipts/bake.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('SAIGA_STOCK_SURFACE_BAKED',flush=True)
