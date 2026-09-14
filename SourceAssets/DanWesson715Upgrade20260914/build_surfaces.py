"""Build local hero geometry and bake per-surface PBR on the existing 715 rig.

The source/reference, editable high meshes and cages are retained. Baking is
asset production; this script does not render previews or run gameplay tests.
"""
import bpy,bmesh,json,math,sys,ast
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;T=O/'Textures';T.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.open_mainfile(filepath=str(O.parent/'DanWesson71520260913/DanWesson715_Manny_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):raise
s=bpy.context.scene;rig=bpy.data.objects['SK_DW715_Manny'];hands=bpy.data.objects['SK_Manny_Arms_Export']
rig.animation_data_clear()
for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
rig.data.pose_position='POSE';bpy.context.view_layer.update()
root=rig.data.bones['WPN_root'].matrix_local.copy();inv=root.inverted();inputs=json.loads((O/'author_inputs.json').read_text())
def collection(name):
    c=bpy.data.collections.new(name);s.collection.children.link(c);return c
refcol=collection('DW715_SOURCE_REFERENCE');hicol=collection('DW715_HIGH');lowcol=collection('DW715_LOW');cagecol=collection('DW715_CAGE')
originals={o.name:o for o in list(s.objects) if o.type=='MESH' and o!=hands}
for ob in originals.values():
    for col in list(ob.users_collection):col.objects.unlink(ob)
    refcol.objects.link(ob);ob.hide_set(True);ob.hide_render=True
def activate(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]
def matset(ob,mat):
    ob.data.materials.clear();ob.data.materials.append(mat)
    for p in ob.data.polygons:p.material_index=0
# Reuse the project-approved M1911 surface construction and baking helpers.
tree=ast.parse((O.parent/'M1911Hero20260913/build.py').read_text(encoding='utf-8'))
helpers={'shader','geometry','bevel','apply_geo','merge','emit'}
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in helpers],type_ignores=[]),'<M1911 surface method>','exec'))
materials={
 'Frame':shader('DW715_SatinStainless',(.23,.255,.28),.245,1,'steel'),
 'Cylinder':shader('DW715_PolishedCylinder',(.255,.278,.30),.21,1,'steel'),
 'Steel':shader('DW715_MachinedDetails',(.19,.21,.23),.25,1,'steel'),
 'Grip':shader('DW715_Rubber',(.013,.017,.021),.61,0),
 'Sights':shader('DW715_SightBlack',(.005,.007,.009),.63,.12),
 'Ammo':shader('DW715_Brass',(.34,.205,.060),.24,1,'steel'),
 'Loader':shader('DW715_LoaderPolymer',(.012,.017,.024),.46,0),
 'Inner':shader('DW715_DarkInterior',(.0025,.003,.004),.82,.15)}
source_base=bpy.data.images.load(str(O.parent/'DanWesson71520260913/Textures/T_DW715_BaseColor.png'),check_existing=True)
source_normal=bpy.data.images.load(str(O.parent/'DanWesson71520260913/Textures/T_DW715_Normal.png'),check_existing=True)
def preserve_source(mat,grip=False):
    m=mat.copy();m.name=mat.name+'_SourceEngraving';n=m.node_tree.nodes;l=m.node_tree.links
    bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');base=n[m['base_node']].outputs[m['base_socket']]
    uv=n.new('ShaderNodeUVMap');uv.uv_map='SourceUV'
    tex=n.new('ShaderNodeTexImage');tex.image=source_base;l.new(uv.outputs[0],tex.inputs['Vector'])
    lum=n.new('ShaderNodeRGBToBW');l.new(tex.outputs['Color'],lum.inputs[0])
    ramp=n.new('ShaderNodeMapRange');l.new(lum.outputs[0],ramp.inputs['Value']);ramp.inputs['From Min'].default_value=.018;ramp.inputs['From Max'].default_value=.20
    ramp.inputs['To Min'].default_value=.11 if not grip else .65;ramp.inputs['To Max'].default_value=1;ramp.clamp=True
    mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.86 if not grip else .45;l.new(base,mix.inputs[1]);l.new(ramp.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],bs.inputs['Base Color'])
    m['base_node']=mix.name;m['base_socket']=mix.outputs[0].name
    normal=n.new('ShaderNodeTexImage');normal.image=source_normal;l.new(uv.outputs[0],normal.inputs['Vector'])
    nm=n.new('ShaderNodeNormalMap');nm.uv_map='SourceUV';nm.inputs['Strength'].default_value=.5 if grip else .72;l.new(normal.outputs[0],nm.inputs['Color'])
    bump=next(x for x in n if x.type=='BUMP');l.new(nm.outputs[0],bump.inputs['Normal'])
    return m
source_mats={k:preserve_source(materials[k],k=='Grip') for k in ('Frame','Grip','Steel','Sights')}
pairs={k:[] for k in ('Frame','Cylinder','Steel','Grip','Sights','Ammo','Loader')};notes=[]
def pair(ob,group,width=.00010,material=None):
    matset(ob,material or materials[group]);hi=ob.copy();hi.data=ob.data.copy();hi.name=ob.name+'_HIGH';hicol.objects.link(hi)
    bevel(ob,width,3);bevel(hi,width,6);pairs[group].append((ob,hi));return ob,hi
def source_part(row,name):
    original=originals[row['object']];ids=row['ids'];iset=set(ids);imap={v:i for i,v in enumerate(ids)}
    polys=[p for p in original.data.polygons if all(v in iset for v in p.vertices)]
    ob=geometry(name,[inv@original.matrix_world@original.data.vertices[i].co for i in ids],[[imap[v] for v in p.vertices] for p in polys],row['bones'][0])
    uv=ob.data.uv_layers.new(name='SourceUV')
    for p,q in zip(ob.data.polygons,polys):
        for a,b in zip(p.loop_indices,q.loop_indices):uv.data[a].uv=original.data.uv_layers.active.data[b].uv
    bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.dissolve_limit(bm,angle_limit=math.radians(.05),verts=list(bm.verts),edges=list(bm.edges),delimit={'UV','MATERIAL','SEAM'})
    bm.to_mesh(ob.data);bm.free();return ob
base_names={355:('RubberGrip','Grip',.00038),817:('Frame','Frame',.00020),16:('FrameLatch','Steel',.00008),21:('RearLatch','Steel',.00008),368:('BarrelShroud','Frame',.00016),12:('FrontBlade','Sights',.00005),68:('RearSight','Sights',.00008)}
for i,row in enumerate(inputs['parts']):
    obj=row['object'];count=len(row['ids'])
    if obj.startswith('DW_Bullet') or obj=='DW715_Speedloader' or obj=='DW_MagazineAssembly' and count in (518,90):continue
    if obj=='DW_BaseModel' and count==72:continue
    if obj=='DW_BaseModel':name,group,width=base_names[count]
    else:name,group,width=obj+str(i),'Steel',.00010
    ob=source_part(row,'DW715_'+name);pair(ob,group,width,source_mats[group])

def tube(name,profile,bone,group,center=(0,.03092),segments=128,inner_start=None):
    x,z=center
    verts=[(x+r*math.cos(2*math.pi*j/segments),y,z+r*math.sin(2*math.pi*j/segments)) for y,r in profile for j in range(segments)]
    faces=[(i*segments+j,i*segments+(j+1)%segments,((i+1)%len(profile))*segments+(j+1)%segments,((i+1)%len(profile))*segments+j) for i in range(len(profile)) for j in range(segments)]
    ob=geometry(name,verts,faces,bone);lo,hi=pair(ob,group,.00005)
    if inner_start is not None:
        for part in (lo,hi):
            part.data.materials.append(materials['Inner'])
            for p in part.data.polygons:
                if p.index//segments>=inner_start:p.material_index=1
    return ob
# Smooth chamber exterior and six cosmetic through-openings for reload views.
segments=144;ys=[-.07023,-.06975,-.066,-.032,-.02712,-.02667];verts=[]
for idx,y in enumerate(ys):
    for j in range(segments):
        theta=2*math.pi*j/segments
        radius=.01853-(.00025 if idx in (0,5) else 0)-(.00115*max(0,math.sin(6*theta))**4 if idx in (2,3) else 0)
        verts.append((radius*math.cos(theta),y,.03092+radius*math.sin(theta)))
faces=[(i*segments+j,i*segments+(j+1)%segments,(i+1)*segments+(j+1)%segments,(i+1)*segments+j) for i in range(len(ys)-1) for j in range(segments)]
faces += [tuple(reversed(range(segments))),tuple((len(ys)-1)*segments+j for j in range(segments))]
cylinder=geometry('DW715_Cylinder_144',verts,faces,'WPN_Cylinder')
bullet_centers=[]
for i in range(6):
    rows=[p for p in inputs['parts'] if p['object']==f'DW_Bullet_{i}'];lo=[min(p['min'][k] for p in rows) for k in range(3)];hi=[max(p['max'][k] for p in rows) for k in range(3)];x=(lo[0]+hi[0])*.5;z=(lo[2]+hi[2])*.5;bullet_centers.append((x,z))
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.00528,depth=.052,location=(x,-.04845,z),rotation=(math.pi/2,0,0));cut=bpy.context.object
    activate([cylinder]);mod=cylinder.modifiers.new('ChamberOpening'+str(i),'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
pair(cylinder,'Cylinder',.00012)
tube('DW715_Muzzle_128',[(-.22479,.00535),(-.22460,.00566),(-.2240,.00566),(-.074,.00566),(-.074,.00435),(-.2228,.00435),(-.22462,.00455)],'WPN_root','Steel',center=(-.00007,.04327),inner_start=4)
tube('DW715_MuzzleInterior',[(-.205,.00438),(-.202,.00438),(-.202,.00002),(-.205,.00002)],'WPN_root','Steel',center=(-.00007,.04327),inner_start=0)
tube('DW715_ExtractorRod',[(-.12076,.00215),(-.1204,.0024),(-.0243,.0024),(-.02421,.0021),(-.02421,.00001),(-.12076,.00001)],'WPN_Extractor','Steel',segments=64)
for i,(x,z) in enumerate(bullet_centers):
    tube(f'DW715_Case_{i}',[(-.0697,.00467),(-.0281,.00467),(-.0281,.00519),(-.02698,.00519),(-.02698,.00002),(-.0280,.00002),(-.0280,.00416),(-.0697,.00416)],f'WPN_Case_{i}','Ammo',center=(x,z),segments=64,inner_start=6)
    tube(f'DW715_Projectile_{i}',[(-.07244,.00002),(-.07185,.00215),(-.0706,.00332),(-.0696,.00335),(-.0696,.00002)],f'WPN_Round_{i}','Ammo',center=(x,z),segments=64)
    tube(f'DW715_Primer_{i}',[(-.0268,.0018),(-.02645,.0018),(-.02645,.00002),(-.0268,.00002)],f'WPN_Case_{i}','Steel',center=(x,z),segments=48)
# A shaped loader with a separate knurled release knob; all belong to its bone.
tube('DW715_LoaderBody',[(-.013,.0158),(-.0124,.0179),(-.002,.0179),(-.0014,.0158),(-.0014,.00002),(-.013,.00002)],'WPN_Loader','Loader',segments=96)
tube('DW715_LoaderKnob',[(-.0014,.0068),(.010,.0068),(.012,.0059),(.012,.00002),(-.0014,.00002)],'WPN_Loader','Steel',segments=64)
for i,(x,z) in enumerate(bullet_centers):
    tube(f'DW715_LoaderSocket_{i}',[(-.0134,.0053),(-.010,.0053),(-.010,.0046),(-.0134,.0046)],'WPN_Loader','Loader',center=(x,z),segments=48)
notes.append('Six-opening 144-segment cylinder, 128-segment muzzle, independent cases/projectiles/primers, shaped loader; existing outer grip and frame retained.')

s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=False;s.render.bake.margin=16
s.render.bake.use_selected_to_active=True;s.render.bake.use_clear=False;s.render.bake.cage_extrusion=.00065;s.render.bake.max_ray_distance=.002
s.render.bake.normal_space='TANGENT';s.render.bake.normal_r='POS_X';s.render.bake.normal_g='POS_Y';s.render.bake.normal_b='POS_Z'
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    if any(d.use for d in prefs.devices):s.cycles.device='GPU'
except Exception:s.cycles.device='CPU'
for ob in s.objects:
    if ob.type=='MESH':ob.hide_render=True
manifest={};stats={}
for group,objects in pairs.items():
    size=4096 if group in ('Frame','Cylinder') else 2048 if group in ('Steel','Grip') else 1024
    for lo,hi in objects:
        apply_geo(lo);uv=lo.data.uv_layers.new(name='HeroUV');lo.data.uv_layers.active=uv;uv.active_render=True
    lows=[p[0] for p in objects];highs=[p[1] for p in objects]
    activate(lows);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(55),island_margin=.006,area_weight=.8,correct_aspect=True,scale_to_bounds=False);bpy.ops.uv.pack_islands(rotate=True,margin=.006);bpy.ops.object.mode_set(mode='OBJECT')
    for hi in highs:hi.hide_set(False)
    bpy.context.view_layer.update();bl=merge(lows,'TEMP_LOW',False);bh=merge(highs,'TEMP_HIGH',True)
    target=bpy.data.materials.new('BAKE_TARGET_'+group);target.use_nodes=True;matset(bl,target)
    for hi in highs:hi.hide_set(True)
    maps={}
    for kind in ('BaseColor','ORM','Normal'):
        im=bpy.data.images.new('T_DW715_Hero_'+group+'_'+('NormalGL' if kind=='Normal' else kind),width=size,height=size,alpha=False,float_buffer=False)
        im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';im.generated_color=(.5,.5,1,1) if kind=='Normal' else (1,.5,0,1) if kind=='ORM' else (0,0,0,1)
        nodes=target.node_tree.nodes;tex=nodes.get('BAKE_TARGET') or nodes.new('ShaderNodeTexImage');tex.name='BAKE_TARGET';tex.image=im;nodes.active=tex
        emit(bh,kind);bl.hide_render=False;bh.hide_render=False;activate([bh,bl]);bpy.ops.object.bake(type='NORMAL' if kind=='Normal' else 'EMIT');bl.hide_render=True;bh.hide_render=True
        im.filepath_raw=str(T/(im.name+'.png'));im.file_format='PNG';im.save();maps[kind]=im;print('DW715_HERO_BAKED',group,kind,flush=True)
    emit(bh,'Normal');bpy.data.objects.remove(bl,do_unlink=True);bpy.data.objects.remove(bh,do_unlink=True)
    mat=bpy.data.materials.new('M_DW715_Hero_'+group);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    for kind,im in maps.items():
        tex=n.new('ShaderNodeTexImage');tex.image=im
        if kind=='BaseColor':l.new(tex.outputs[0],bs.inputs['Base Color'])
        elif kind=='Normal':nm=n.new('ShaderNodeNormalMap');nm.uv_map='HeroUV';l.new(tex.outputs[0],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs['Normal'])
        else:sep=n.new('ShaderNodeSeparateColor');l.new(tex.outputs[0],sep.inputs[0]);l.new(sep.outputs[1],bs.inputs['Roughness']);l.new(sep.outputs[2],bs.inputs['Metallic'])
    for lo,hi in objects:
        matset(lo,mat)
        for uv in list(lo.data.uv_layers):
            if uv.name!='HeroUV':lo.data.uv_layers.remove(uv)
        cage=lo.copy();cage.data=lo.data.copy();cage.name=lo.name+'_CAGE';cagecol.objects.link(cage)
        for v in cage.data.vertices:v.co+=v.normal*.00065
        cage.display_type='WIRE';cage.hide_render=True;cage.hide_set(True)
        lo.data.transform(root);lo.data.update();lo.vertex_groups.clear();lo.vertex_groups.new(name=lo['bone']).add(list(range(len(lo.data.vertices))),1,'REPLACE')
        lo.parent=rig;lo.matrix_parent_inverse=Matrix.Identity(4);lo.matrix_basis=Matrix.Identity(4);lo.modifiers.new('DW715 rigid mechanical skin','ARMATURE').object=rig;lo.hide_set(False);lo.hide_render=False;hi.hide_set(True);hi.hide_render=True
    manifest[group]={'size':size,'material':mat.name,'textures':{k:im.filepath_raw for k,im in maps.items()},'objects':[lo.name for lo,hi in objects]}
    stats[group]={'triangles':sum(len(lo.data.polygons) for lo,hi in objects),'parts':len(objects)}
    (O/'textures.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_Hero_Working.blend'))
author_space=bpy.data.objects.new('DW715_AuthoringBindSpace',None);s.collection.objects.link(author_space);author_space.matrix_world=root
for col in (hicol,cagecol):
    for ob in col.objects:ob.parent=author_space;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
refcol.hide_render=True;hicol.hide_render=True;cagecol.hide_render=True
hands.hide_set(False);hands.hide_render=False
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_Hero_Editable.blend'))
(O/'surfaces.json').write_text(json.dumps({'groups':stats,'notes':notes,'testing':'Not run; user testing pending'},indent=2),encoding='utf-8')
print('DW715_HERO_SURFACES_COMPLETE',flush=True)
