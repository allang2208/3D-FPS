"""Produce UE-native LOD payloads and the actual inventory artwork; no QA views."""
import bpy
import json
import sys
from pathlib import Path
import numpy as np
from mathutils import Vector

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/TacticalMagazineBelt20261024';D=R/'Delivery';D.mkdir(exist_ok=True)
KEY='ue_tactical_magazine_belt'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')),encoding='utf-8')

def export_objects(objects,bones=None):
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
    names={b['name']:i for i,b in enumerate(bones)} if bones else {}
    out=dict(positions=[],triangles=[],normals=[],uv=[],triangle_materials=[],material_slots=[],weights=[])
    for ob in objects:
        if ob.type!='MESH':continue
        ev=ob.evaluated_get(deps);me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=deps);me.calc_loop_triangles();base=len(out['positions']);matrix=ob.matrix_world;normal_matrix=matrix.to_3x3().inverted().transposed();uv=me.uv_layers.active
        if not out['material_slots']:out['material_slots']=[m.name for m in me.materials]
        groups={g.index:names[g.name] for g in ob.vertex_groups if g.name in names}
        for vertex in me.vertices:
            p=matrix@vertex.co;out['positions'].append([p.x*100,-p.y*100,p.z*100])
            if bones:
                weights=sorted([(groups[g.group],g.weight) for g in vertex.groups if g.group in groups and g.weight>1.e-6],key=lambda x:-x[1])[:8]
                total=sum(w for _,w in weights);out['weights'].append([[i,w/total] for i,w in weights])
        for tri in me.loop_triangles:
            out['triangles'].append([base+i for i in tri.vertices]);out['triangle_materials'].append(tri.material_index)
            out['uv'].append([[uv.data[i].uv.x,1-uv.data[i].uv.y] for i in tri.loops]);ns=[]
            for i in tri.loops:
                n=(normal_matrix@me.corner_normals[i].vector).normalized();ns.append([n.x,-n.y,n.z])
            out['normals'].append(ns)
        ev.to_mesh_clear()
    if bones:out['bones']=bones
    out['contract']='Native UE centimetres; reflected Y; clockwise triangles; V flipped; OpenGL normal green flipped on UE import'
    return out

def append_prop(out,prop,slot):
    base=len(out['positions']);basis=np.array(slot['basis']);seat=np.array(slot['seat_cm'])
    out['positions'].extend((np.array(prop['positions'])@basis.T+seat).tolist())
    out['triangles'].extend([[i+base for i in t] for t in prop['triangles']]);out['uv'].extend(prop['uv'])
    out['normals'].extend((np.array(prop['normals'])@basis.T).tolist());out['triangle_materials'].extend(prop['triangle_materials'])
    out['weights'].extend([[[int(i),w] for i,w in slot['weights'].items()] for _ in prop['positions']])
    # The mounting frame changes handedness in UE space; retain clockwise winding.
    if np.linalg.det(basis)<0:
        count=len(prop['triangles'])
        for k in ('triangles','uv','normals'):
            for j in range(len(out[k])-count,len(out[k])):out[k][j].reverse()

def mesh_from(data,name):
    # The payload preserves Blender's index order for the UE clockwise writer.
    me=bpy.data.meshes.new(name);me.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in data['positions']],[],data['triangles']);me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(ob)
    for mat in data['material_slots']:me.materials.append(bpy.data.materials[mat])
    uv=me.uv_layers.new(name='UV0')
    for i,poly in enumerate(me.polygons):
        poly.material_index=data['triangle_materials'][i];poly.use_smooth=True
        for j,li in enumerate(poly.loop_indices):u,v=data['uv'][i][j];uv.data[li].uv=(u,1-v)
    me.normals_split_custom_set([(x,-y,z) for face in data['normals'] for x,y,z in face])
    return ob

inputs=read(R/'inputs.json')['records'];props={};prop_rows=[];records=[]
bpy.ops.wm.open_mainfile(filepath=str(R/'Exports/TacticalBelt_Jason_Editable.blend'))
master=bpy.data.collections['05_MAGAZINE_MASTERS'];master.hide_viewport=False
for kind in ('rifle','pistol'):
    rows=[]
    for lod in range(3):
        data=export_objects([o for o in master.objects if o.name.startswith('MASTER_'+kind+'_LOD'+str(lod)+'_')]);props[kind,lod]=data
        path=D/f'{kind}_LOD{lod}.json';write(path,data);rows.append(dict(file=str(path),triangles=len(data['triangles'])))
    prop_rows.append(dict(kind=kind,lods=rows))
for row in reversed(inputs):
    body=row['body'];bpy.ops.wm.open_mainfile(filepath=str(R/'Exports'/f'TacticalBelt_{body}_Editable.blend'))
    bones=read(row['native_reference'])['bones'];slots=read(R/'Authored'/f'{body}_attachments.json')['slots'];lods=[];empty=[]
    for lod,colname in enumerate(('01_EDITABLE_LOD0','02_EXPORT_LOD1','03_EXPORT_LOD2')):
        col=bpy.data.collections[colname];col.hide_viewport=False;data=export_objects(list(col.objects),bones);data['source']=row['pants_asset']
        path=D/f'{body}_Empty_LOD{lod}.json';write(path,data);empty.append(dict(file=str(path),triangles=len(data['triangles'])))
        for slot in slots:append_prop(data,props[slot['kind'],lod],slot)
        path=D/f'{body}_Loaded_LOD{lod}.json';write(path,data);lods.append(dict(file=str(path),triangles=len(data['triangles'])))
        col.hide_viewport=lod>0
        if body=='Jason' and lod==0:icon_data=data
    records.append(dict(body=body,source=row['pants_asset'],lods=lods,empty_lods=empty))
# Preserve the source models; the studio saves a separate inventory-source blend.
families={r['name']:r for r in read(R/'textures.json')['maps']};materials=[]
for name in icon_data['material_slots']:
    mat=bpy.data.materials[name];bs=mat.node_tree.nodes.get('Principled BSDF');cloth=families.get(name,{}).get('kind') in ('nylon','webbing','pad') or name=='Belt_Tonal_Stitch'
    materials.append(dict(name=name,family=name if name in families else None,color=list(bs.inputs['Base Color'].default_value)[:3],roughness=bs.inputs['Roughness'].default_value,metallic=bs.inputs['Metallic'].default_value,cloth=cloth,fuzz=.14 if cloth else 0))
write(R/'materials.json',materials)
ob=mesh_from(icon_data,'TacticalBelt_Inventory_Source')
sys.path.insert(0,str(P/'Tools/WorkwearSet'));from workwear_inventory import studio
icons=studio(R,KEY);icons.FAMILIES[KEY]='TacticalMagazineBelt20261024'
icon_policy=read(P/'Tools/BeltIcons/policy.json')
icon=icons.render_current(KEY,ob,item={k:icon_policy[k] for k in ('grid_w','grid_h')},camera_offset=tuple(icon_policy['camera_offset']))
write(R/'delivery.json',dict(completed=True,records=records,magazines=prop_rows,icon=icon,default_visual='four decorative loaded magazines',gameplay_ammo_storage=False,runtime_tested=False))
print('TACTICAL_BELT_DELIVERY_READY',[(r['body'],[v['triangles'] for v in r['lods']]) for r in records],flush=True)
