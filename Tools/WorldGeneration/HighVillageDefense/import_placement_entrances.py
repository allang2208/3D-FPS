"""Save the construction-only overlays and their shared red material."""
import json
import os
import sys
from pathlib import Path
import unreal as u

sys.path.insert(0,str(Path(__file__).parent))
import import_kit as kit

dest=kit.PACK+'/PlacementPreview'
source=kit.PROJECT/'SourceAssets/HillsVillageHighWall20261120/PlacementPreview'
run=Path(os.environ['GATEHOUSE_RUN'])
kit.E.make_directory(dest)
mat=kit.A.create_asset('M_EntranceHighlight',dest,u.Material,u.MaterialFactoryNew())
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property('two_sided',True)
mat.set_editor_property('disable_depth_test',True)
red=kit.L.create_material_expression(mat,u.MaterialExpressionConstant3Vector)
red.set_editor_property('constant',u.LinearColor(2.8,.023,.015,1.))
alpha=kit.L.create_material_expression(mat,u.MaterialExpressionConstant)
alpha.set_editor_property('r',.9)
for expression,pin in ((red,u.MaterialProperty.MP_EMISSIVE_COLOR),(alpha,u.MaterialProperty.MP_OPACITY)):
    if not kit.L.connect_material_property(expression,'',pin):
        raise RuntimeError('Cannot connect entrance highlight '+str(pin))
errors=kit.L.recompile_material(mat)
if errors:raise RuntimeError(str(errors))
kit.save(mat)
receipt={'material':mat.get_path_name(),'saved':{}}
for role in ('SM_TowerEntrances','SM_StoneGateEntrances','SM_StairEntrances','SM_WoodGateExterior'):
    kit.create_role(role,{'Coping':mat},receipt,package_root=dest,source_dir=source,
                    receipt_file=run/'importing.json',preserve_silhouette=True)
(run/'saved.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
