"""Package the three authored cosmetic meshes as FBX LODGroups."""
import bpy
from pathlib import Path
O=Path(__file__).parent
for name,folder in [('SM_Super90_ExtendedTube',O/'Exports'),
                    ('SM_Super90_ChokeTubeFit',O/'CompatibleMuzzles/Choke/Exports'),
                    ('SM_Super90_SuppressorTubeFit',O/'CompatibleMuzzles/Suppressor/Exports')]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1.0
    group=bpy.data.objects.new(name+'_LODGroup',None)
    group['fbx_type']='LodGroup';bpy.context.collection.objects.link(group)
    materials={}
    for level in range(3):
        before=set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=str(folder/(name+f'_LOD{level}.fbx')),use_anim=False)
        for obj in set(bpy.data.objects)-before:
            if obj.type=='MESH':
                for slot in obj.material_slots:
                    key=slot.material.name.split('.')[0]
                    if key not in materials:materials[key]=slot.material
                    slot.material=materials[key]
                obj.parent=group;obj.name=name+f'_LOD{level}'
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.fbx(filepath=str(O/'Exports'/(name+'_Lods.fbx')),
        use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE',use_tspace=True)
    print('EXTENDED_TUBE_RUNTIME_PACKAGE_SAVED',name,flush=True)
