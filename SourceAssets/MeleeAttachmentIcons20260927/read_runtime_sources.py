"""Read only: current static mesh source files and material bindings for the icon audit."""
import unreal as u
import json, copy
from pathlib import Path

P=Path(__file__).resolve().parent
ROOT=P.parents[1]
DATA=ROOT/'Content/ColdSteelData'
def read(name):return json.loads((DATA/name).read_text(encoding='utf-8-sig'))
catalogs={}
for name in ['rune-sword-modules.json','frost-sword-modules.json','highland-claymore-modules.json']:
    cat=read(name);profile=cat['pommel_profile'];lib=read(profile['library'])
    for oid,base in lib['options'].items():
        spec=copy.deepcopy(base)
        fitting=profile.get('interfaces',{}).get(spec['interface'],{})
        for key in ['location_cm','rotation_deg','scale','adapter']:
            if key in profile:spec[key]=profile[key]
            if key in fitting:spec[key]=fitting[key]
        spec.update(lib.get('finishes',{}).get(profile['finish'],{}).get(oid,{}))
        cat['slots']['pommel'][oid]=spec
    catalogs[cat['weapon']]=cat
mesh_paths=set()
for c in catalogs.values():
    for choices in c['slots'].values():
        for spec in choices.values():
            mesh_paths.add(spec['mesh'])
            if 'adapter' in spec:mesh_paths.add(spec['adapter']['mesh'])
assets={};materials={}
def sources(obj):
    try:return list(obj.get_editor_property('asset_import_data').extract_filenames())
    except Exception:return []
def material(mat):
    if mat is None:return None
    path=mat.get_path_name()
    if path in materials:return path
    row={'name':mat.get_name(),'type':mat.get_class().get_name(),'textures':{},'scalars':{},'vectors':{}}
    materials[path]=row
    E=u.MaterialEditingLibrary
    for kind,getter in [('textures',E.get_texture_parameter_names),('scalars',E.get_scalar_parameter_names),('vectors',E.get_vector_parameter_names)]:
        try:names=getter(mat)
        except Exception:names=[]
        for name in names:
            try:
                if kind=='textures':
                    tex=E.get_material_instance_texture_parameter_value(mat,name) if isinstance(mat,u.MaterialInstanceConstant) else E.get_material_default_texture_parameter_value(mat,name)
                    row[kind][str(name)]={'asset':tex.get_path_name(),'sources':sources(tex)} if tex else None
                elif kind=='scalars':
                    fn=E.get_material_instance_scalar_parameter_value if isinstance(mat,u.MaterialInstanceConstant) else E.get_material_default_scalar_parameter_value
                    row[kind][str(name)]=fn(mat,name)
                else:
                    fn=E.get_material_instance_vector_parameter_value if isinstance(mat,u.MaterialInstanceConstant) else E.get_material_default_vector_parameter_value
                    v=fn(mat,name);row[kind][str(name)]=[v.r,v.g,v.b,v.a]
            except Exception as ex:row[kind][str(name)]={'read_error':str(ex)}
    if isinstance(mat,u.MaterialInstanceConstant):row['parent']=material(mat.get_editor_property('parent'))
    return path
for path in sorted(mesh_paths):
    mesh=u.load_asset(path)
    if mesh is None:raise RuntimeError('Missing runtime mesh '+path)
    row={'sources':sources(mesh),'materials':[]}
    for slot in mesh.static_materials:
        row['materials'].append({'slot':str(slot.material_slot_name),'material':material(slot.material_interface)})
    assets[path]=row
for c in catalogs.values():
    for choices in c['slots'].values():
        for spec in choices.values():
            for path in spec.get('materials',{}).values():material(u.load_asset(path))
(P/'runtime_sources.json').write_text(json.dumps({'catalogs':catalogs,'meshes':assets,'materials':materials},ensure_ascii=False,indent=2),encoding='utf-8')
print('MELEE_ICON_RUNTIME_SOURCES '+str(len(assets))+' meshes '+str(len(materials))+' materials; read only')
