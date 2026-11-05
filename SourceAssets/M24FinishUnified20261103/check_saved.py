"""Read back this requested material repair, without playing the game."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;D=json.loads((O/'materials_before.json').read_text());R=json.loads((O/'publish_receipt.json').read_text());L=u.MaterialEditingLibrary
if not R['complete']:raise RuntimeError('Publication incomplete')
report={'mesh_count':len(D['meshes']),'changed_mesh_count':len(R['meshes']),'changed_material_count':len(R['materials']),'errors':[],'bindings':{},'gameplay_tested':False,'rendered':False}
for key,row in D['meshes'].items():
    m=u.load_asset(row['path']);slots=m.materials if isinstance(m,u.SkeletalMesh) else m.static_materials
    expected=R['meshes'].get(row['path'],{}).get('slots',row['slots'])
    live=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in slots]
    if live!=expected:report['errors'].append('Saved binding differs: '+key)
    report['bindings'][key]=live
for source,row in R['materials'].items():
    paths=[row['path']]+([source] if source==R['carbon_runtime_override_saved'] else [])
    for path in paths:
        mi=u.load_asset(path)
        for key,v in row['scalars'].items():
            actual=L.get_material_instance_scalar_parameter_value(mi,key)
            if abs(actual-v)>1e-5:report['errors'].append(path+': scalar '+key)
        for key,v in row['vectors'].items():
            actual=L.get_material_instance_vector_parameter_value(mi,key)
            if max(abs(a-b) for a,b in zip([actual.r,actual.g,actual.b],v[:3]))>1e-5:report['errors'].append(path+': vector '+key)
        for key,v in D['materials'][source]['parameters'].get('texture',{}).items():
            if key in row['textures']:continue
            actual=L.get_material_instance_texture_parameter_value(mi,key)
            if (actual.get_path_name() if actual else None)!=v:report['errors'].append(path+': source texture changed '+key)
    # Source instances/graphs remain intact, except the explicitly owned carbon override.
    if source!=R['carbon_runtime_override_saved']:
        f=Path(u.Paths.project_content_dir())/(source.split('.')[0][6:]+'.uasset')
        if hashlib.sha256(f.read_bytes()).hexdigest()!=D['materials'][source]['sha256']:report['errors'].append('Source material changed '+source)
report['complete']=not report['errors'];(O/'saved_material_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if report['errors']:raise RuntimeError(str(report['errors']))
print('M24_SAVED_FINISH_CHECK',report['changed_material_count'],report['changed_mesh_count'],'errors=0',flush=True)
