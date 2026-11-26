"""Create task-owned R3 producers from the bounded native-asset pipeline."""
from pathlib import Path
T=Path(__file__).parent
def clone(old,new,edit=lambda text:text):
    if (T/new).exists():return
    text=(T/old).read_text(encoding='utf-8-sig').replace('CombatShirtR2','CombatShirtR3').replace('combat2_','combat3_').replace('COMBAT2','COMBAT3').replace('ModernTacticalShirtR220261114','ModernTacticalShirtR320261114');(T/new).write_text(edit(text),encoding='utf-8')
def assembly(text):
    return text.replace("elif name=='RangerNylon'", "elif name in ['RangerNylon','OliveWebbing']").replace("elif name=='CharcoalStretch':", "elif name=='StitchThread':d['materials'][i]=DEST+'/Materials/M_CombatThread'\n        elif name=='CharcoalStretch':")
clone('combat2_assemble.py','combat3_assemble.py',assembly)
def material(text):
    text=text.replace('max_texture_size=1024','max_texture_size=2048').replace('combat2-physical-fields-v3:','combat3-photographic-cloth-v1:')
    text=text.replace("mat.set_editor_property('two_sided',False)","mat.set_editor_property('two_sided',False);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_CLOTH)\n        coord=node(mat,u.MaterialExpressionTextureCoordinate,u_tiling=8/28.8,v_tiling=8/28.8)")
    text=text.replace("if channel=='BaseColor':L.connect", "wire(coord,expression,'UVs')\n            if channel=='BaseColor':L.connect")
    text=text.replace("errors=L.recompile_material(mat)","L.connect_material_property(node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.18,.12,.065,1)),'',u.MaterialProperty.MP_SUBSURFACE_COLOR)\n        L.connect_material_property(node(mat,u.MaterialExpressionConstant,r=.28),'',u.MaterialProperty.MP_CUSTOM_DATA0)\n        errors=L.recompile_material(mat)")
    return text
clone('combat2_save.py','combat3_save.py',material)
clone('combat2_save_artwork.py','combat3_save_artwork.py')
clone('combat2_backpack_capture.py','combat3_backpack_capture.py',lambda text:text.replace("'ModernTacticalFitR320261114']", "'ModernTacticalFitR320261114','ModernTacticalShirtR220261114']"))
clone('combat2_backpack_save.py','combat3_backpack_save.py')
clone('combat2_backpack_run.ps1','combat3_backpack_run.ps1')
clone('combat2_resume.ps1','combat3_resume.ps1')
print('R3_PRODUCERS_READY')
