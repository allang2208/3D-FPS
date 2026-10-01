"""Render final G18 production UI textures from the saved, current geometry.

No acceptance scene, editor launch or game test. Numeric-only options deliberately
share the real factory part instead of inventing a replacement model.
"""
import bpy,bmesh,json,math,re,sys,shutil
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;P=O.parents[1];S=O.parent/'G18Integration20260929'
I=O/'Icons';I.mkdir(exist_ok=True);SC=O/'Scenes';SC.mkdir(exist_ok=True)
sys.path.insert(0,str(P/'skills/ue5-weapon-workflow/scripts'))
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
ROOT_INV=Matrix(json.loads((O/'source_parts.json').read_text())['root_inverse'])
PARTS=json.loads((S/'attachment_authoring.json').read_text())
records=json.loads((O/'render_receipt.json').read_text()) if '--resume' in sys.argv else {}
bpy.context.preferences.filepaths.save_version=0

def shader(name,color=(.017,.020,.024,1),metal=.85,rough=.44):
    m=bpy.data.materials.new(name);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=color
    bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    return m,bs

def image_node(material,file,noncolor=False):
    node=material.node_tree.nodes.new('ShaderNodeTexImage')
    node.image=bpy.data.images.load(str(file),check_existing=True)
    node.image.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
    return node

def normal_input(material,bs,file,directx=False):
    nodes=material.node_tree.nodes;links=material.node_tree.links
    tex=image_node(material,file,True);color=tex.outputs['Color']
    if directx:
        sep=nodes.new('ShaderNodeSeparateColor');links.new(color,sep.inputs[0])
        inv=nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1
        links.new(sep.outputs['Green'],inv.inputs[1]);combine=nodes.new('ShaderNodeCombineColor')
        links.new(sep.outputs['Red'],combine.inputs['Red']);links.new(inv.outputs[0],combine.inputs['Green'])
        links.new(sep.outputs['Blue'],combine.inputs['Blue']);color=combine.outputs[0]
    norm=nodes.new('ShaderNodeNormalMap');links.new(color,norm.inputs['Color']);links.new(norm.outputs[0],bs.inputs['Normal'])

def gun_material():
    mat,bs=shader('G18_OriginalPBR');links=mat.node_tree.links;T=S/'Textures'
    for field,file in [('Base Color','Base_color'),('Metallic','Metallic'),('Roughness','Roughness')]:
        tex=image_node(mat,T/('T_G18_'+file+'.png'),field!='Base Color');links.new(tex.outputs[0],bs.inputs[field])
    normal_input(mat,bs,T/'T_G18_Normal_DirectX.png',True);return mat

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0

def source_object(file,name):
    with bpy.data.libraries.load(str(file),link=False) as (src,dst):dst.objects=[name]
    ob=dst.objects[0]
    if ob is None:raise RuntimeError('Missing authoring object '+name)
    bpy.context.scene.collection.objects.link(ob);ob.hide_set(False);ob.hide_render=False
    ob.modifiers.clear();ob.parent=None;ob.matrix_world=Matrix.Identity(4)
    return ob

def factory(kind):
    file=S/'Single/G18_single_Editable.blend'
    names=['G18_G18','G18_G18_mag','G18_G18_bullet'] if kind=='equipment' else ['G18_G18']
    mat=gun_material();objects=[]
    for name in names:
        ob=source_object(file,name);ob.data.transform(ROOT_INV);ob.data.uv_layers.active_index=0
        if kind!='equipment':
            if kind=='optic':
                # The complete 44-vertex rear-sight island, disconnected from slide.
                keep={v.index for v in ob.data.vertices if .0399<v.co.y<.0502 and .0364<v.co.z<.0417}
                adj={v.index:set() for v in ob.data.vertices}
                for e in ob.data.edges:
                    a,b=e.vertices;adj[a].add(b);adj[b].add(a)
                keep={1832};todo=[1832]
                while todo:
                    for j in adj[todo.pop()]-keep:keep.add(j);todo.append(j)
            else:
                group=ob.vertex_groups['WPN_Trigger' if kind=='trigger' else 'WPN_Barrel'].index
                keep={v.index for v in ob.data.vertices if any(g.group==group and g.weight>.99 for g in v.groups)}
            bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table()
            bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in keep],context='VERTS')
            bm.to_mesh(ob.data);bm.free()
        ob.data.materials.clear();ob.data.materials.append(mat)
        for face in ob.data.polygons:face.material_index=0
        objects.append(ob)
    return objects,str(file)

def finish_materials(ob,kind):
    if kind in ('factory_magazine','ext_mag','GripSurface'):
        mat=gun_material();ob.data.materials.clear();ob.data.materials.append(mat)
        for face in ob.data.polygons:face.material_index=0
        ob.data.transform(ROOT_INV);return
    if kind in ('laser','flashlight'):
        donor=O.parent/'M1911CompactFit20260913'/kind/'M1911_Device_Editable.blend'
        with bpy.data.libraries.load(str(donor),link=False) as (src,dst):
            dst.materials=[n for n in src.materials if n.startswith('M_Tactical_')]
        mats={re.sub(r'[._]\d{3}$','',m.name):m for m in dst.materials}
        for slot in ob.material_slots:
            key=re.sub(r'[._]\d{3}$','',slot.material.name)
            if key in mats:slot.material=mats[key]
        if len(ob.data.uv_layers)>1:ob.data.uv_layers[1].name='M1911Coating'
        if kind=='flashlight':
            for im in bpy.data.images:
                if im.source=='FILE' and not im.packed_file and 'normal' in im.filepath.lower() and not Path(bpy.path.abspath(im.filepath)).exists():
                    im.filepath=str(O.parent/'TacticalDevices20260913/HunyuanV3/flashlight/T_flashlight_Normal.png')
                    im.reload();im.colorspace_settings.name='Non-Color'
        return
    for slot in ob.material_slots:
        mat=slot.material;name=mat.name.lower();mat.use_nodes=True
        bs=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
        if bs is None:continue
        if any(k in name for k in ('glass','reticle','lens')):continue
        if 'recess' in name:
            for link in list(bs.inputs['Base Color'].links):mat.node_tree.links.remove(link)
            bs.inputs['Base Color'].default_value=(.005,.005,.005,1);bs.inputs['Metallic'].default_value=.4
            bs.inputs['Roughness'].default_value=.6;continue
        # Opaque housings use the same G18 dark-steel contract; keep source marking
        # texture and normal links, including the suppressor's authored structure.
        if not bs.inputs['Base Color'].is_linked:bs.inputs['Base Color'].default_value=(.017,.020,.024,1)
        bs.inputs['Metallic'].default_value=.85;bs.inputs['Roughness'].default_value=.44

def attachment(kind,grip=None):
    entry=PARTS[kind];file=Path(entry['fbx']).with_name(Path(entry['fbx']).stem+'_Editable.blend')
    ob=source_object(file,'SM_G18_'+kind);finish_materials(ob,kind)
    if grip:
        donor=O.parent/'PistolGripSurface20260927/M1911_GripSurface_Editable.blend'
        with bpy.data.libraries.load(str(donor),link=False) as (src,dst):dst.materials=['M_'+grip]
        mat=dst.materials[0]
        if mat is None:raise RuntimeError('Missing actual grip material '+grip)
        # Runtime samples UV0; the donor normal node names that same channel.
        ob.data.uv_layers[0].name='Physical10cm'
        ob.data.materials.clear();ob.data.materials.append(mat)
        for face in ob.data.polygons:face.material_index=0
    for uv in ob.data.uv_layers:uv.active_render=False
    if ob.data.uv_layers:ob.data.uv_layers.active_index=0;ob.data.uv_layers[0].active_render=True
    return [ob],str(file)

def remove_symbol():
    # A neutral UI removal glyph; no nonexistent gun part is depicted.
    mat,bs=shader('NoTactical_Gray',(.4,.4,.4,1),.0,.55)
    bpy.ops.mesh.primitive_torus_add(major_segments=128,minor_segments=12,location=(0,0,0),rotation=(0,math.pi/2,0),major_radius=.032,minor_radius=.0027)
    ring=bpy.context.object;ring.data.materials.append(mat)
    bpy.ops.mesh.primitive_cube_add(size=1);bar=bpy.context.object;bar.dimensions=(.005,.034,.0054)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);bar.data.materials.append(mat)
    bevel=bar.modifiers.new('Soft UI corners','BEVEL');bevel.width=.0025;bevel.segments=5
    bpy.context.view_layer.objects.active=bar;bpy.ops.object.modifier_apply(modifier=bevel.name)
    return [ring,bar],'Original neutral remove glyph'

def scene(objects,axis,gray):
    s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True
    try:
        pref=bpy.context.preferences.addons['cycles'].preferences;pref.compute_device_type='OPTIX';pref.get_devices()
        for device in pref.devices:device.use=device.type=='OPTIX'
        if any(d.use for d in pref.devices):s.cycles.device='GPU'
    except Exception:pass
    s.render.resolution_x=s.render.resolution_y=1024;s.render.resolution_percentage=100
    s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
    s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=.4 if gray else .7
    palette=apply_grayscale(objects) if gray else []
    if gray:neutral_output(s)
    s.world=bpy.data.worlds.new('NeutralStudio');s.world.use_nodes=True
    bg=s.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.18,.18,.18,1);bg.inputs[1].default_value=.35
    normal=Vector(axis);up=Vector((0,0,1));right=(-normal).cross(up)
    coords=[ob.matrix_world@v.co for ob in objects for v in ob.data.vertices]
    lo=Vector([min(v[i] for v in coords) for i in range(3)]);hi=Vector([max(v[i] for v in coords) for i in range(3)])
    center=(lo+hi)*.5;span=max(max(v.dot(a) for v in coords)-min(v.dot(a) for v in coords) for a in (right,up))
    cam=bpy.data.objects.new('IconCamera',bpy.data.cameras.new('IconCamera'));s.collection.objects.link(cam)
    cam.data.type='ORTHO';cam.data.clip_start=.0001;cam.data.clip_end=10
    cam.location=center+normal*1.5;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=span/.82;s.camera=cam
    factor=span/.1
    for name,offset,power,size in [('Key',(.4,-.1,.42),32,.4),('Fill',(.2,.32,.13),18,.35),('Rim',(-.28,-.12,.3),35,.3)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power*factor*factor;light.shape='DISK';light.size=size*factor
        ob=bpy.data.objects.new(name,light);s.collection.objects.link(ob)
        ob.location=center+(normal*offset[0]+right*offset[1]+up*offset[2])*factor
        ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
    return s,palette

jobs=[('ue_g18','factory','equipment',(1,0,0),False),
      ('ue_g18_optic_false','factory','optic',(1,0,0),True),
      ('ue_g18_trigger_false','factory','trigger',(1,0,0),True),
      ('ue_g18_barrel_false','factory','barrel',(1,0,0),True),
      ('ue_g18_tactical_false','symbol','none',(1,0,0),True)]
for suffix,kind,axis in [('optic_holographic','holographic',(0,1,0)),('optic_panoramic_red_dot','panoramic_red_dot',(0,1,0)),
    ('muzzle_true','suppressor',(-1,0,0)),('muzzle_tactical_suppressor','tactical_suppressor',(-1,0,0)),('muzzle_brake','brake',(-1,0,0)),
    ('magazine_false','factory_magazine',(1,0,0)),('magazine_ext_mag','ext_mag',(1,0,0)),('reargrip_false','GripSurface',(1,0,0)),
    ('tactical_laser','laser',(1,0,0)),('tactical_flashlight','flashlight',(1,0,0))]:
    jobs.append(('ue_g18_'+suffix,'attachment',kind,axis,True))
for variant in ('granular','diamond','quickdot'):jobs.append(('ue_g18_reargrip_pistol_grip_'+variant,'grip','pistol_grip_'+variant,(1,0,0),True))
for key,mode,kind,axis,gray in jobs:
    if '--resume' in sys.argv and key in records:continue
    reset()
    if mode=='factory':objects,source=factory(kind)
    elif mode=='symbol':objects,source=remove_symbol()
    else:objects,source=attachment('GripSurface' if mode=='grip' else kind,kind if mode=='grip' else None)
    s,palette=scene(objects,axis,gray);s.render.filepath=str(I/(key+'.png'))
    # Production sources retain packed maps and the exact camera, shader and crop.
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(SC/(key+'.blend')))
    bpy.ops.render.render(write_still=True)
    records[key]={'source':source,'file':str(I/(key+'.png')),'scene':str(SC/(key+'.blend')),'size':[1024,1024],
        'alpha':'transparent','grayscale':gray,'camera_normal':axis,'up':'+Z','gun_forward':'screen left','materials':palette,'purpose':'Production UI asset'}
    (O/'render_receipt.json').write_text(json.dumps(records,indent=2))
    print('G18_ICON_AUTHORED',key,flush=True)

aliases={'ue_g18_muzzle_false':'ue_g18_barrel_false','ue_g18_trigger_g18_controlled_trigger':'ue_g18_trigger_false',
    'ue_g18_barrel_short':'ue_g18_barrel_false','ue_g18_barrel_long':'ue_g18_barrel_false'}
for category in ('optic','muzzle','magazine','reargrip','trigger','tactical','barrel'):
    aliases['ue_g18_category_'+category]='ue_g18_'+category+'_false'
for target,source in aliases.items():
    shutil.copy2(I/(source+'.png'),I/(target+'.png'))
    records[target]={**records[source],'file':str(I/(target+'.png')),'same_physical_part_as':source}
(O/'render_receipt.json').write_text(json.dumps(records,indent=2))
print('G18_FINAL_PRODUCTION_ICONS_COMPLETE',len(records),flush=True)
