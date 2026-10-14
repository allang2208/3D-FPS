import unreal as u
import json,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Skills')
from build_fireball_assets import API,ref,setdata
HELP=getattr(u,'CampfireAssetTools',getattr(u,'RainAssetEditor',None))
dest='/Game/Building/Campfire20261013/TorchFire'
s=u.load_asset(dest+'/NS_CampfireTorchFire');assert s
rows=[]
for emitter,source,name,fade in [('Fire','M_TorchFire','M_CampfireTorchFire',4.),('Smoke','M_Smoke','M_CampfireTorchSmoke',8.)]:
    target=dest+'/'+name
    assert not u.EditorAssetLibrary.does_asset_exist(target),target
    mat=u.EditorAssetLibrary.duplicate_asset('/Game/TorchFire/Material/'+source,target)
    assert mat
    fades=[n for n in u.MaterialEditingLibrary.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionDepthFade)]
    assert len(fades)==1
    node=fades[0]
    node.set_editor_property('fade_distance_default',fade)
    constant=u.MaterialEditingLibrary.create_material_expression(mat,u.MaterialExpressionConstant)
    constant.set_editor_property('r',fade)
    constant.set_editor_property('desc','Campfire contact fade in cm; preserve native flame/smoke shading')
    inputs=[str(n) for n in u.MaterialEditingLibrary.get_material_expression_input_names(node)]
    slot=next(n for n in inputs if 'fade' in n.lower())
    assert u.MaterialEditingLibrary.connect_material_expressions(constant,'',node,slot)
    u.MaterialEditingLibrary.recompile_material(mat)
    assert u.EditorLoadingAndSavingUtils.save_packages([mat.get_outermost()],False)
    setdata('SetRendererData',u.NiagaraExt_RendererData,ref(s,emitter,renderer=0),{'Material':mat.get_path_name()})
    rows.append({'emitter':emitter,'material':mat.get_path_name(),'contact_fade_cm':fade,'input':slot})
assert HELP.compile_rain(s)
assert u.EditorLoadingAndSavingUtils.save_packages([s.get_outermost()],False)
(OUT/'material-adaptation.json').write_text(json.dumps(rows,indent=2))
print('CAMPFIRE_MATERIAL_ADAPTATION_OK')
