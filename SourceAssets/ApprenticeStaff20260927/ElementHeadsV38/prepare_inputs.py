"""Read the four installed heads and export production inputs; no scene capture."""
from pathlib import Path
import json, shutil
import unreal as u

P=Path(__file__).resolve().parent
PROJECT=P.parents[2]
INPUTS=P/'Inputs';INPUTS.mkdir(parents=True,exist_ok=True)
catalog=json.loads((PROJECT/'Content/ColdSteelData/staff-gunsmith.json').read_text(encoding='utf-8-sig'))
entries=next(c['options'] for c in catalog['columns'] if c['key']=='head_crystal')
receipt={'meshes':[],'materials':{},'playing':u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),'runtime_tested':False}
for entry in entries:
    if entry['id'] not in ('frozen_crystal','magma_core','storm_core'):continue
    mesh=u.load_asset(entry['mesh'])
    if not mesh:raise RuntimeError('Missing head '+entry['id'])
    asset_path=mesh.get_path_name().split('.')[0]
    filename=INPUTS/(mesh.get_name()+'.fbx')
    task=u.AssetExportTask();task.object=mesh;task.filename=str(filename)
    task.automated=True;task.prompt=False;task.replace_identical=True
    task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption()
    task.options.set_editor_property('ascii',False)
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+entry['id'])
    materials=[]
    for slot in mesh.get_editor_property('static_materials'):
        material=slot.material_interface
        path=material.get_path_name().split('.')[0] if material else None
        materials.append({'slot':str(slot.material_slot_name),'material':path})
        if path and path not in receipt['materials']:
            props={}
            for prop in ['blend_mode','shading_model','two_sided']:
                try:props[prop]=str(material.get_editor_property(prop))
                except Exception:pass
            receipt['materials'][path]=props
    bounds=mesh.get_bounds()
    receipt['meshes'].append({'id':entry['id'],'name':entry['name'],'asset':asset_path,'fbx':str(filename),
        'origin_cm':[bounds.origin.x,bounds.origin.y,bounds.origin.z],
        'extent_cm':[bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z],'materials':materials})
paths={x['asset'] for x in receipt['meshes']}|set(receipt['materials'])
for path in paths:
    rel=Path(path.removeprefix('/Game/')+'.uasset');src=PROJECT/'Content'/rel;dest=P/'Before/Content'/rel
    if src.exists() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
(P/'inputs.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('STAFF_ELEMENT_HEADS_INPUTS_EXPORTED '+str(len(receipt['meshes'])))
