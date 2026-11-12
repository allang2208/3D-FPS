"""Read the locally installed CitySamplePCG hazel donor; never save its packages."""
import json
from pathlib import Path
import unreal as u
root=Path('D:/FPS3D/FPSGAME/SourceAssets/TemperateForestSpecies20261110')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world,'PackageName.RegisterMountPoint /CitySamplePCG/ "D:/FPS3D/FPSGAME/城市示例/Plugins/Experimental/CitySamplePCG/Content/"')
base='/CitySamplePCG/Megaplants/Tree_Common_Hazel'
r=u.AssetRegistryHelpers.get_asset_registry();r.scan_paths_synchronous([base],True)
report={'meshes':[],'materials':{},'api':{}}
for a in r.get_assets_by_path(base,True):
    if str(a.asset_class_path.asset_name)!='StaticMesh':continue
    m=a.get_asset();b=m.get_bounds()
    mats=[s.get_editor_property('material_interface') for s in m.get_editor_property('static_materials')]
    report['meshes'].append({'path':str(a.package_name),'height':b.box_extent.z*2,
                            'materials':[x.get_path_name() for x in mats],
                            'nanite':str(m.get_editor_property('nanite_settings'))})
    for mi in mats:
        lib=u.MaterialEditingLibrary
        report['materials'][mi.get_path_name()]={
            'parent':mi.get_editor_property('parent').get_path_name(),
            'textures':{str(k):lib.get_material_instance_texture_parameter_value(mi,k).get_path_name()
                        for k in lib.get_texture_parameter_names(mi)
                        if lib.get_material_instance_texture_parameter_value(mi,k)}}
report['api']['copy_to_static']=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh.__doc__
report['api']['copy_from_skeletal']=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh.__doc__
(root/'extra_sources.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('HAZEL_DONORS_CAPTURED '+str(len(report['meshes'])))
