from pathlib import Path
import json,unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData'
items=json.loads((DATA/'items.json').read_text(encoding='utf-8-sig'))
L=u.MaterialEditingLibrary
result={'weapons':{},'materials':{}}
fallback={'ue_rune_sword':'rune-sword-modules.json','ue_frost_crystal_sword':'frost-sword-modules.json','ue_steel_warhammer':'warhammer-modules.json'}
for ident,item in items.items():
    if not item.get('isTwoHanded') or item.get('category')!='weapon_melee':continue
    file=item.get('modular_melee_catalog') or item.get('modular_sword_catalog') or fallback.get(ident)
    if not file:raise RuntimeError('Missing module catalog '+ident)
    cat=json.loads((DATA/file).read_text(encoding='utf-8-sig'));blunt=item.get('weaponType')=='blunt'
    slot='hammer_heads' if blunt else 'blade_1'
    entry={'catalog':file,'slot':slot,'variants':{},'native_rune_surfaces':{}}
    def record(path):
        obj=u.load_asset(path)
        if not obj:raise RuntimeError('Missing material '+path)
        master=obj.get_base_material();key=master.get_path_name()
        if key not in result['materials']:
            props={}
            for field in ['BASE_COLOR','NORMAL','ROUGHNESS','METALLIC','EMISSIVE_COLOR','FRONT_MATERIAL']:
                src=L.get_material_property_input_node(master,getattr(u.MaterialProperty,'MP_'+field))
                props[field]={'class':src.get_class().get_name(),'name':src.get_name(),'desc':str(src.get_editor_property('desc'))} if src else None
            expressions=[]
            for n in L.get_material_expressions(master):
                if isinstance(n,(u.MaterialExpressionCustom,u.MaterialExpressionScalarParameter,u.MaterialExpressionTextureSampleParameter2D)):
                    row={'class':n.get_class().get_name(),'desc':str(n.get_editor_property('desc'))}
                    if isinstance(n,u.MaterialExpressionCustom):row['code']=str(n.get_editor_property('code'));row['inputs']=[str(x) for x in L.get_material_expression_input_names(n)]
                    else:row['parameter']=str(n.get_editor_property('parameter_name'))
                    expressions.append(row)
            result['materials'][key]={'blend':str(master.get_editor_property('blend_mode')),'props':props,'expressions':expressions}
        return {'material':obj.get_path_name(),'master':key}
    for variant,spec in cat['slots'][slot].items():
        if 'mesh' not in spec:continue
        mesh=u.load_asset(spec['mesh'])
        if not mesh:raise RuntimeError('Missing mesh '+spec['mesh'])
        mats=[]
        for sm in mesh.get_editor_property('static_materials'):
            name=str(sm.get_editor_property('material_slot_name'));base=sm.get_editor_property('material_interface')
            path=spec.get('materials',{}).get(name) or (base.get_path_name() if base else None)
            if path:mats.append({'slot':name,**record(path)})
        entry['variants'][variant]={'mesh':mesh.get_path_name(),'materials':mats}
    for rune,spec in cat['slots'].get('blade_2',{}).items():
        entry['native_rune_surfaces'][rune]={k:record(v) for k,v in spec.get('surface_materials',{}).items()}
    result['weapons'][ident]=entry
(P/'surface-inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('TWO_HAND_SURFACES',len(result['weapons']),len(result['materials']))
for key,value in result['materials'].items():print(key,value['blend'])
