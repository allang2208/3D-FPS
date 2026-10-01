"""HK416 source-preserving mechanical rig, V7 arms and contact-adapted actions.

No automatic reduction, preview or runtime validation. Source mesh roles remain
separate. Static fittings use the skeletal reference frame for exact mounting.
"""
import bpy,bmesh,json,math,sys,re
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;X=O/'Exports';X.mkdir(exist_ok=True)
(X/'Animations').mkdir(exist_ok=True);(X/'Attachments').mkdir(exist_ok=True)
sys.path.insert(0,str(S/'M1911RevolverInspect20260927'))
import author_support as support
bpy.context.preferences.filepaths.save_version=0
inv=json.loads((O/'source_inventory.json').read_text());source={a['name']:a for a in inv['objects'] if a['type']=='MESH'}
base=S/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(base));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
names=list(rest);root=rest['WPN_root'];ri=root.inverted()
actions={k:bpy.data.actions['M4_'+k] for k in ('idle','aim','fire','aim_fire','inspect')}
actions['reload']=bpy.data.actions['M4_MAT_reload']
def action(file,name):
    with bpy.data.libraries.load(str(S/file),link=False) as (src,dst):dst.actions=[name]
    if not dst.actions[0]:raise RuntimeError('Missing source action '+name)
    return dst.actions[0]
actions['reload_empty']=action('M4SlapImpact20260910/M4_Hand_MAT_Editable.blend','M4_MAT_reload_empty')
actions['equip_charge']=action('M4WrapGrip20260910/M4_Hand_MAT_Editable.blend','M4_MAT_equip_charge')
families={'base':actions,'vertical':{}}
for kind in ('idle','aim','fire','aim_fire','reload','reload_empty','equip'):
    families['vertical']['equip_charge' if kind=='equip' else kind]=action('MannyGraspDonor20260912/Final/m4/vertical/M4_Vertical_VRE_Editable.blend','A_M4_Vertical_'+kind+'_VRE')
families['vertical']['inspect']=actions['inspect']
for family in families:
    title=family.title()
    for suffix in ('Enter','Loop','Exit'):
        families[family]['sprint_'+suffix.lower()]=action(f'M4TacticalSprint20260915/{title}/M4_TacticalSprint_{title}_Editable.blend',f'M4_TacticalSprint_{title}_{suffix}')
    families[family]['quick_melee']=action(f'M4QuickMeleeReplica20260919/{title}/M4_QuickCombat_{title}_Editable.blend',f'M4_QuickCombatReplica_{title}')
support.install_bare_arms(r,'M4');arms=[o for o in bpy.context.scene.objects if o.get('inspect_skin_source')]
for ob in list(bpy.context.scene.objects):
    if ob!=r and ob not in arms:bpy.data.objects.remove(ob,do_unlink=True)
for ob in arms:
    ob.hide_set(False);ob.hide_render=False
    for m in ob.data.materials:
        if m:m.name='M_HK416_Manny_'+m.name
for c in list(r.constraints):r.constraints.remove(c)
for b in r.pose.bones:
    for c in list(b.constraints):b.constraints.remove(c)

# Uniform source registration: preserve every source proportion. The 111.5 mm
# grip height and 27.2 mm grip width keep a human-sized AR receiver interface.
# Its grip centre is registered to the accepted M4 hand contact, not whole bounds.
scale=4.;grip=source['Hand_grip_low']['bounds'];grip_center=Vector([(a+b)*.5 for a,b in zip(grip['min'],grip['max'])])
donor=json.loads((O/'mechanical_sources.json').read_text())['donor']
reference=next(x for x in donor['meshes'] if x['name']=='M4_Grip Default Unreal_Export')
target_grip=Vector([(a+b)*.5 for a,b in zip(reference['lo'],reference['hi'])])
rotation=Matrix.Rotation(math.pi,4,'Z');linear=rotation@Matrix.Diagonal((scale,scale,scale,1))
A=Matrix.Translation(target_grip-linear@grip_center)@linear
def point(v):return root@A@Vector(v)

material_groups={'Upper_body':'Upper_Body','Lower_body':'Lower_Body','Stock':'Stock','Muzzle':'Muzzle',
 # Source UVs: the laser/RVG atlas is UDIM 1004; flashlight is UDIM 1001.
 'Laser_Grip':'Accs_1004','Eo_tech':'Accs_1002','Mag_Silencer':'Accs_1003','Flash_Light':'Accs_1001','Glass':'Glass_1002'}
materials={}
def material(source_name,role=''):
    key=source_name+'_'+role
    if key in materials:return materials[key]
    group=material_groups[source_name];name='M_HK416_'+source_name+('_'+role if role else '')
    mat=bpy.data.materials.new(name);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;bs=next(node for node in n if node.type=='BSDF_PRINCIPLED')
    for kind,input_name in [('albedo','Base Color'),('metallic','Metallic'),('roughness','Roughness'),('emissive','Emission Color'),('opacity','Alpha')]:
        file=O/'Original/textures'/(group+'_'+kind+'.jpg')
        if file.exists():
            tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(file),check_existing=True)
            tex.image.colorspace_settings.name='sRGB' if kind in ('albedo','emissive') else 'Non-Color';l.new(tex.outputs[0],bs.inputs[input_name])
    file=O/'Original/textures'/(group+'_normal.png');tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(file),check_existing=True);tex.image.colorspace_settings.name='Non-Color'
    norm=n.new('ShaderNodeNormalMap');l.new(tex.outputs[0],norm.inputs['Color']);l.new(norm.outputs[0],bs.inputs['Normal'])
    bs.inputs['Emission Strength'].default_value=5.0 if role=='Reticle' else .2
    if source_name=='Glass':bs.inputs['Transmission Weight'].default_value=.75;mat.surface_render_method='DITHERED'
    mat['texture_group']=group;materials[key]=mat;return mat

def connected(mesh,first):
    adj=[[] for _ in mesh.vertices]
    for e in mesh.edges:
        a,b=e.vertices;adj[a].append(b);adj[b].append(a)
    found={first};todo=[first]
    while todo:
        for i in adj[todo.pop()]:
            if i not in found:found.add(i);todo.append(i)
    return found

def ancestors(entry):
    all_entries={e['name']:e for e in inv['objects']};result=[];parent=entry.get('parent')
    while parent:result.append(parent);parent=all_entries[parent].get('parent')
    return result
with bpy.data.libraries.load(str(O/'HK416_Original_Editable.blend'),link=False) as (src,dst):dst.objects=list(source)
parts={};groups={key:[] for key in ('body','holographic','laser','flashlight','vertical','suppressor','bullet')};role_records={}
for ob in dst.objects:
    entry=source[ob.name];name=ob.name;line=ancestors(entry)
    role='holographic' if 'EOtech' in line else 'laser' if 'Laser_sight' in line else 'flashlight' if 'T_Flash' in line else 'vertical' if 'RVG_grip' in line else 'suppressor' if name=='Silencer_low' else 'bullet' if 'Bullet' in line else 'body'
    s.collection.objects.link(ob);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.hide_set(False);ob.hide_render=False;ob.modifiers.clear()
    weights={}
    if name=='Triger_low':weights['WPN_Trigger']=connected(ob.data,752)
    if name=='Buttons_low':weights['WPN_BoltCatch']=connected(ob.data,0)
    bone={'Reload_Bar_low':'WPN_ChargingHandle','Piston_low':'WPN_bolt','Magazine_low':'WPN_SOCKET_Magazine'}.get(name,'WPN_root')
    ob.vertex_groups.clear();ob.vertex_groups.new(name=bone).add(list(range(len(ob.data.vertices))),1,'REPLACE')
    for k,ids in weights.items():
        ob.vertex_groups[bone].remove(list(ids));ob.vertex_groups.new(name=k).add(list(ids),1,'REPLACE')
    frame=root@A@Matrix(entry['matrix_world'])
    # The source EOTech sits on the front handguard. Bring the complete assembly
    # to the measured central top rail, clear of the rear diopter's fixed base.
    if role=='holographic':frame=root@A@Matrix.Translation((0,-.035,0))@Matrix(entry['matrix_world'])
    ob.data.transform(frame);ob.data.update()
    group=entry['materials'][0];extra='Magazine' if name=='Magazine_low' else 'Reticle' if name=='cross_hair_low' else ''
    ob.data.materials.clear();ob.data.materials.append(material(group,extra))
    for f in ob.data.polygons:f.material_index=0
    if ob.data.uv_layers:
        # Source FBX contains abandoned UV sets with inconsistent names. Every
        # published PBR group uses its first set; keep that one under one shared
        # name so joining stock/optic parts does not create blank or excess sets.
        for unused in list(ob.data.uv_layers)[1:]:ob.data.uv_layers.remove(unused)
        ob.data.uv_layers[0].name='UVMap'
        ob.data.uv_layers.active_index=0;uv=ob.data.uv_layers[0]
        # Each named source material has a separate exported UDIM tile image.
        tile=math.floor(sum(v.uv.x for v in uv.data)/len(uv.data))
        for v in uv.data:v.uv.x-=tile
        uv.active_render=True
    ob['HK416_SourceObject']=name;ob['HK416_SourceRole']=role;parts[name]=ob;groups[role].append(ob)
    role_records[name]={'role':role,'bone':bone,'mechanical_islands':{k:len(ids) for k,ids in weights.items()},'source_triangles':entry['triangles']}

# Mechanical bone identities and marker points follow this model's interfaces.
newrest={n:m.copy() for n,m in rest.items()}
markers={'WPN_SOCKET_Muzzle':(0,.0936854,.0198872),'WPN_SOCKET_Eject':(.005,-.0005,.0210),
 # Measured through the source diopter aperture and at the front post tip.
 # The old common Z=0.03455 aimed into the solid rear drum below its opening.
 'WPN_RearSight':(0,-.02455,.03739),'WPN_FrontSight':(0,.06692993,.03627359),
 'WPN_ChargingHandle':(0,-.0347,.0261),'WPN_BoltCatch':(-.0044,-.0078,.0150),
 'WPN_Trigger':(0,-.0188,.01054),'WPN_bolt':(.0005,.0004,.0207)}
for n,p in markers.items():newrest[n].translation=point(p)
new_local={n:(newrest[parents[n]].inverted()@m if parents[n] else m) for n,m in newrest.items()}
old_rel={n:ri@m for n,m in rest.items() if n.startswith('WPN_') and n!='WPN_root'}

def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
def export_static(key,objects,sockets=None):
    copies=[]
    for old in objects:
        ob=old.copy();ob.data=old.data.copy();s.collection.objects.link(ob);ob.parent=None;ob.modifiers.clear();ob.vertex_groups.clear();copies.append(ob)
    select(copies);bpy.ops.object.join();ob=copies[0];ob.name='SM_HK416_'+key
    selected=[ob]
    for name,p in (sockets or {}).items():
        socket=bpy.data.objects.new('SOCKET_'+name,None);s.collection.objects.link(socket);socket.parent=ob;socket.location=point(p);selected.append(socket)
    select(selected);file=X/'Attachments'/(ob.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    bpy.data.libraries.write(str(file.with_name(file.stem+'_Editable.blend')),set(selected),fake_user=True)
    static[key]={'fbx':str(file),'objects':[x.name for x in objects],'sockets_source_m':sockets or {}}
    for obj in selected:bpy.data.objects.remove(obj,do_unlink=True)

static={}
export_static('holographic',groups['holographic'],{'SightRear':(0,.0318-.035,.03842),'SightFront':(0,.0418-.035,.03842),'SightUp':(0,.0318-.035,.04842)})
export_static('laser',groups['laser'],{'Emitter':(.0100,.0694,.0232),'AimGuide':(.0100,.0794,.0232)})
export_static('flashlight',groups['flashlight'],{'Emitter':(0,.0788,.00655),'AimGuide':(0,.0888,.00655)})
export_static('vertical',groups['vertical'])
export_static('suppressor',groups['suppressor'],{'Muzzle':(0,.1292,.0198872),'AimGuide':(0,.1392,.0198872)})
for key,objs in [('factory_magazine',[parts['Magazine_low']]),('factory_grip',[parts['Hand_grip_low']]),
    ('factory_stock',[ob for n,ob in parts.items() if 'Stock_Full_low' in ancestors(source[n])]),('factory_barrel',[parts['Muzzle_low']]),('factory_trigger',[parts['Triger_low']]),('factory_sights',[parts['ironsight_low']])]:export_static(key,objs)
for key in groups:
    if key!='body':
        for ob in groups[key]:bpy.data.objects.remove(ob,do_unlink=True)
for ob in groups['body']:
    ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
    mod=ob.modifiers.new('HK416_MechanicalSkin','ARMATURE');mod.object=r
report={'source_archive':'hk416-full-reworked.zip','uniform_scale':scale,'source_to_weapon_root':[list(v) for v in A],
 'root_matrix':[list(v) for v in root],'source_parts':role_records,'static':static,'clips':{},
 'source_triangles':sum(e['triangles'] for e in source.values()),'native_arm_source':str(S/'ModularOutfit20260925/BarePalmV7/Editable/M4_BareArmsV7.blend'),
 'markers_source_m':markers,'material_groups':{m.name:m['texture_group'] for m in materials.values()},'runtime_tested':False}

def smooth(v):v=max(0,min(1,v));return v*v*(3-2*v)
def window(t,a,b,c,d):return smooth((t-a)/max(b-a,1e-6))*(1-smooth((t-c)/max(d-c,1e-6)))
def pose(action,frame):
    r.animation_data_create();r.animation_data.action=action;r.animation_data.action_slot=action.slots[0]
    s.frame_set(math.floor(frame),subframe=frame-math.floor(frame));bpy.context.view_layer.update()
    return {b.name:b.matrix.copy() for b in r.pose.bones}
def hand_shift(p,side,shift):
    if shift.length<1e-8:return
    un='upperarm_'+side;fn='lowerarm_'+side;hn='hand_'+side
    a=p[un].translation.copy();b=p[fn].translation.copy();c=p[hn].translation.copy();l1=(b-a).length;l2=(c-b).length
    for name in names:
        if name==hn or name.endswith('_'+side) and name.startswith(('thumb','index','middle','ring','pinky')):p[name].translation+=shift
    goal=p[hn].translation;axis=(goal-a).normalized();distance=min((goal-a).length,l1+l2-.00001)
    pole=(b-a)-axis*(b-a).dot(axis);pole.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    elbow=a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
    p[un]=Matrix.LocRotScale(a,(b-a).rotation_difference(elbow-a)@p[un].to_quaternion(),p[un].to_scale())
    p[fn]=Matrix.LocRotScale(elbow,(c-b).rotation_difference(goal-elbow)@p[fn].to_quaternion(),p[fn].to_scale())
    for name in names:
        if name.endswith('_'+side) and name.startswith(('upperarm_twist','lowerarm_twist')):
            p[name]=p[parents[name]]@(rest[parents[name]].inverted()@rest[name])

# Sample the original bind/action first. Only then change the rig's reference.
samples={}
s.render.fps=60
for family,clips in families.items():
    for kind,clip in clips.items():
        start,end=map(float,clip.frame_range);count=max(1,round((end-start)*2));rows=[];frames=[]
        for i in range(count+1):
            frame=start+(end-start)*i/count;t=(frame-start)/60;old=pose(clip,frame);p={n:m.copy() for n,m in old.items()}
            for n in old_rel:
                p[n]=old['WPN_root']@(ri@newrest[n])@old_rel[n].inverted()@(old['WPN_root'].inverted()@old[n])
            free=1.
            if kind.startswith('reload'):
                empty=kind=='reload_empty';free=1-window(t,.12,.25,1.52 if empty else 1.7,2.1 if empty else 2.02)
                release=window(t,1.65,2.0,2.18,2.5) if empty else 0
                shift=(p['WPN_BoltCatch'].translation-old['WPN_BoltCatch'].translation)*release
            elif kind=='equip_charge':
                contact=window(t,.04,.16,.49,.63);shift=(p['WPN_ChargingHandle'].translation-old['WPN_ChargingHandle'].translation)*contact;free=1-contact
            else:shift=Vector()
            # Retain the accepted grouped hand shape. Reposition wrist and arm
            # together to the measured HK rail / its RVG contact centre.
            offset=Vector((0,.006 if family=='vertical' else 0,-.013 if family=='vertical' else -.002))
            shift+=old['WPN_root'].to_3x3()@offset*free
            hand_shift(p,'l',shift)
            rows.append({n:(new_local[n].inverted()@(p[parents[n]].inverted()@p[n]) if parents[n] else newrest[n].inverted()@p[n]).decompose() for n in names})
            frames.append((frame-start))
        samples[(family,kind)]=(rows,frames,(end-start)/60,clip.name)
        print('HK416_ACTION_AUTHORED',family,kind,flush=True)

r.animation_data_clear();select([r]);bpy.ops.object.mode_set(mode='EDIT')
for n,m in newrest.items():r.data.edit_bones[n].matrix=m
bpy.ops.object.mode_set(mode='OBJECT')
for b in r.pose.bones:b.matrix_basis=Matrix.Identity(4)
select([r]+arms+groups['body']);s.frame_set(0)
file=X/'SK_HK416_Manny.fbx'
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
report['mesh']=str(file)
for (family,kind),(rows,frames,duration,source_action) in samples.items():
    support.DURATION=duration
    r.animation_data_create();baked=support.bake_action(r,s,'HK416_'+family+'_'+kind,rows,frames)
    s.frame_start=0;s.frame_end=round(duration*60);s.frame_set(0);select([r])
    folder=X/'Animations'/family;folder.mkdir(exist_ok=True);file=folder/('A_HK416_'+family+'_'+kind+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_step=.5,bake_anim_simplify_factor=0)
    report['clips'][family+'/'+kind]={'fbx':str(file),'duration':duration,'source_action':source_action,'sample_rate':120}
    (O/'authoring.json').write_text(json.dumps(report,indent=2))
    print('HK416_ACTION_EXPORTED',family,kind,flush=True)
r.animation_data.action=bpy.data.actions['HK416_base_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'HK416_Gameplay_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2));print('HK416_AUTHORING_COMPLETE',flush=True)
