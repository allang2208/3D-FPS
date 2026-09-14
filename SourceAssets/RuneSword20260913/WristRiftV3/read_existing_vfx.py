import unreal as u,json
from pathlib import Path
P=Path(__file__).parent
paths=['/Game/NiagaraExamples/Materials/MasterMaterials/M_Distortion',
       '/Game/RPGEnvironmentVFX/Essentials/Materials/M_HeatDistortion',
       '/Game/Realistic_Starter_VFX_Pack_Vol2/Materials/M_Distortion',
       '/Game/Realistic_Starter_VFX_Pack_Vol2/Materials/M_Slash']
report={}
for path in paths:
    mat=u.load_asset(path)
    if not mat:continue
    row={'textures':[t.get_path_name() for t in u.MaterialEditingLibrary.get_used_textures(mat)],'properties':{},'inputs':{}}
    for key in ['blend_mode','shading_model','refraction_method','translucency_pass','two_sided']:
        try:row['properties'][key]=str(mat.get_editor_property(key))
        except Exception as e:row['properties'][key]=str(e)
    for prop in ['NORMAL','OPACITY','REFRACTION','EMISSIVE_COLOR']:
        node=u.MaterialEditingLibrary.get_material_property_input_node(mat,getattr(u.MaterialProperty,'MP_'+prop))
        row['inputs'][prop]=node.get_class().get_name() if node else None
    report[path]=row
(P/'existing_vfx.json').write_text(json.dumps(report,indent=2))
u.log('RUNESWORD_EXISTING_VFX_READ')
