"""Author interchangeable hilt variants from the Vibe3D-cut factory interfaces.

Only production FBX, editable source and menu icons are made. No review renders.
"""
import bpy,bmesh,math,json,shutil
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from pathlib import Path
P=Path(__file__).parent;OUT=P/'Export';ICONS=P/'Icons';ICONS.mkdir(exist_ok=True)
ROOT=P.parents[1]
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True)
source=P.parent/'RuneSword20260913/CompactNaturalV4/AzureRunesword_Manny_Editable.blend'
with bpy.data.libraries.load(str(source),link=False) as (src,dst):dst.materials=['M_AzureRunesword']
stock=dst.materials[0]
rows=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts']
factory={};objects={};interfaces={}
for row in rows:
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(OUT/(row['mesh']+'.fbx')))
    obj=next(o for o in set(bpy.data.objects)-before if o.type=='MESH')
    obj.data.transform(obj.matrix_world);obj.matrix_world=Matrix.Identity(4)
    obj.name=row['mesh'];obj.data.materials.clear();obj.data.materials.append(stock)
    factory[row['slot']]=obj;objects[(row['slot'],'factory')]=obj
    # Actual face-corner data at the three mounting cuts, retained with the source.
    cuts={'blade_1':[.125],'guard':[.125,-.04],'grip':[0.,-.155],'pommel':[0.]}[row['slot']]
    rings=[]
    for z in cuts:
        ring=[]
        for poly in obj.data.polygons:
            for li in poly.loop_indices:
                co=obj.data.vertices[obj.data.loops[li].vertex_index].co
                if abs(co.z-z)<.000004:
                    ring.append({'position_m':list(co),'uv':list(obj.data.uv_layers[0].data[li].uv),'normal':list(obj.data.corner_normals[li].vector)})
        rings.append({'z_m':z,'corners':ring})
    interfaces[row['slot']]={'location_cm':row['location_cm'],'mounting_rims':rings}

def smooth(x):x=max(0.,min(1.,x));return x*x*(3-2*x)
def create_material(name,color,metal,rough,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
    return m
silver=create_material('M_RuneModuleSilver',(.36,.43,.50),.88,.29)
glow=create_material('M_RuneModuleGlow',(.11,.48,.80),0,.3,3.0)
crystal=create_material('M_RuneModuleCrystal',(.055,.30,.64),0,.12,.5)
crystal.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value=.65

def deform(slot,option,fn):
    base=factory[slot];obj=base.copy();obj.data=base.data.copy();obj.name=base.name.replace('factory',option);bpy.context.scene.collection.objects.link(obj)
    normals=[n.vector.copy() for n in obj.data.corner_normals]
    old=[v.co.copy() for v in obj.data.vertices];inverses=[];eps=1e-5
    for p in old:
        J=Matrix([(fn(p+Vector(tuple(eps if i==j else 0 for i in range(3))))-fn(p-Vector(tuple(eps if i==j else 0 for i in range(3)))))/(2*eps) for j in range(3)]).transposed()
        inverses.append(J.inverted_safe().transposed())
    for v,p in zip(obj.data.vertices,old):v.co=fn(p)
    for f in obj.data.polygons:f.use_smooth=True
    obj.data.update();obj.data.normals_split_custom_set([(inverses[l.vertex_index]@normals[l.index]).normalized() for l in obj.data.loops])
    objects[(slot,option)]=obj
    return obj

for option in ['bastion_guard','riposte_guard','light_guard']:
    def shape(p,option=option):
        w=smooth((abs(p.x)-.072)/.06);q=p.copy()
        if option=='bastion_guard':q.x*=1+.08*w;q.y*=1+.16*w;q.z-=.018*w
        elif option=='riposte_guard':q.z+=.055*w;q.x*=1-.12*w
        else:q.x*=1-.24*w;q.y*=1-.32*w;q.z=.032+(q.z-.032)*(1-.24*w)
        return q
    deform('guard',option,shape)
for option in ['shock_wrap','swift_grip','long_twohand']:
    def shape(p,option=option):
        w=smooth((-p.z-.016)/.014)*smooth((p.z+.139)/.014);q=p.copy()
        if option=='long_twohand':q.z-=.028*smooth((-p.z-.022)/.11)
        else:
            a=math.atan2(p.y,p.x);phase=(p.z/.010+a/(math.tau)) if option=='shock_wrap' else a*8/math.tau
            amount=(-.0005 if option=='shock_wrap' else -.00035)*w*(.5+.5*math.cos(math.tau*phase))**6
            r=max(.001,math.hypot(p.x,p.y));q.x*=1+amount/r;q.y*=1+amount/r
        return q
    deform('grip',option,shape)
# Pommel upgrades now use the six shared designs; retain the factory mounting source.

# Export each selected module at its own mounting origin, with source UVs and normals.
newrows=[]
for (slot,option),obj in objects.items():
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    if option!='factory':
        bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
        newrows.append({'slot':slot,'id':option,'mesh':obj.name,'location_cm':next(r['location_cm'] for r in rows if r['slot']==slot)})
    obj.hide_set(option!='factory');obj.hide_render=option!='factory'
    if option=='factory':obj.location=Vector(next(r['location_cm'] for r in rows if r['slot']==slot))*.01
for row in rows:
    datum=bpy.data.objects.new('Mount_'+row['slot'],None);bpy.context.scene.collection.objects.link(datum);datum.location=Vector(row['location_cm'])*.01;datum.empty_display_type='ARROWS';datum.empty_display_size=.025
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'RuneSword_Modular_Editable.blend'))
(P/'interfaces.json').write_text(json.dumps({'interface':'azure_hilt_v1','units':'metres; blade +Z, width X, thickness Y','parts':interfaces},indent=2),encoding='utf-8')
(P/'variant_exports.json').write_text(json.dumps(newrows,indent=2),encoding='utf-8')

# Actual-model thumbnail production is part of the workbench asset delivery.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='AgX'
scene.world=bpy.data.worlds.new('Rune modules UI studio');scene.world.use_nodes=True
scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.16,.16,.16,1)
scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.45
camera=bpy.data.objects.new('Module icon camera',bpy.data.cameras.new('Module icon camera'));scene.collection.objects.link(camera);scene.camera=camera;camera.data.type='ORTHO';camera.data.clip_start=.001
lights=[]
for name,loc,power in [('Key',(-.3,-.6,.5),65),('Fill',(.4,-.2,.1),20),('Rim',(.1,.3,.4),40)]:
    o=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(o);o.data.energy=power;o.data.size=.4;lights.append((o,Vector(loc)))
for (slot,option),obj in objects.items():
    for o in objects.values():o.hide_render=o!=obj
    obj.hide_set(False);obj.location=Vector();center=sum((Vector(v) for v in obj.bound_box),Vector())/8
    size=Vector([max(v[i] for v in obj.bound_box)-min(v[i] for v in obj.bound_box) for i in range(3)])
    camera.location=center+Vector((.025,-1.,.025));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=max(size.x,size.z)/.83
    for light,offset in lights:light.location=center+offset;light.rotation_euler=(center-light.location).to_track_quat('-Z','Y').to_euler()
    target=ICONS/('ue_rune_sword_'+slot+'_'+('false' if option=='factory' else option)+'.png')
    scene.render.filepath=str(target);bpy.ops.render.render(write_still=True)
    shutil.copy2(target,ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/target.name)
    print('MENU_ICON_WRITTEN '+target.name,flush=True)
# Numeric blade treatments share the physical factory blade.
for option in ['extended_edge','heavy_spine','feather_edge']:
    name='ue_rune_sword_blade_1_'+option+'.png';shutil.copy2(ICONS/'ue_rune_sword_blade_1_false.png',ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/name)
for slot in factory:
    shutil.copy2(ICONS/('ue_rune_sword_'+slot+'_false.png'),ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/('ue_rune_sword_category_'+slot+'.png'))
for name in ['ue_rune_sword_blade_2_false.png','ue_rune_sword_category_blade_2.png']:
    shutil.copy2(ICONS/'ue_rune_sword_blade_1_false.png',ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/name)
print('RUNE_SWORD_VARIANTS_AND_MENU_ASSETS_AUTHORED',flush=True)
