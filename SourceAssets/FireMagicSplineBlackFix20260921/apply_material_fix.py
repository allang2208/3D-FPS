import json,sys,importlib,shutil
from pathlib import Path
import unreal as u
root=Path(u.Paths.project_dir()).resolve()
out=root/'SourceAssets/FireMagicSplineBlackFix20260921'
backup=out/'Before';backup.mkdir(parents=True,exist_ok=True)
for name in ['M_SplineFireSoft','MI_SplineFireFlame','MI_SplineFireFury','M_SplineSmoke','MI_SplineSmoke']:
    src=root/'Content/Skills/FireMagic20260921/SplineV4'/(name+'.uasset')
    dst=backup/src.name
    if not dst.exists():shutil.copy2(src,dst)
sys.path.insert(0,str(root/'Tools/Skills'))
import build_fire_magic_spline as m
importlib.reload(m)
m.materials()
rows=[]
for name in ['MI_SplineFireFlame','MI_SplineFireFury','MI_SplineSmoke']:
    mi=u.load_asset(m.DEST+'/'+name);parent=mi.get_editor_property('parent')
    emission=m.LIB.get_material_property_input_node(parent,u.MaterialProperty.MP_EMISSIVE_COLOR)
    assert isinstance(emission,u.MaterialExpressionEyeAdaptationInverse),name+' exposure output missing'
    inputs=m.LIB.get_inputs_for_material_expression(parent,emission)
    assert inputs and inputs[0],name+' disconnected emission'
    opacity=m.LIB.get_material_property_input_node(parent,u.MaterialProperty.MP_OPACITY)
    assert opacity,name+' disconnected opacity'
    rows.append({'instance':mi.get_path_name(),'emissive_output':emission.get_class().get_name(),
                 'emissive_input':inputs[0].get_name(),'opacity_input':opacity.get_name(),'compiled_and_saved':True})
(out/'material-fix-result.json').write_text(json.dumps({'materials':rows,'game_tested':False},indent=2),encoding='utf8')
print(json.dumps(rows,indent=2))
