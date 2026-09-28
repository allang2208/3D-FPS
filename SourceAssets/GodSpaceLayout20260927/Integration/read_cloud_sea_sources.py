"""Read existing cloud texture sources for authoring the coverage threshold."""
import json
from pathlib import Path
import unreal as u
root=Path(__file__).parent/'CloudSeaSources'
root.mkdir(exist_ok=True)
mi=u.load_asset('/Game/Props/GodSpaceLayout20260927/Materials/MI_GodSpaceCloudSea')
report={}
for name in ['Layout_CloudGlobalPattern','Noise_Texture3D','Layout_CloudHeightProfile']:
    tex=u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mi,name)
    if not tex:raise RuntimeError('Existing cloud texture is missing: '+name)
    report[name]={'path':tex.get_path_name(),'type':tex.get_class().get_name(),'srgb':tex.get_editor_property('srgb')}
    if name=='Layout_CloudGlobalPattern':
        report[name]['size']=[tex.blueprint_get_size_x(),tex.blueprint_get_size_y()]
        task=u.AssetExportTask();task.object=tex;task.filename=str(root/'ExistingCloudPattern.exr')
        # Let UE choose a compatible exporter through SupportsObject instead of
        # forcing PNG on the engine's floating-point cloud distribution source.
        task.automated=True;task.prompt=False;task.replace_identical=True
        if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot export coverage authoring source')
(root/'sources.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('GODSPACE_CLOUD_AUTHORING_SOURCES '+json.dumps(report))
