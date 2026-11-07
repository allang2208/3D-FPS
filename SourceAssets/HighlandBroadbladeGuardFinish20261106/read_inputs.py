"""Read active guard material authoring inputs; no scene or asset mutations."""
from pathlib import Path
import json
import unreal as u
P=Path('D:/FPS3D/FPSGAME/SourceAssets/HighlandBroadbladeGuardFinish20261106')
ROOT=P.parents[1]
cat=json.loads((ROOT/'Content/ColdSteelData/highland-claymore-modules.json').read_text(encoding='utf-8-sig'))
L=u.MaterialEditingLibrary
result={'guards':{},'materials':{}}
for key,spec in cat['slots']['guard'].items():
    mesh=u.load_asset(spec['mesh'])
    slots=[]
    for s in mesh.static_materials:
        m=s.material_interface
        slots.append({'slot':str(s.material_slot_name),'material':m.get_path_name()})
        if m.get_path_name() in result['materials']:continue
        base=m.get_base_material()
        fields={}
        for field in ['BASE_COLOR','NORMAL','ROUGHNESS','METALLIC','EMISSIVE_COLOR','FRONT_MATERIAL']:
            n=L.get_material_property_input_node(base,getattr(u.MaterialProperty,'MP_'+field))
            fields[field]={'name':n.get_name(),'class':n.get_class().get_name(),'desc':str(n.get_editor_property('desc'))} if n else None
        nodes=[]
        for n in L.get_material_expressions(base):
            if isinstance(n,u.MaterialExpressionCustom):
                nodes.append({'name':n.get_name(),'desc':str(n.get_editor_property('desc')),'code':str(n.get_editor_property('code'))})
        result['materials'][m.get_path_name()]={'base':base.get_path_name(),'fields':fields,'custom':nodes}
    result['guards'][key]={'mesh':mesh.get_path_name(),'slots':slots}
(P/'inputs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'guards':result['guards'],'materials':{k:v['fields'] for k,v in result['materials'].items()}},ensure_ascii=False))
