"""Export native wear LODs and final inventory artwork from the saved masters.

Only production inventory PNGs are rendered; no acceptance/preview scenes.
The full-detail editable ModelR1 files are never overwritten.
"""
import ast,gc,sys,types
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from combat_belts_common import *
from geometry_delivery import prepare_geometry

def frozen_functions():
    path=P/'Tools/TacticalMagazineBelt/prepare_delivery.py'
    text=path.read_text(encoding='utf-8-sig');tree=ast.parse(text)
    wanted={'export_objects','mesh_from'}
    code='\n\n'.join(ast.get_source_segment(text,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted)
    namespace=dict(bpy=bpy,np=np)
    exec(compile(code,str(path),'exec'),namespace)
    return namespace['export_objects'],namespace['mesh_from'],sha(path)

export_objects,mesh_from,export_source_hash=frozen_functions()
sys.path.insert(0,str(P/'Tools/WorkwearSet'))
from workwear_inventory import studio

def payload(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    return dict(file=str(path),triangles=len(data['triangles']),vertices=len(data['positions']),sha256=sha(path),
        delivery_repairs=data.get('delivery_repairs',{}))

def materials(row,objects):
    src=source(row);families={f['name']:f for f in read(src/'textures.json')['maps']}
    rows=[]
    for mat in objects[0].data.materials:
        bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        family=families.get(mat.name,{})
        rows.append(dict(name=mat.name,family=mat.name if family else None,
            color=list(bs.inputs['Base Color'].default_value)[:3],roughness=bs.inputs['Roughness'].default_value,
            metallic=bs.inputs['Metallic'].default_value,cloth=family.get('kind') in ('nylon','webbing','pad','suede'),
            transmission=bs.inputs['Transmission Weight'].default_value,
            emission=list(bs.inputs['Emission Color'].default_value)[:3],emission_strength=bs.inputs['Emission Strength'].default_value,
            ior=bs.inputs['IOR'].default_value))
    return rows

def produce(which):
    row=BELTS[which];src=source(row);out=R/which;out.mkdir(parents=True,exist_ok=True)
    saved_path=out/'saved_assets.json'
    if saved_path.exists():
        saved=read(saved_path);saved['completed']=False;saved['pending_geometry_revision']='uv-and-topology-r2';write(saved_path,saved)
    records=[];icon_data=None;material_rows=None
    for body in ('Kaitlin','Jason'):
        blend=Path(row.get('editable_directory',src/'Exports'))/f"{row['stem']}_{body}_Editable.blend"
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        collection=bpy.data.collections['01_EDITABLE_LOD0'];collection.hide_viewport=False
        objects=[o for o in collection.objects if o.type=='MESH']
        inputs=next(v for v in read(src/'inputs.json')['records'] if v['body']==body)
        bones=read(inputs['native_reference'])['bones']
        if material_rows is None:material_rows=materials(row,objects)
        # Evaluate the full source once. Decimation is confined to derived LODs.
        data=prepare_geometry(export_objects(objects,bones));data['source']=inputs['pants_asset']
        lods=[payload(out/'Geometry'/f'{body}_LOD0.json',data)]
        if body=='Jason':icon_data=data
        mesh=mesh_from(data,'ProductionLODSource')
        for bone in bones:mesh.vertex_groups.new(name=bone['name'])
        for vi,bindings in enumerate(data['weights']):
            for bi,weight in bindings:mesh.vertex_groups[bi].add([vi],weight,'REPLACE')
        for level,ratio in ((1,.55),(2,.22)):
            mod=mesh.modifiers.new('Distance-only topology reduction','DECIMATE')
            mod.ratio=ratio;mod.use_collapse_triangulate=True
            mod.delimit={'MATERIAL','SEAM','SHARP','UV'}
            reduced=prepare_geometry(export_objects([mesh],bones));reduced['source']=inputs['pants_asset']
            lods.append(payload(out/'Geometry'/f'{body}_LOD{level}.json',reduced))
            mesh.modifiers.remove(mod);del reduced;gc.collect()
        bpy.data.objects.remove(mesh,do_unlink=True)
        records.append(dict(body=body,source=inputs['pants_asset'],master=str(blend),master_sha256=sha(blend),lods=lods))
        print('COMBAT_BELT_LODS',which,body,[v['triangles'] for v in lods],flush=True)
    write(out/'materials.json',material_rows)
    # Front is the negative Blender Y direction, shared by both approved belts.
    obj=mesh_from(icon_data,row['stem']+'_InventorySource')
    icons=studio(out,row['key']);icons.FAMILIES[row['key']]=row['family']
    icon_policy=read(P/'Tools/BeltIcons/policy.json')
    icon=icons.render_current(row['key'],obj,item={k:icon_policy[k] for k in ('grid_w','grid_h')},camera_offset=tuple(icon_policy['camera_offset']))
    write(out/'delivery.json',dict(completed=True,item=row['key'],records=records,materials=str(out/'materials.json'),icon=icon,
        icon_source='Full-detail native Jason model; front buckle facing camera',export_helper_sha256=export_source_hash,
        geometry_revision='uv-and-topology-r2',geometry_repair_sha256=sha(Path(__file__).with_name('geometry_delivery.py')),
        lod_policy=dict(preserve_full_detail_lod0=True,ratios=[1.,.55,.22],screen_sizes=[1.,.18,.065]),
        runtime_tested=False,multiplayer_tested=False))
    print('COMBAT_BELT_DELIVERY_READY',which,flush=True)

if __name__=='__main__':
    chosen=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else list(BELTS)
    for which in chosen:produce(which)
