import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'G18_Drum50_Editable.blend'))
body=bpy.data.objects['Drum50_AuthoredBody'];neck=bpy.data.objects['Retained_G18_Feed_Neck']
group=bpy.data.objects.new('SM_G18_Drum50_LODGroup',None);group['fbx_type']='LodGroup';bpy.context.collection.objects.link(group)
lods=[]
for lod,ratio in enumerate((1,.50,.24)):
    bpy.ops.object.select_all(action='DESELECT')
    low=body.copy();low.data=body.data.copy();bpy.context.collection.objects.link(low);low.select_set(True);bpy.context.view_layer.objects.active=low
    if lod:
        dec=low.modifiers.new('Distance LOD','DECIMATE');dec.ratio=ratio;bpy.ops.object.modifier_apply(modifier=dec.name)
    feed=neck.copy();feed.data=neck.data.copy();bpy.context.collection.objects.link(feed);feed.select_set(True);bpy.ops.object.join()
    low.name='SM_G18_Drum50_LOD'+str(lod);low.parent=group;lods.append(low)
bpy.ops.object.select_all(action='DESELECT');group.select_set(True)
for ob in lods:ob.select_set(True)
bpy.context.view_layer.objects.active=lods[0]
bpy.ops.export_scene.fbx(filepath=str(O/'Exports/SM_G18_Drum50.fbx'),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.object.select_all(action='DESELECT');lods[0].select_set(True)
bpy.ops.export_scene.gltf(filepath=str(O/'Exports/SM_G18_Drum50.glb'),use_selection=True,export_format='GLB')
print('DRUM_LOD_GROUP_EXPORTED',flush=True)
