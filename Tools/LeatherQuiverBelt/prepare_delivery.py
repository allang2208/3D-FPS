"""Export the authored right-hip model, motion masks and production inventory icon."""
import ast,json,sys
from pathlib import Path
import bpy
import numpy as np

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/LeatherQuiverBelt20261025';D=R/'Delivery';D.mkdir(exist_ok=True)
KEY='ue_leather_quiver_belt'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')),encoding='utf-8')

# Preserve the established UE clockwise/V-flipped native-space contract.
source=P/'Tools/TacticalMagazineBelt/prepare_delivery.py'
tree=ast.parse(source.read_text(encoding='utf-8-sig'))
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name in ('export_objects','mesh_from'):
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),globals())

records=[]
for row in reversed(read(R/'inputs.json')['records']):
    body=row['body'];bpy.ops.wm.open_mainfile(filepath=str(R/'Exports'/f'LeatherQuiverBelt_{body}_Editable.blend'))
    bones=read(row['native_reference'])['bones'];lods=[];attachments=read(R/'Authored'/f'{body}_attachments.json')
    for lod,colname in enumerate(('01_EDITABLE_LOD0','02_EXPORT_LOD1','03_EXPORT_LOD2')):
        col=bpy.data.collections[colname];col.hide_viewport=False
        objects=list(col.objects);data=export_objects(objects,bones);data['source']=row['pants_asset']
        values=[];quiver=[];deps=bpy.context.evaluated_depsgraph_get()
        for ob in objects:
            if ob.type!='MESH':continue
            ev=ob.evaluated_get(deps);me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=deps)
            attr=me.attributes.get('QuiverMotionMask')
            if not attr:raise RuntimeError('Missing authored motion mask '+ob.name)
            values.extend(float(v.value) for v in attr.data)
            if ob.get('assembly_kind')=='quiver':
                for v in me.vertices:
                    p=ob.matrix_world@v.co;quiver.append([p.x*100,-p.y*100,p.z*100])
            ev.to_mesh_clear()
        if len(values)!=len(data['positions']):raise RuntimeError('Motion mask does not match export')
        data['motion_mask']=values
        path=D/f'{body}_LOD{lod}.json';write(path,data);lods.append(dict(file=str(path),triangles=len(data['triangles'])))
        if lod==0:
            attachments['bounds_min']=np.min(quiver,axis=0).tolist();attachments['bounds_max']=np.max(quiver,axis=0).tolist()
            if body=='Jason':icon_data=data
        col.hide_viewport=lod>0
    attachments.update(arrow_mesh='/Game/Weapons/DarkBow20260925/ArmsV2/SM_Bow_WoodArrow.SM_Bow_WoodArrow',frequency_hz=1.7,damping=1.,max_angle_degrees=2.,max_displacement_cm=2.,decorative_arrows=5)
    records.append(dict(body=body,source=row['pants_asset'],lods=lods,quiver_motion=attachments))

families={r['name']:r for r in read(R/'textures.json')['maps']};materials=[]
for name in icon_data['material_slots']:
    mat=bpy.data.materials[name];bs=mat.node_tree.nodes.get('Principled BSDF');cloth='Suede' in name or name=='Flax_Waxed_Stitch'
    materials.append(dict(name=name,family=name if name in families else None,color=list(bs.inputs['Base Color'].default_value)[:3],roughness=bs.inputs['Roughness'].default_value,metallic=bs.inputs['Metallic'].default_value,cloth=cloth,fuzz=.18 if cloth else 0))
write(R/'materials.json',materials)
ob=mesh_from(icon_data,'LeatherQuiverBelt_Inventory_Source')
sys.path.insert(0,str(P/'Tools/WorkwearSet'));from workwear_inventory import studio
icons=studio(R,KEY);icons.FAMILIES[KEY]='LeatherQuiverBelt20261025'
icon=icons.render_current(KEY,ob,item=dict(grid_w=2,grid_h=3),camera_offset=(-3.,-1.4,1.3))
write(R/'delivery.json',dict(completed=True,records=records,icon=icon,side='right',gameplay_ammo_storage=False,runtime_tested=False))
print('LEATHER_QUIVER_DELIVERY_READY',flush=True)
