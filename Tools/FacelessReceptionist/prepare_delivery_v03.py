from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\Tools\FacelessReceptionist')
s=(p/'export_delivery_v02.py').read_text(encoding='utf-8-sig').replace('V02','V03')
s=s.replace("copies=[]\nfor o in allmeshes:","""# Keep an independently importable clothing mesh on the exact same skeleton.
def merge_copy(objects,name):
 copies=[]
 for obj in objects:
  d=obj.copy();d.data=obj.data.copy();bpy.context.collection.objects.link(d);copies.append(d)
 bpy.ops.object.select_all(action='DESELECT')
 for d in copies:d.select_set(True)
 bpy.context.view_layer.objects.active=copies[0]
 bpy.ops.object.join();result=bpy.context.object;result.name=name
 return result
clothes=merge_copy([o for o in allmeshes if o!=body],'Receptionist_Clothing_RenderMesh')
fbx('SK_FacelessReceptionist_Clothing_V03.fbx',[clothes])
bpy.data.objects.remove(clothes,do_unlink=True)
copies=[]
for o in allmeshes:""")
(p/'export_delivery_v03.py').write_text(s,encoding='utf-8')
s=(p/'import_assets_v02.py').read_text(encoding='utf-8-sig').replace('V02','V03')
s=s.replace("('body','SK_FacelessReceptionist_Body_V03.fbx','SK_FacelessReceptionist_Body')","('body','SK_FacelessReceptionist_Body_V03.fbx','SK_FacelessReceptionist_Body'),('clothes','SK_FacelessReceptionist_Clothing_V03.fbx','SK_FacelessReceptionist_Clothing')")
s=s.replace("V03: anatomical skin repair and continuous outfit. Blender reference rendered; no gameplay test.","V03: clothing motion fit from current UE clips and tailored surface details. No gameplay test.")
s=s.replace("body_mesh=meshes['body'].get_path_name(),","body_mesh=meshes['body'].get_path_name(),clothing_mesh=meshes['clothes'].get_path_name(),")
(p/'import_assets_v03.py').write_text(s,encoding='utf-8')
s=(p/'render_reference_v02.py').read_text(encoding='utf-8-sig').replace('V02','V03')
(p/'render_reference_v03.py').write_text(s,encoding='utf-8')
