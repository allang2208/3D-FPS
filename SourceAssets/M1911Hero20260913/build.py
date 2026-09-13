"""M1911 local hard-surface refinement, PBR baking and accepted-rig export.

The P9 hand/action tracks, skeleton rest and camera basis are not edited.
No preview renders or gameplay tests are run by this authoring script.
"""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;T=O/'Textures';T.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M1911P9Retarget20260913/M1911_P9_Manny_Editable.blend'))
s=bpy.context.scene;rig=bpy.data.objects['SK_M1911_Manny'];hands=bpy.data.objects['SK_Manny_Arms_Export'];original=bpy.data.objects['M1911_Export']
inputs=json.loads((O/'author_inputs.json').read_text());root=rig.data.bones['WPN_root'].matrix_local.copy();inv=root.inverted()
rig.data.pose_position='REST';bpy.context.view_layer.update()
def collection(name):
    c=bpy.data.collections.new(name);s.collection.children.link(c);return c
refcol=collection('M1911_SOURCE_REFERENCE');hicol=collection('M1911_HIGH');lowcol=collection('M1911_LOW');cagecol=collection('M1911_CAGE')
for c in list(original.users_collection):c.objects.unlink(original)
refcol.objects.link(original);original.name='M1911_Accepted_Bound_Reference';original.hide_render=True;original.hide_set(True)
def activate(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]
def matset(ob,m):
    ob.data.materials.clear();ob.data.materials.append(m)
    for p in ob.data.polygons:p.material_index=0
def shader(name,base,rough,metal,kind='coat'):
    m=bpy.data.materials.new('AUTH_M1911_'+name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
    out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs[0],out.inputs['Surface'])
    co=n.new('ShaderNodeTexCoord');pos=co.outputs['Object']
    def mathn(op,a,b):
        x=n.new('ShaderNodeMath');x.operation=op
        for i,v in enumerate((a,b)):
            if isinstance(v,(int,float)):x.inputs[i].default_value=v
            else:l.new(v,x.inputs[i])
        return x.outputs[0]
    def noise(vector,scale):
        x=n.new('ShaderNodeTexNoise');x.inputs['Scale'].default_value=scale;x.inputs['Detail'].default_value=2;l.new(vector,x.inputs['Vector']);return x.outputs['Fac']
    def stretch(v):
        x=n.new('ShaderNodeVectorMath');x.operation='MULTIPLY';l.new(pos,x.inputs[0]);x.inputs[1].default_value=v;return x.outputs['Vector']
    micro=noise(pos,3500); broad=noise(pos,65)
    tex=micro;depth=.0000025
    if kind=='steel':tex=noise(stretch((12,.12,12)),1200);depth=.000003
    if kind=='wood':tex=noise(stretch((7,9,.32)),95);depth=.000016
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(x*(.52 if kind=='wood' else .94) for x in base),1);ramp.color_ramp.elements[1].color=(*(x*(1.40 if kind=='wood' else 1.05) for x in base),1)
    l.new(tex,ramp.inputs[0]);base_out=ramp.outputs[0]
    rough_out=mathn('ADD',rough,mathn('MULTIPLY',tex,.085 if kind=='wood' else .045))
    height=tex
    if kind=='wood':
        # Diamond checkering is confined to the visible central grip panel;
        # the smooth border and screw surroundings retain their wood grain.
        sep=n.new('ShaderNodeSeparateXYZ');l.new(pos,sep.inputs[0]);y,z=sep.outputs['Y'],sep.outputs['Z']
        diag1=mathn('SINE',mathn('MULTIPLY',mathn('ADD',y,z),2100),0)
        diag2=mathn('SINE',mathn('MULTIPLY',mathn('SUBTRACT',y,z),2100),0)
        grid=mathn('MULTIPLY',mathn('ABSOLUTE',diag1,0),mathn('ABSOLUTE',diag2,0))
        mask=mathn('MULTIPLY',mathn('GREATER_THAN',z,-.080),mathn('LESS_THAN',z,-.020))
        mask=mathn('MULTIPLY',mask,mathn('GREATER_THAN',y,.018));mask=mathn('MULTIPLY',mask,mathn('LESS_THAN',y,.052))
        height=mathn('ADD',mathn('MULTIPLY',tex,.055),mathn('MULTIPLY',grid,mask));depth=.00022
    else:
        geo=n.new('ShaderNodeNewGeometry')
        edge=mathn('MINIMUM',mathn('MULTIPLY',mathn('MAXIMUM',mathn('SUBTRACT',geo.outputs['Pointiness'],.505),0),18),1)
        wear=mathn('MULTIPLY',mathn('MULTIPLY',edge,broad),.12 if kind=='coat' else .045)
        mix=n.new('ShaderNodeMixRGB');l.new(wear,mix.inputs[0]);l.new(base_out,mix.inputs[1]);mix.inputs[2].default_value=(.13,.145,.16,1);base_out=mix.outputs[0]
        rough_out=mathn('SUBTRACT',rough_out,mathn('MULTIPLY',wear,.08))
    l.new(base_out,bs.inputs['Base Color']);l.new(rough_out,bs.inputs['Roughness']);bs.inputs['Metallic'].default_value=metal
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.32 if kind=='wood' else .16;bump.inputs['Distance'].default_value=depth;l.new(height,bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
    orm=n.new('ShaderNodeCombineColor');orm.mode='RGB';orm.inputs[0].default_value=1;l.new(rough_out,orm.inputs[1]);orm.inputs[2].default_value=metal
    m['base_node']=base_out.node.name;m['base_socket']=base_out.name;m['orm_node']=orm.name
    return m
materials={
 'Slide':shader('BluedSlide',(.022,.028,.036),.26,.88),
 'Frame':shader('SatinFrame',(.016,.021,.028),.34,.82),
 'Grip':shader('OiledWalnut',(.092,.032,.010),.34,0,'wood'),
 'Steel':shader('MachinedSteel',(.20,.22,.245),.23,1,'steel'),
 'Magazine':shader('MagazineSteel',(.035,.041,.049),.29,.96,'steel'),
 'Sights':shader('SightExterior',(.008,.010,.013),.54,.45),
 'Ammo':shader('CartridgeBrass',(.33,.19,.055),.25,1,'steel'),
 'Inner':shader('UnlitCavityFinish',(.003,.004,.005),.84,.12)}
pairs={k:[] for k in ['Slide','Frame','Grip','Steel','Magazine','Sights','Ammo']};notes=[]
def geometry(name,verts,faces,bone):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    for f in bm.faces:f.smooth=True
    for e in bm.edges:e.smooth=not(e.is_manifold and e.calc_face_angle(0)>math.radians(42))
    bm.to_mesh(me);bm.free();ob=bpy.data.objects.new(name,me);lowcol.objects.link(ob);ob['bone']=bone;return ob
def source_part(i,name,bone=None):
    part=inputs['parts'][i];ids=part['ids'];imap={v:j for j,v in enumerate(ids)};idsset=set(ids)
    ps=[p for p in original.data.polygons if p.vertices[0] in idsset]
    ob=geometry(name,[inv@original.data.vertices[j].co for j in ids],[[imap[v] for v in p.vertices] for p in ps],bone or part['bones'][0])
    if original.data.uv_layers:
        uv=ob.data.uv_layers.new(name='SourceUV')
        for p,q in zip(ob.data.polygons,ps):
            for a,b in zip(p.loop_indices,q.loop_indices):uv.data[a].uv=original.data.uv_layers.active.data[b].uv
    return ob
def bevel(ob,width,segments):
    if width:
        m=ob.modifiers.new('Editable edge radius','BEVEL');m.limit_method='ANGLE';m.angle_limit=math.radians(35);m.width=width;m.segments=segments;m.use_clamp_overlap=True;m.harden_normals=True
    m=ob.modifiers.new('Planar weighted normals','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=40
def pair(ob,group,width=.00012,material=None):
    matset(ob,material or materials[group]);hi=ob.copy();hi.data=ob.data.copy();hi.name=ob.name+'_HIGH';hicol.objects.link(hi)
    bevel(ob,width,2);bevel(hi,width,6);pairs[group].append((ob,hi));return ob,hi
names={0:'Frame',1:'Slide',2:'MagazineShell',4:'LeftWoodPanel',5:'RightWoodPanel',6:'Hammer',8:'LanyardLoop',10:'GripSafety',11:'MuzzleBushing',12:'MagRelease',13:'SlideStop',14:'Trigger',15:'ThumbSafety',16:'RearSight',22:'RecoilPlug',28:'MagazineFloorplate',29:'MainspringHousing',33:'MagazineFollower',36:'FrontSight'}
for i,part in enumerate(inputs['parts']):
    if i in [3,17,18,19,20]:continue
    group='Grip' if i in [4,5] else 'Slide' if i==1 else 'Magazine' if i in [2,28,33] else 'Sights' if i in [16,36] else 'Ammo' if i in [7,9] else 'Steel' if i in [6,8,11,12,13,14,15,21,22,23,24,25,26,27,30,31,32,34,35,37,38] else 'Frame'
    bone='WPN_Hammer' if i==6 else 'WPN_Slide' if i in [11,22] else None
    ob=source_part(i,'M1911_'+names.get(i,'Detail'+str(i)),bone)
    if i in [0,1]:
        bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.dissolve_limit(bm,angle_limit=math.radians(.08),verts=list(bm.verts),edges=list(bm.edges),delimit={'UV','MATERIAL','SEAM'});bm.to_mesh(ob.data);bm.free()
    if i==1:
        # Close visible open boundaries with inward-facing wall thickness.
        bm=bmesh.new();bm.from_mesh(ob.data);open_edges=sum(e.is_boundary for e in bm.edges);bm.free()
        if open_edges:
            sol=ob.modifiers.new('Slide opening wall thickness','SOLIDIFY');sol.thickness=.00055;sol.offset=-1;sol.use_even_offset=True;sol.use_quality_normals=True
            activate([ob]);bpy.ops.object.modifier_apply(modifier=sol.name)
        notes.append({'slide_original_open_edges':open_edges})
    pair(ob,group,.00024 if i in [4,5] else .00016 if i in [0,1] else .00008)
def tube(name,profile,bone,group,center_z=.02898,segments=96,inner_start=None):
    # Closed wall profile in axial/radial space. Internal end surfaces are
    # cosmetic occluders, not a functional barrel/chamber construction.
    verts=[(r*math.cos(2*math.pi*j/segments),y,center_z+r*math.sin(2*math.pi*j/segments)) for y,r in profile for j in range(segments)]
    faces=[]
    for i in range(len(profile)):
        for j in range(segments):faces.append((i*segments+j,i*segments+(j+1)%segments,((i+1)%len(profile))*segments+(j+1)%segments,((i+1)%len(profile))*segments+j))
    ob=geometry(name,verts,faces,bone);lo,hi=pair(ob,group,.00006)
    if inner_start is not None:
        for obj in [lo,hi]:
            obj.data.materials.append(materials['Inner'])
            for p in obj.data.polygons:
                if p.index//segments>=inner_start:p.material_index=1
    return lo
# Follow the existing external envelope and retain all existing mechanical pivots.
barrel=tube('M1911_Barrel_Rebuilt',[(-.15588,.00825),(-.15545,.00850),(-.034,.00850),(-.029,.01045),(.00247,.01045),(.00247,.0057),(-.139,.0057),(-.15565,.0057)],'WPN_Barrel','Steel',inner_start=5)
def box(name,lo,hi,bone,group,width=.00012):
    verts=[(x,y,z) for z in [lo[2],hi[2]] for y in [lo[1],hi[1]] for x in [lo[0],hi[0]]]
    faces=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
    ob=geometry(name,verts,faces,bone);return pair(ob,group,width)[0]
box('M1911_ChamberHood',(-.0091,-.027,.0278),(.0091,.0023,.0401),'WPN_Barrel','Steel',.00028)
# A dark shallow muzzle insert avoids a visibly open shell when the slide moves.
tube('M1911_Bore_ShadowInsert',[(-.1389,.00572),(-.1378,.00572),(-.1378,.0001),(-.1389,.0001)],'WPN_Barrel','Steel',inner_start=0)
box('M1911_ChamberRearShadow',(-.0059,.0024,.0206),(.0059,.0029,.0349),'WPN_Barrel','Steel',.0001)
matset(pairs['Steel'][-1][0],materials['Inner']);matset(pairs['Steel'][-1][1],materials['Inner'])
# Cosmetic guide surface fills the exposed lower opening, independent of the barrel.
tube('M1911_ExposedGuideSurface',[(-.145,.0030),(-.142,.0033),(-.071,.0033),(-.071,.0001),(-.145,.0001)],'WPN_root','Steel',center_z=.0105,segments=64)
for i in [17,18,19,20]:
    part=inputs['parts'][i];lo,hi=Vector(part['min']),Vector(part['max']);c=(lo+hi)*.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=max(hi.y-lo.y,hi.z-lo.z)*.5,depth=hi.x-lo.x,location=c,rotation=(0,math.pi/2,0))
    ob=bpy.context.object;ob.name='M1911_GripScrew_'+str(i)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    for col in list(ob.users_collection):col.objects.unlink(ob)
    lowcol.objects.link(ob);ob['bone']='WPN_root'
    face_x=hi.x if c.x>0 else lo.x
    bpy.ops.mesh.primitive_cube_add(size=1,location=(face_x,c.y,c.z));cut=bpy.context.object;cut.scale=(.0009,.0078,.00065);activate([cut]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    activate([ob]);mod=ob.modifiers.new('Recessed screw slot','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
    pair(ob,'Steel',.000065)

def apply_geo(ob):
    activate([ob])
    for m in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=m.name)
    tri=ob.modifiers.new('Baked export triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
def merge(obs,name,evaluated):
    copies=[];dg=bpy.context.evaluated_depsgraph_get()
    for ob in obs:
        me=bpy.data.meshes.new_from_object(ob.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg) if evaluated else ob.data.copy()
        x=bpy.data.objects.new(name+'_part',me);s.collection.objects.link(x);copies.append(x)
    activate(copies);bpy.ops.object.join();ob=bpy.context.object;ob.name=name;return ob
def emit(high,kind):
    for m in high.data.materials:
        n=m.node_tree.nodes;l=m.node_tree.links;out=next(x for x in n if x.type=='OUTPUT_MATERIAL')
        if kind=='Normal':l.new(next(x for x in n if x.type=='BSDF_PRINCIPLED').outputs[0],out.inputs['Surface'])
        else:
            em=n.get('BAKE_EMIT') or n.new('ShaderNodeEmission');em.name='BAKE_EMIT'
            src=n[m['base_node']].outputs[m['base_socket']] if kind=='BaseColor' else n[m['orm_node']].outputs[0]
            l.new(src,em.inputs[0]);l.new(em.outputs[0],out.inputs['Surface'])
s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=False;s.render.bake.margin=16
s.render.bake.use_selected_to_active=True;s.render.bake.use_clear=False;s.render.bake.cage_extrusion=.00065;s.render.bake.max_ray_distance=.002
s.render.bake.normal_space='TANGENT';s.render.bake.normal_r='POS_X';s.render.bake.normal_g='POS_Y';s.render.bake.normal_b='POS_Z'
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for d in prefs.devices:d.use=d.type=='OPTIX'
    if any(d.use for d in prefs.devices):s.cycles.device='GPU'
except Exception:s.cycles.device='CPU'
for ob in s.objects:
    if ob.type=='MESH':ob.hide_render=True
manifest={};runtime=[];stats={}
for group,objects in pairs.items():
    size=4096 if group in ['Slide','Frame'] else 1024 if group in ['Sights','Ammo'] else 2048
    for lo,hi in objects:
        apply_geo(lo)
        layer=lo.data.uv_layers.new(name='HeroUV');lo.data.uv_layers.active=layer;layer.active_render=True
    lows=[p[0] for p in objects];highs=[p[1] for p in objects]
    activate(lows);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(55),island_margin=.006,area_weight=.8,correct_aspect=True,scale_to_bounds=False);bpy.ops.uv.pack_islands(rotate=True,margin=.006);bpy.ops.object.mode_set(mode='OBJECT')
    for hi in highs:hi.hide_set(False)
    bpy.context.view_layer.update();bl=merge(lows,'TEMP_LOW',False);bh=merge(highs,'TEMP_HIGH',True)
    target=bpy.data.materials.new('BAKE_TARGET_'+group);target.use_nodes=True;matset(bl,target)
    for hi in highs:hi.hide_set(True)
    maps={}
    for kind in ['BaseColor','ORM','Normal']:
        im=bpy.data.images.new('T_M1911_Hero_'+group+'_'+('NormalGL' if kind=='Normal' else kind),width=size,height=size,alpha=False,float_buffer=False)
        im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';im.generated_color=(.5,.5,1,1) if kind=='Normal' else (1,.5,0,1) if kind=='ORM' else (0,0,0,1)
        n=target.node_tree.nodes;tex=n.get('BAKE_TARGET') or n.new('ShaderNodeTexImage');tex.name='BAKE_TARGET';tex.image=im;n.active=tex
        emit(bh,kind);bl.hide_render=False;bh.hide_render=False;activate([bh,bl]);bpy.ops.object.bake(type='NORMAL' if kind=='Normal' else 'EMIT');bl.hide_render=True;bh.hide_render=True
        im.filepath_raw=str(T/(im.name+'.png'));im.file_format='PNG';im.save();maps[kind]=im
        print('M1911_HERO_BAKED',group,kind,flush=True)
    emit(bh,'Normal');bpy.data.objects.remove(bl,do_unlink=True);bpy.data.objects.remove(bh,do_unlink=True)
    mat=bpy.data.materials.new('M_M1911_Hero_'+group);mat.use_nodes=True;n=mat.node_tree.nodes;l=mat.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
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
        # Carry the author mesh into the unchanged accepted inverse-bind space.
        lo.data.transform(root);lo.data.update();lo.vertex_groups.clear();lo.vertex_groups.new(name=lo['bone']).add(list(range(len(lo.data.vertices))),1,'REPLACE')
        lo.parent=rig;lo.matrix_parent_inverse=Matrix.Identity(4);lo.matrix_basis=Matrix.Identity(4);lo.modifiers.new('Accepted M1911 rig','ARMATURE').object=rig
        lo.hide_set(False);lo.hide_render=False;runtime.append(lo);hi.hide_set(True);hi.hide_render=True
    manifest[group]={'size':size,'material':mat.name,'textures':{k:im.filepath_raw for k,im in maps.items()},'objects':[lo.name for lo,hi in objects]}
    stats[group]={'triangles':sum(len(lo.data.polygons) for lo,hi in objects),'parts':len(objects)}
    (O/'textures.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    # Save work after each atlas so a later authoring interruption is recoverable.
    bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_Hero_Working.blend'))

sys.path.insert(0,str(O))
from export_assets import export_assets
export_assets(O)
refcol.hide_render=True;hicol.hide_render=True;cagecol.hide_render=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_Hero_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'groups':stats,'notes':notes,'reassigned':{'Hammer':'WPN_Hammer','MuzzleBushing':'WPN_Slide','RecoilPlug':'WPN_Slide'},'preserved':'Accepted P9 clips, Manny skin and skeleton rest, weapon transforms and event timings','state':'Authored, baked and exported; no rendered or gameplay test'},indent=2),encoding='utf-8')
print('M1911_HERO_AUTHORING_COMPLETE',flush=True)
