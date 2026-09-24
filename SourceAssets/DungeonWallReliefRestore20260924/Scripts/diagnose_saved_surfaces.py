"""Read only: live catalog surface bindings, texture settings and material graphs."""
import json
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
L=u.MaterialEditingLibrary
catalog=json.loads((PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json').read_text())
report={'meshes':{},'materials':{},'textures':{}}
paths=set()
for module in catalog['modules']:
    if module['id'] not in ('Distribution','Transit','Threshold','FreightAssembly','Ventilation'):continue
    for part in module['parts']:
        path=part['mesh']
        if path.endswith(('_Tiles','_Shell')):
            paths.add(path)
            report.setdefault('catalog_overrides',{})[path]=part.get('materials',[])
masters=set()
for path in sorted(paths):
    mesh=u.load_asset(path)
    if not mesh:continue
    row=[]
    for s in mesh.get_editor_property('static_materials'):
        m=s.material_interface
        if not m:continue
        master=m.get_base_material()
        masters.add(master.get_path_name())
        row.append({'slot':str(s.material_slot_name),'material':m.get_path_name(),'master':master.get_path_name()})
    report['meshes'][path]=row
masters.add('/Game/Dungeons/WallDamage20260923/Materials/M_FabWallMortarRelief20260924')
masters.add('/Game/Dungeons/AtmosphereV2/WallRelief/Materials/M_WallMortarRelief')
for path in sorted(masters):
    mat=u.load_asset(path)
    if not mat:continue
    rows=[]
    for e in L.get_material_expressions(mat):
        kind=e.__class__.__name__
        row={'kind':kind,'name':e.get_name()}
        for key in ('parameter_name','default_value','code','sampler_type','texture','coordinate_index','u_tiling','v_tiling'):
            try:
                value=e.get_editor_property(key)
                row[key]=value.get_path_name() if hasattr(value,'get_path_name') else str(value)
            except Exception:pass
        try:row['inputs']=[x.get_name() if x else None for x in L.get_inputs_for_material_expression(mat,e)]
        except Exception:pass
        if row.get('texture'):
            tex=u.load_asset(row['texture']);props={}
            for key in ('compression_settings','srgb','lod_bias','lod_group','max_texture_size','mip_gen_settings','never_stream','flip_green_channel','virtual_texture_streaming'):
                try:props[key]=str(tex.get_editor_property(key))
                except Exception:pass
            props['size']=[tex.blueprint_get_size_x(),tex.blueprint_get_size_y()]
            report['textures'][row['texture']]=props
        rows.append(row)
    report['materials'][path]={'nodes':rows,'tangent_normal':mat.get_editor_property('tangent_space_normal'),
                               'ism':mat.get_editor_property('used_with_instanced_static_meshes'),'nanite':mat.get_editor_property('used_with_nanite')}
(ROOT/'Receipts/surface-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('WALL_SURFACE_DIAGNOSIS',len(report['meshes']),len(report['materials']),len(report['textures']),flush=True)
