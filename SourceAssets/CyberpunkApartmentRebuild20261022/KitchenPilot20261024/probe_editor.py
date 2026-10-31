"""Editor Python bridge capability and current transaction guard, read-only."""
from pathlib import Path
import unreal as u,json,runpy
R=Path(__file__).resolve().parent
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
path='/Game/Props/CyberpunkApartmentKitchen20261024/Materials/M_KP_Enamel'
m=u.load_asset(path)
result=dict(dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],asset_exists=bool(m),create_node=False,save_signatures={})
if m:
    try:
        n=L.create_material_expression(m,u.MaterialExpressionConstant)
        result['create_node']=bool(n)
        if n:
            n.set_editor_property('r',.25)
            L.delete_material_expression(m,n)
    except Exception as e:result['node_error']=repr(e)
print('KITCHEN_BRIDGE_GUARD '+json.dumps(result))
(R/'editor-state.json').write_text(json.dumps(result,indent=2),encoding='utf8')
