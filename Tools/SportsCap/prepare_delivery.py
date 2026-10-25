"""Export authored LODs in the existing UE headwear contract and make the item icon."""
import bpy
import json
import sys
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SportsCap20261024';KEY='ue_charcoal_sports_cap'
D=R/'Delivery';D.mkdir(exist_ok=True)
sys.path.insert(0,str(P/'Tools/WorkwearSet'))
from workwear_inventory import studio


def combined(collection):
    collection.hide_viewport=False
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();parts=[]
    for original in list(collection.objects):
        if original.type!='MESH':continue
        me=bpy.data.meshes.new_from_object(original.evaluated_get(deps),depsgraph=deps,preserve_all_data_layers=True)
        ob=bpy.data.objects.new(original.name+'_Delivery',me);bpy.context.scene.collection.objects.link(ob);ob.matrix_world=original.matrix_world.copy();parts.append(ob)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in parts:ob.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();ob=bpy.context.object
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    return ob


def export(ob,path):
    me=ob.data;me.calc_loop_triangles();uv=me.uv_layers.active
    data=dict(positions=[[v.co.x*100,-v.co.y*100,v.co.z*100] for v in me.vertices],triangles=[],uv=[],normals=[],triangle_materials=[],material_slots=[m.name for m in me.materials],coordinate_contract='UE headwear writer: reflected Y, clockwise triangles, V flipped; OpenGL normal texture flips green on import')
    for tri in me.loop_triangles:
        data['triangles'].append(list(tri.vertices));data['triangle_materials'].append(tri.material_index)
        data['uv'].append([[uv.data[i].uv.x,1-uv.data[i].uv.y] for i in tri.loops])
        data['normals'].append([[me.corner_normals[i].vector.x,-me.corner_normals[i].vector.y,me.corner_normals[i].vector.z] for i in tri.loops])
    path.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    return len(data['triangles'])


rows=[]
for body in ('Kaitlin','Jason'):
    bpy.ops.wm.open_mainfile(filepath=str(R/'Exports'/f'SportsCap_{body}_Editable.blend'))
    paths=[]
    for lod,colname in enumerate(('01_EDITABLE_LOD0','02_EXPORT_LOD1','03_EXPORT_LOD2')):
        ob=combined(bpy.data.collections[colname]);path=D/f'{body}_LOD{lod}.json';triangles=export(ob,path)
        paths.append(dict(file=str(path),triangles=triangles))
        if lod==0 and body=='Jason':
            families={r['name'] for r in json.loads((R/'textures.json').read_text())['maps']}
            materials=[]
            for m in ob.data.materials:
                bs=m.node_tree.nodes.get('Principled BSDF');cloth=m.name not in ('Cap_BlackPolymer','Cap_ReflectiveTape')
                materials.append(dict(name=m.name,family=m.name if m.name in families else None,color=list(bs.inputs['Base Color'].default_value)[:3],roughness=bs.inputs['Roughness'].default_value,metallic=bs.inputs['Metallic'].default_value,cloth=cloth,fuzz=.22 if m.name=='Cap_BlackSweatband' else .10))
            (R/'materials.json').write_text(json.dumps(materials,indent=2),encoding='utf-8')
        bpy.data.objects.remove(ob,do_unlink=True)
        bpy.data.collections[colname].hide_viewport=lod>0
    rows.append(dict(body=body,lods=paths))
# Make only the production inventory icon, from the actual approved cap mesh.
ob=combined(bpy.data.collections['01_EDITABLE_LOD0']);ob.name='SportsCap_Inventory_Source'
icons=studio(R,KEY);icons.FAMILIES[KEY]='SportsCap20261024'
icon=icons.render_current(KEY,ob,item=dict(grid_w=2,grid_h=2),camera_offset=(.85,3.,1.5))
receipt=dict(completed=True,records=rows,icon=icon,source_blends_preserved=True,runtime_tested=False)
(R/'delivery.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
production=R/(KEY+'-production.json');p=json.loads(production.read_text());p['source']=str(R/'Exports/SportsCap_Jason_Editable.blend');production.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
print('SPORTS_CAP_DELIVERY_READY',[(r['body'],[v['triangles'] for v in r['lods']]) for r in rows],flush=True)
