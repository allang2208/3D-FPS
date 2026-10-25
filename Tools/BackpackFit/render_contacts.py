"""Requested diagnostic side views from captured saved meshes, not concept artwork."""
import bpy,json,os,math
from pathlib import Path
import numpy as np
from mathutils import Quaternion,Vector
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ.get('BACKPACK_FIT_RUN_DIR',P/'SourceAssets/BackpackFit20261024/ContactAuditR1'))
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
plan=read(R/'plan.json');records=read(R/'captured.json');report=read(R/'contact_report.json')
contacts=read(R/'native_contacts.json')['cases'] if (R/'native_contacts.json').exists() else []
def rot(q):return np.asarray(Quaternion((q[3],q[0],q[1],q[2])).to_matrix())
def load(path,render=False):
    row=records[path];folder=Path(row['folder']);prefix='render_' if render and 'render_vertices' in row else ''
    return np.fromfile(folder/(prefix+'positions.bin'),dtype='<f4').reshape(-1,3).astype(float),np.fromfile(folder/(prefix+'triangles.bin'),dtype='<i4').reshape(-1,3)
male={b['name']:b for b in records[plan['rigs']['Jason']['body']]['bones']};frames={}
for rig,row in plan['rigs'].items():
    target={b['name']:b for b in records[row['body']]['bones']}['spine_04'];source=male['spine_04']
    matrix=rot(source['rotation'])@rot(target['rotation']).T;shift=np.asarray(target['position'])-np.asarray(source['position'])@matrix;frames[rig]=(matrix,shift)
def norm(rig,v):
    matrix,shift=frames[rig];return (v-shift)@matrix.T
bpy.ops.wm.read_factory_settings(use_empty=True)
def mat(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    node=m.node_tree.nodes.get('Principled BSDF');node.inputs['Base Color'].default_value=(*color,1);node.inputs['Roughness'].default_value=.8
    return m
skin=mat('Torso',(.55,.57,.59));cloth=mat('Clothing',(.12,.35,.52));pack=mat('Cargo',(.47,.25,.08));strap=mat('Harness',(.04,.07,.10));textmat=mat('Text',(.04,.04,.04))
scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=2520;scene.render.resolution_y=1512;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('World');scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.8,.8,.8,1);bg.inputs[1].default_value=.8
scene.view_settings.view_transform='Standard'
for xyz,energy,size in [((0,-5,5),1500,8),((3,-2,1),800,6)]:
    data=bpy.data.lights.new('Studio','AREA');data.energy=energy;data.size=size;ob=bpy.data.objects.new('Studio',data);scene.collection.objects.link(ob);ob.location=xyz;ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
camera=bpy.data.cameras.new('Side');ob=bpy.data.objects.new('Side',camera);scene.collection.objects.link(ob);ob.location=(0,-12,0);ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler();camera.type='ORTHO';camera.ortho_scale=7.4;scene.camera=ob
def mesh(name,v,f,material,col,row,section=False):
    if section:f=f[np.all((v[f,2]>83)&(v[f,2]<159)&(abs(v[f,0])<14),axis=1)]
    me=bpy.data.meshes.new(name);me.from_pydata((v/100-[0,0,1.22]).tolist(),[],f[:,[0,2,1]].tolist());me.update();me.materials.append(material)
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);ob.rotation_euler.z=math.pi/2;ob.location=((col-3)*1.02,0,(1.5-row)*1.03)
def label(text,col,row,below=False):
    curve=bpy.data.curves.new('Label','FONT');curve.body=text;curve.size=.038;curve.align_x='CENTER';curve.materials.append(textmat)
    ob=bpy.data.objects.new('Label',curve);scene.collection.objects.link(ob);ob.rotation_euler.x=math.pi/2;ob.location=((col-3)*1.02,-.65,(1.5-row)*1.03+(-.43 if below else .44))
items=list(dict.fromkeys(r['item'] for r in plan['rows']));short={'ue_portable_backpack':'Portable','ue_mountain_backpack':'Mountain','ue_expedition_backpack':'Expedition','ue_simple_sling_bag':'Sling','ue_pathfinder_backpack':'Pathfinder','ue_farreach_backpack':'Farreach','ue_special_duty_backpack':'Special Duty'}
selected=[]
for row_index,(rig,worst) in enumerate([('Jason',False),('Kaitlin',False),('Jason',True),('Kaitlin',True)]):
    for col,item in enumerate(items):
        choices=[r for r in report['rows'] if r['rig']==rig and r['item']==item and (bool(r['shirt']) if worst else not r['shirt'])]
        metric=max(choices,key=lambda r:r['shell_gap'].get('p90_cm',0))
        row=next(r for r in plan['rows'] if r['rig']==rig and r['item']==item and r['shirt']==metric['shirt']);selected.append({'rig':rig,'item':item,'shirt':row['shirt']})
        contact=next((c for c in contacts if c['rig'].lower()==rig.lower() and c['item']==item and c['shirt']==row['shirt']),None)
        v,f=load(row['body']);mesh('Body',norm(rig,v),f,skin,col,row_index,True)
        if row['garment']:
            v,f=load(row['garment']);mesh('Shirt',norm(rig,v),f,cloth,col,row_index,True)
        v,f=load(row['mesh'],False)
        if contact:
            weights=np.fromfile(Path(records[row['mesh']]['folder'])/'mask.bin',dtype='<f4');field=np.asarray(contact['current_and_previous_wpo'])
            v+=((v-field[:3])@field[3:12].reshape(3,3).T+field[12:15])*weights[:,None]
        mesh('Harness',norm(rig,v),f,strap,col,row_index)
        if row.get('rigid_mesh'):
            placement=contact if contact else row
            v,f=load(row['rigid_mesh']);v=v@rot(placement['rigid_rotation_quat']).T+placement['rigid_location'];mesh('Cargo',norm(rig,v),f,pack,col,row_index)
        label(short[item]+' / '+rig,col,row_index)
        shirt=(row['shirt'].removeprefix('ue_').replace('field_sweater_charcoal','T-shirt').replace('field_sweater','knit').replace('blue_mage_robe','robe') or 'bare')
        label(shirt+' | P90 '+str(round(metric['shell_gap'].get('p90_cm',0),1))+' cm',col,row_index,True)
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(R/'contact_side_sections.png');bpy.ops.render.render(write_still=True)
(R/'rendered_routes.json').write_text(json.dumps({'scope':'reference-pose side sections; central torso slice removes arm occlusion; diagnostic flat materials, not gameplay','routes':selected},indent=2))
print('BACKPACK_CONTACT_VIEWS_COMPLETE',len(selected),flush=True)
