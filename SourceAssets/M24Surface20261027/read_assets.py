import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent;L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
paths=['/Game/Weapons/M24/Hold20261027/SK_M24_HoldV9']+['/Game/Weapons/M24/Repair20261027/SM_M24_'+x for x in ['m24_custom_scope_6x','m24_factory_suppressor','m24_cheekrest']]
out={'meshes':{},'materials':{},'surface_masters':list(E.list_assets('/Game/Weapons/WeaponSurface/Master',True,False))}
for path in paths:
    ob=u.load_asset(path);slots=ob.materials if isinstance(ob,u.SkeletalMesh) else ob.static_materials
    out['meshes'][path]=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in slots]
    for s in slots:
        m=s.material_interface
        if m.get_path_name() in out['materials']:continue
        row={'class':m.get_class().get_name(),'textures':[],'nodes':[]}
        if isinstance(m,u.Material):
            for n in L.get_material_expressions(m):
                item={'type':n.get_class().get_name()}
                if isinstance(n,u.MaterialExpressionTextureSample):
                    t=n.texture
                    if t:item.update(texture=t.get_path_name(),srgb=t.srgb,compression=str(t.compression_settings),flip_green=t.flip_green_channel);row['textures'].append(item)
                row['nodes'].append(item)
        out['materials'][m.get_path_name()]=row
(O/'current_assets.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('M24_SURFACE_INPUTS_RECORDED')
