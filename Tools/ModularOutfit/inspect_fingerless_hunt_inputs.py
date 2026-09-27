"""Read current brown material and Bow binding for the authorized glove rework."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260926/FingerlessHuntV2')
ROOT.mkdir(parents=True,exist_ok=True)
mat=u.load_asset('/Game/Characters/ModularOutfit20260924/Materials/M_FieldGloves_Brown')
report={'material':mat.get_path_name(),'parameters':{},'textures':{},'custom_code':[]}
for x in u.MaterialEditingLibrary.get_material_expressions(mat):
    if isinstance(x,u.MaterialExpressionScalarParameter):report['parameters'][str(x.get_editor_property('parameter_name'))]=float(x.get_editor_property('default_value'))
    if isinstance(x,(u.MaterialExpressionTextureObjectParameter,u.MaterialExpressionTextureSampleParameter2D)):
        t=x.get_editor_property('texture')
        if t:
            row={'path':t.get_path_name()}
            for k in ('srgb','compression_settings','flip_green_channel','lod_bias'):
                try:row[k]=str(t.get_editor_property(k))
                except Exception:pass
            report['textures'][str(x.get_editor_property('parameter_name'))]=row
    if isinstance(x,u.MaterialExpressionCustom):report['custom_code'].append(x.get_editor_property('code'))
(ROOT/'material-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('FINGERLESS_INPUTS_READ',json.dumps({'material':report['material'],'parameters':report['parameters']}))
