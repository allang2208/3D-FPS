"""Set the authored placement and export the prepared researcher's assets."""
import bpy,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V01')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/FacelessResearcher_V01.blend'))
body=bpy.data.objects['Researcher_CompleteBody']
z=[v.co.z for v in body.data.vertices];native_height=max(z)-min(z);scale=1.88/native_height
shoes=[o for o in bpy.context.scene.objects if o.name.startswith('Researcher_ClosedShoe')]
sole=min(v.co.z for o in shoes for v in o.data.vertices)
placement={'design_height_cm':188.,'native_body_height_cm':native_height*100,'component_scale':scale,
    'capsule_half_height_cm':94.,'native_sole_z_cm':sole*100,'capsule_floor_clearance_cm':2.15,
    'mesh_relative_z_cm':-94.-2.15-sole*100*scale,'method':'uniform authored body scale and sole-based offset; existing Nurse axes; no bone scale keys'}
(ROOT/'placement_manifest.json').write_text(json.dumps(placement,indent=2),encoding='utf-8')
exec(compile(Path('D:/FPS3D/FPSGAME/Tools/FacelessResearcher/export_delivery.py').read_text(encoding='utf-8'),'researcher_exports','exec'))
exec(compile(Path('D:/FPS3D/FPSGAME/Tools/FacelessResearcher/build_import_recipe.py').read_text(encoding='utf-8'),'researcher_import_recipe','exec'))
print('RESEARCHER_DELIVERY_AUTHORED '+json.dumps(placement),flush=True)
