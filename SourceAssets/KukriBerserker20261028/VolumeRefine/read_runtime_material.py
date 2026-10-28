import unreal as u,json
from pathlib import Path
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriBerserker20261028/VolumeRefine')
L=u.MaterialEditingLibrary
data=[]
for kind in ('Factory','Swift','HeavyBack','FoldedBalanced','Hunter','Canine'):
    path='/Game/Weapons/Kukri20261020/Berserker20261028/Materials/M_Berserker_'+kind
    mat=u.load_asset(path)
    entry={'blade':kind,'nodes':[]}
    for n in L.get_material_expressions(mat):
        if isinstance(n,(u.MaterialExpressionTextureCoordinate,u.MaterialExpressionTextureSampleParameter2D,u.MaterialExpressionCustom)):
            row={'class':n.get_class().get_name(),'name':n.get_name()}
            if isinstance(n,u.MaterialExpressionTextureCoordinate):
                row.update({key:n.get_editor_property(key) for key in ('coordinate_index','u_tiling','v_tiling')})
            if isinstance(n,u.MaterialExpressionTextureSampleParameter2D):row['parameter']=str(n.get_editor_property('parameter_name'))
            if isinstance(n,u.MaterialExpressionCustom):row['code']=n.get_editor_property('code')[:600]
            entry['nodes'].append(row)
    data.append(entry)
(P/'runtime-materials.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('RUNE_MATERIAL_READ_COMPLETE')
