"""Bake distant LODs in Blender and export an FBX LodGroup for one-pass import."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O/'SVD_ExtendedMagazine_Editable.blend'))
body=bpy.data.objects['SM_SVD_ext_mag']
for ob in list(bpy.context.scene.objects):
    if ob!=body:bpy.data.objects.remove(ob,do_unlink=True)
group=bpy.data.objects.new('SM_SVD_ext_mag',None);bpy.context.collection.objects.link(group)
group['fbx_type']='LodGroup'
body.name='SM_SVD_ext_mag_LOD0';body.parent=group
levels=[body]
for index,ratio in [(1,.5),(2,.2)]:
    part=body.copy();part.data=body.data.copy();part.name='SM_SVD_ext_mag_LOD'+str(index)
    bpy.context.collection.objects.link(part)
    bpy.ops.object.select_all(action='DESELECT');part.hide_set(False);part.select_set(True);bpy.context.view_layer.objects.active=part
    modifier=part.modifiers.new('DistantAttachmentReduction','DECIMATE');modifier.ratio=ratio;modifier.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=modifier.name);levels.append(part)
    part.hide_render=True
bpy.ops.object.select_all(action='DESELECT')
for ob in [group]+levels:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.export_scene.fbx(filepath=str(O/'Exports/SM_SVD_ext_mag.fbx'),use_selection=True,object_types={'MESH','EMPTY'},
    axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,use_custom_props=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVD_ExtendedMagazine_LODs.blend'))
record={'group':'LodGroup','lods':[{'object':ob.name,'triangles':len(ob.data.polygons)} for ob in levels]}
(O/'lod_authoring.json').write_text(json.dumps(record,indent=2));print('SVD_EXTMAG_LODS '+json.dumps(record),flush=True)
