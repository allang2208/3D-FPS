"""Bake manufactured edge normals and an independent WS1 mask for each mesh."""
import bpy,json,sys,hashlib
import numpy as np
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KDetail20261018'
sys.path.insert(0,str(P/'SourceAssets/WeaponSurface20260930/A762'));import bake_a762 as B
bpy.ops.wm.open_mainfile(filepath=str(O/'Authoring/Saiga12K_SurfaceRebuilt.blend'));scene=B.setup_cycles();scene.cycles.samples=32;scene.render.bake.normal_space='TANGENT';scene.render.bake.normal_r='POS_X';scene.render.bake.normal_g='POS_Y';scene.render.bake.normal_b='POS_Z'
R={'complete':False,'normal_convention':'OpenGL; UE import flip_green_channel=True exactly once','all_over_grain_normal':False,'textures':{}}
prior=json.loads((O/'Receipts/bake.json').read_text()) if (O/'Receipts/bake.json').exists() else {}
(O/'Receipts/bake.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
for key,name,res in [('gun','Saiga12K_SurfaceRebuilt',4096),('ext12','Saiga12K_Ext12_SurfaceRebuilt',2048)]:
 source_sha=hashlib.sha256((O/('Authoring/'+key+'.json')).read_bytes()).hexdigest()
 if prior.get('textures',{}).get(key,{}).get('source_sha256')==source_sha:
  R['textures'][key]=prior['textures'][key];print('SAIGA_BAKE_REUSED_UNCHANGED_SOURCE',key,flush=True);continue
 for a in bpy.data.objects:a.hide_render=True;a.hide_set(True)
 ob=bpy.data.objects[name];ob.hide_render=False;ob.hide_set(False);B.select_only(ob);ob.data.uv_layers.active_index=0
 # Separate material copies allow normal and mask bakes without changing the authoring scene.
 for s in ob.material_slots:s.material=s.material.copy()
 im=bpy.data.images.new('T_Saiga12K_'+key+'_N',res,res,alpha=False,float_buffer=False);im.colorspace_settings.name='Non-Color';im.generated_color=(.5,.5,1,1)
 for m in ob.data.materials:
  nt=m.node_tree;nt.nodes.clear();out=nt.nodes.new('ShaderNodeOutputMaterial');bs=nt.nodes.new('ShaderNodeBsdfPrincipled');bevel=nt.nodes.new('ShaderNodeBevel');bevel.samples=8;bevel.inputs['Radius'].default_value=.012;nt.links.new(bevel.outputs['Normal'],bs.inputs['Normal']);nt.links.new(bs.outputs[0],out.inputs['Surface']);target=nt.nodes.new('ShaderNodeTexImage');target.image=im;nt.nodes.active=target
 bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',margin=12,margin_type='EXTEND',use_clear=True);im.filepath_raw=str(O/('Textures/T_Saiga12K_'+key+'_N.png'));im.file_format='PNG';im.save()
 R['textures'][key]={'normal':im.filepath_raw,'resolution':res,'normal_uv':0,'normal_radius_cm':.012,'source_sha256':source_sha};print('SAIGA_NORMAL_BAKED',key,flush=True)
 copy=ob.copy();copy.data=ob.data.copy();copy.name=key+'_MASK_BAKE';scene.collection.objects.link(copy);ob.hide_render=True;ob.hide_set(True);B.select_only(copy)
 B.EDGE_RADIUS=.045;B.RAYS=24;B.densify(copy,max_edge=.50,rounds=5)
 import bmesh
 bm=bmesh.new();bm.from_mesh(copy.data);loose=[v for v in bm.verts if not v.link_faces]
 if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(copy.data);bm.free()
 R['textures'][key]['mask_sampling']=B.vertex_masks(copy)
 size=res//2;mask=bpy.data.images.new('Saiga_'+key+'_Mask',size,size,alpha=True,float_buffer=True);mask.colorspace_settings.name='Non-Color';B.bake(copy,mask,'UV1');R['textures'][key]['mask']=B.finish(mask,O/('Textures/T_Saiga12K_'+key+'_Mask.png'));bpy.data.objects.remove(copy,do_unlink=True)
 (O/'Receipts/bake.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('SAIGA_MASK_BAKED',key,flush=True)
R['complete']=True;(O/'Receipts/bake.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print('SAIGA_SURFACE_BAKES_COMPLETE',flush=True)
