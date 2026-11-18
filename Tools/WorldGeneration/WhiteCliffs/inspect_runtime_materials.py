import unreal as u, json
from pathlib import Path
root='/Game/WorldGeneration/TemperateHills/WhiteCliffs/'
rows=[]
for name in ('CliffA','CliffB','LimestoneSpoil'):
    mat=u.load_asset(root+'Materials/M_'+name)
    nodes=[]
    for n in u.MaterialEditingLibrary.get_material_expressions(mat):
        row={'class':n.get_class().get_name(),'name':n.get_name()}
        if isinstance(n,u.MaterialExpressionTextureSample):
            t=n.texture;row.update(texture=t.get_path_name(),srgb=t.srgb,size=[t.blueprint_get_size_x(),t.blueprint_get_size_y()],sampler=str(n.sampler_type))
        if isinstance(n,u.MaterialExpressionConstant):row['value']=n.r
        if isinstance(n,u.MaterialExpressionConstant3Vector):row['value']=str(n.constant)
        if isinstance(n,u.MaterialExpressionClamp):row.update(min=n.get_editor_property('min_default'),max=n.get_editor_property('max_default'))
        nodes.append(row)
    rows.append({'material':mat.get_path_name(),'two_sided':mat.two_sided,'nodes':nodes})
out=Path('D:/FPS3D/FPSGAME/SourceAssets/HillsLandscapeRepair20261117/Materials/runtime-inspection.json')
out.write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows))
