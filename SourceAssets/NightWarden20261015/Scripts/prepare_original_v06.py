"""Restore the user's original Meshy body, without derived rig or wardrobe."""
import bpy,json,struct,hashlib
from pathlib import Path
P=Path(__file__).resolve().parents[1];OUT=P/'V06Original'
for folder in ['Authoring','Exports','Textures','Records']:(OUT/folder).mkdir(parents=True,exist_ok=True)
source=P/'Input/NightWarden_Meshy_Original.glb';data=source.read_bytes()
json_size,json_type=struct.unpack_from('<II',data,12);gltf=json.loads(data[20:20+json_size]);bin_offset=20+json_size;bin_size,bin_type=struct.unpack_from('<II',data,bin_offset);binary=data[bin_offset+8:bin_offset+8+bin_size]
roles={'normal':'NormalGL','texture_0':'BaseColor','texture_0_metallic_roughness':'MetallicRoughness'};textures={}
for item in gltf['images']:
 role=roles[item['name']];view=gltf['bufferViews'][item['bufferView']];offset=view.get('byteOffset',0);path=OUT/'Textures'/('T_NW_Original_'+role+'.png')
 path.write_bytes(binary[offset:offset+view['byteLength']]);textures[role]=str(path)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
bpy.ops.import_scene.gltf(filepath=str(source))
body=bpy.data.objects['output'];rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
# Icosphere is the glTF importer's custom bone shape, not an input mesh.
for pb in rig.pose.bones:pb.custom_shape=None
for o in list(bpy.context.scene.objects):
 if o not in (body,rig):bpy.data.objects.remove(o,do_unlink=True)
rig.data.pose_position='REST';bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1.
body.data.calc_loop_triangles();points=[body.matrix_world@v.co for v in body.data.vertices]
report={'stage':'preparing_original','source':str(source),'user_original':r'C:\Users\allan\Downloads\Meshy_AI_Character_output (5).glb','source_sha256':hashlib.sha256(data).hexdigest(),
 'mesh':body.name,'vertices':len(body.data.vertices),'triangles':len(body.data.loop_triangles),'original_bones':len(rig.data.bones),
 'bones':[{'name':b.name,'parent':b.parent.name if b.parent else None} for b in rig.data.bones],
 'bounds_m':{'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]},
 'textures':textures,'material':gltf['materials'][0],'body_topology_modified':False,'weights_modified':False,'rig_modified':False,'scale_modified':False,
 'clothing':False,'props':False,'animations':False,'game_tested':False,'rendered':False,
 'export_unit_policy':'FBX_SCALE_UNITS: meters declared in FBX units; UE converts scene units to centimeters, no 100x armature object scale'}
blend=OUT/'Authoring/NightWarden_Original_Restored.blend';fbx=OUT/'Exports/SK_NightWarden_Original.fbx'
bpy.ops.wm.save_as_mainfile(filepath=str(blend));bpy.ops.object.select_all(action='DESELECT')
for o in (body,rig):o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',
 apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',global_scale=1.,add_leaf_bones=False,bake_anim=False,
 use_armature_deform_only=True,armature_nodetype='NULL',mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP',embed_textures=False)
report.update(stage='original_source_and_fbx_saved',blend=str(blend),fbx=str(fbx))
(OUT/'Records/source_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('NIGHT_WARDEN_ORIGINAL_PREPARED '+json.dumps({k:report[k] for k in ['stage','original_bones','triangles','fbx']}),flush=True)
