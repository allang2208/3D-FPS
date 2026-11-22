"""Collect the installed factory face, its PBR inputs and the active crescent bindings."""
import json, os
from pathlib import Path
import unreal as u
batch=Path(os.environ['CRESCENT_BATCH'])
cfg=json.loads((Path(os.environ['FPSGAME_PROJECT'])/'Content/ColdSteelData/tactical-hatchet-modules.json').read_text('utf-8-sig'))
records={}
for id in ('factory','axe_swift_crescent'):
    row=cfg['slots']['blade_1'][id]
    mesh=u.load_asset(row['mesh'])
    slot,link=next(iter(row['materials'].items()))
    mat=u.load_asset(link)
    library=u.MaterialEditingLibrary
    todo=[library.get_material_property_input_node(mat,getattr(u.MaterialProperty,prop)) for prop in
          ('MP_BASE_COLOR','MP_FRONT_MATERIAL','MP_ROUGHNESS','MP_METALLIC','MP_NORMAL')]
    seen=set()
    textures={}
    while todo:
        node=todo.pop()
        if not node or node.get_path_name() in seen: continue
        seen.add(node.get_path_name())
        todo.extend(library.get_inputs_for_material_expression(mat,node))
        if not isinstance(node,u.MaterialExpressionTextureSample) or not node.texture: continue
        t=node.texture
        name=t.get_name().rsplit('_',1)[-1]
        role='ORM' if name=='MetalRough' else name
        entry=dict(asset=t.get_path_name(),srgb=t.get_editor_property('srgb'),flip_green=t.get_editor_property('flip_green_channel'))
        if id=='factory' and role in ('ORM','Normal','BaseColor') and role not in textures:
            path=batch/'Factory'/(role+'.tga')
            task=u.AssetExportTask()
            task.set_editor_properties(dict(object=t,filename=str(path),automated=True,prompt=False,replace_identical=True))
            if not u.Exporter.run_asset_export_task(task) or not path.is_file(): raise RuntimeError('Unable to read '+entry['asset'])
        textures[role]=entry
    if not {'ORM','Normal','BaseColor'}.issubset(textures): raise RuntimeError(str(textures))
    records[id]=dict(mesh=mesh.get_path_name(),slot=slot,slot_materials=[s.material_interface.get_path_name() for s in mesh.static_materials],material=mat.get_path_name(),textures=textures)
(batch/'factory-bindings.json').write_text(json.dumps(records,indent=2),encoding='utf8')
