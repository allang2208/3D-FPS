"""Read the installed M249 optical geometry and material contracts; no asset writes."""
import unreal as u,json,hashlib,gc
from pathlib import Path
r=Path(__file__).resolve().parent;r.mkdir(exist_ok=True)
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
out={'meshes':{},'materials':{}}
for key in ('lpvo_1_6x','kv_scope_4x','prism_scope_2x','thermal_scope','lpvo_ring','CommonRail'):
    p='/Game/Weapons/M249/CommonOptics20261108/SM_M249_'+key
    a=u.load_asset(p)
    if not isinstance(a,u.StaticMesh):raise RuntimeError('Missing '+p)
    f=r/('SM_'+key+'.fbx')
    t=u.AssetExportTask();t.object=a;t.filename=str(f);t.automated=True;t.prompt=False;t.replace_identical=True;t.exporter=u.StaticMeshExporterFBX();t.options=u.FbxExportOption()
    if not u.Exporter.run_asset_export_task(t):raise RuntimeError('Export '+p)
    mats=[]
    for s in a.static_materials:
        m=s.material_interface;mp=m.get_path_name();base=m.get_base_material()
        mats.append(dict(slot=str(s.material_slot_name),material=mp))
        if mp not in out['materials']:
            out['materials'][mp]=dict(base=base.get_path_name(),blend=str(base.blend_mode),two_sided=base.get_editor_property('two_sided'),
                scalars={str(n):L.get_material_instance_scalar_parameter_value(m,n) for n in L.get_scalar_parameter_names(m)} if isinstance(m,u.MaterialInstanceConstant) else {})
    sockets={}
    for n in ('SightRear','SightFront','SightUp','ZoomRing','AimCenter'):
        s=a.find_socket(n)
        if s:sockets[n]=dict(location=list(s.relative_location.to_tuple()),rotation=list(s.relative_rotation.to_tuple()))
    file=Path(u.Paths.project_content_dir())/(p.removeprefix('/Game/')+'.uasset')
    out['meshes'][key]=dict(asset=p,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),slots=mats,sockets=sockets,fbx=str(f))
    print('M249_OPTIC_INPUT',key,flush=True)
(r/'inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
gc.collect()
print('M249_OPTIC_INPUTS_COMPLETE',flush=True)
