"""Package authored LOD meshes as a single FBX LODGroup for UE import."""
import bpy
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1.0
group=bpy.data.objects.new('ShotgunChoke_LODGroup',None)
group['fbx_type']='LodGroup'
bpy.context.collection.objects.link(group)
materials={}
for level in range(3):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(O/'Exports'/f'SM_ShotgunChoke_Box01_LOD{level}.fbx'),use_anim=False)
    for obj in set(bpy.data.objects)-before:
        if obj.type=='MESH':
            for slot in obj.material_slots:
                name=slot.material.name.split('.')[0]
                if name not in materials:materials[name]=slot.material
                slot.material=materials[name]
            obj.parent=group
            obj.name=f'SM_ShotgunChoke_Box01_LOD{level}'
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(filepath=str(O/'Exports/SM_ShotgunChoke_Box01_Lods.fbx'),
    use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',
    bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
print('CHOKE_RUNTIME_LOD_PACKAGE_SAVED',flush=True)
