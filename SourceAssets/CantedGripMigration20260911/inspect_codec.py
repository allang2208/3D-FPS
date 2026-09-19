import unreal as u,json
from pathlib import Path
a=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel');c=a.get_editor_property('codecs')[0];d={'class':str(c.get_class()),'python_type':str(type(c)),'doc':type(c).__doc__,'dir':dir(c)}
for k in ['ErrorThreshold','error_threshold','DefaultVirtualVertexDistance','default_virtual_vertex_distance','optimization_targets','OptimizationTargets','compression_level']:
 try:d[k]=str(c.get_editor_property(k))
 except Exception as e:d[k]=str(e)
(Path(__file__).parent/'codec_properties.json').write_text(json.dumps(d,indent=2));u.log('CODEC_INSPECTED')
