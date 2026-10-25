"""Approved ancient seal seat, with separate native steel/rune mounting ends."""
import bpy,bmesh,types,math,json,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2];RUNE=ROOT/'SourceAssets/RuneboundWarhammer20261022'
code=(RUNE/'FinalTollHammerHeadV2/author_model.py').read_text('utf-8')
m=types.ModuleType('ancient_seal_tools');m.__file__=str(P/'author_model.py')
exec(compile(code,'<solid_surface_tools>','exec'),m.__dict__)
m.P=RUNE/'StarTideCoreV1';m.initialize();m.P=P
bpy.context.preferences.filepaths.save_version=0
sys.path.insert(0,str(RUNE/'HeadRunePBRV3'))
from surface_authoring import refine_metal
bronze=m.procedural_metal('AUTHOR_AncientSeal_Bronze',(.115,.070,.032),(.30,.20,.095),.38,.000035)
iron=m.procedural_metal('AUTHOR_AncientSeal_Iron',(.026,.032,.038),(.075,.085,.095),.43,.000045)
silver=m.procedural_metal('AUTHOR_AncientSeal_Silver',(.28,.29,.30),(.48,.49,.50),.29,.000012)
for mat in (bronze,iron,silver):refine_metal(mat)
red=m.simple_material('M_AncientSeal_Inlay',(.075,.007,.004),.22,.27)
p=red.node_tree.nodes.get('Principled BSDF');p.inputs['Coat Weight'].default_value=.3
factory_file=ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend'
with bpy.data.libraries.load(str(factory_file),link=False) as (a,b):b.objects=['SM_Warhammer_head_mount_factory']
steel_factory=b.objects[0];m.HOST.objects.link(steel_factory);steel_factory.hide_render=True

def clip(poly,axis,limit,positive):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0][axis]-limit)*(1 if positive else -1);db=(b[0][axis]-limit)*(1 if positive else -1)
        if da>=0:result.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);result.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return result

def retain_interfaces(factory,left,right,bottom):
    original=factory.data;original.calc_loop_triangles();normals=[n.vector.copy() for n in original.corner_normals]
    verts=[];faces=[];corners=[]
    # Retain real side contact cheeks and lower joining collar; interpolated UV
    # and split normals remain intact at the author cuts.
    planes=[(0,left+.0027,True),(0,right-.0027,False),(2,bottom+.008,True)]
    for tri in original.loop_triangles:
        remaining=[(original.vertices[original.loops[i].vertex_index].co.copy(),original.uv_layers[0].data[i].uv.copy(),normals[i]) for i in tri.loops]
        pieces=[]
        for axis,limit,inside in planes:
            outside=clip(remaining,axis,limit,not inside)
            if outside:pieces.append(outside)
            remaining=clip(remaining,axis,limit,inside)
            if not remaining:break
        for poly in pieces:
            for i in range(1,len(poly)-1):
                triangle=(poly[0],poly[i],poly[i+1])
                if (triangle[1][0]-triangle[0][0]).cross(triangle[2][0]-triangle[0][0]).length<1e-12:continue
                faces.append(tuple(range(len(verts),len(verts)+3)))
                for item in triangle:verts.append(item[0]);corners.append(item)
    mesh=bpy.data.meshes.new('Retained native mounting surfaces');mesh.from_pydata(verts,[],faces);mesh.update();mesh.materials.append(bronze)
    uv=mesh.uv_layers.new(name='UVMap');stored=mesh.attributes.new('PreservedNormal',type='FLOAT_VECTOR',domain='CORNER')
    for poly in mesh.polygons:
        poly.use_smooth=True
        for index in poly.loop_indices:
            co,tex,n=corners[mesh.loops[index].vertex_index];uv.data[index].uv=tex;stored.data[index].vector=n.normalized()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    new=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)['faces'];bm.normal_update()
    uv=bm.loops.layers.uv['UVMap'];nlayer=bm.loops.layers.float_vector['PreservedNormal']
    for face in new:
        face.smooth=False
        axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(face.normal[i]))]
        for loop in face.loops:loop[uv].uv=(loop.vert.co[axes[0]]/.12,loop.vert.co[axes[1]]/.12);loop[nlayer]=face.normal
    bmesh.ops.triangulate(bm,faces=new);bm.to_mesh(mesh);bm.free();mesh.update()
    mesh.normals_split_custom_set([tuple(n.vector) for n in mesh.attributes['PreservedNormal'].data])
    obj=bpy.data.objects.new('Preserved_original_interface',mesh);m.BUILD.objects.link(obj);m.PARTS.append(obj)
    return obj

def octagon(w,h,c=.22):return [(-w*(1-c),-h),(w*(1-c),-h),(w,-h*(1-c)),(w,h*(1-c)),(w*(1-c),h),(-w*(1-c),h),(-w,h*(1-c)),(-w,-h*(1-c))]

def frame_ring(name,f,w,h,band,d0,d1,mat):
    outer=octagon(w,h);inner=octagon(w-band,h-band)
    verts=[m.pt(f,x,y,d) for d,shape in ((d0,outer),(d1,outer),(d1,inner),(d0,inner)) for x,y in shape];faces=[]
    for layer in range(4):
        for i in range(8):faces.append((layer*8+i,layer*8+(i+1)%8,((layer+1)%4)*8+(i+1)%8,((layer+1)%4)*8+i))
    return m.solid(name,verts,faces,mat,.00022,4)

def outline_stroke(points,width):
    pts=[Vector(p) for p in points];a=[];b=[]
    for i,p in enumerate(pts):
        d=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]).normalized();n=Vector((-d.y,d.x))*width
        a.append(tuple(p+n));b.append(tuple(p-n))
    return a+list(reversed(b))

SIGILS=[ [(-.013,-.017),(-.010,-.007),(-.006,-.005),(0,.009),(.006,-.005),(.010,-.007),(.013,-.017)],
         [(-.009,-.002),(-.007,.007),(-.004,.010),(0,.023),(.004,.010),(.007,.007),(.009,-.002)],
         [(-.005,-.024),(0,-.011),(.005,-.024)] ]

def engraved_seal(plate,f,scale,top):
    cutters=[]
    for i,path in enumerate(SIGILS):
        points=[(x*scale,y*scale) for x,y in path]
        m.strip('Carved_ancient_sigil_cutter',f,outline_stroke(points,.0009*scale),top-.00085,top+.0004,iron,0,cutters)
        m.strip('Cinnabar_set_into_seal',f,outline_stroke(points,.00060*scale),top-.00078,top-.00056,red,.00008,m.ENERGY)
    cut=m.join_group(cutters,'Joined solid seal cutters');m.activate(plate)
    mod=plate.modifiers.new('True carved broken-mountain seal','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;mod.use_self=True
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)

def meander(f,x,y,s,cutters,flip=1):
    path=[(0,0),(1,0),(1,1),(.2,1),(.2,.3),(.7,.3),(.7,.7),(.45,.7)]
    points=[m.pt(f,x+flip*a*s,y+b*s,.00230) for a,b in path]
    m.stroke('Cut_silver_meander_channel',points,.00032,iron,8,cutters)
    m.stroke('Worn_silver_meander_inlay',[p-f[3]*.00028 for p in points],.00015,silver,8)

def build_variant(label,factory,left,right,bottom,top,mid):
    m.PARTS=[];m.ENERGY=[];cx=(left+right)*.5;half=(right-left)*.5-.0015
    native=retain_interfaces(factory,left,right,bottom)
    body_bottom=bottom+.011;body_top=top;depth=.0335 if label=='Steel' else .0305
    sections=[(body_bottom,half*.73,depth*.86),(body_bottom+.012,half*.88,depth),(body_bottom+.024,half,depth*1.06),
              (body_top-.021,half,depth*1.06),(body_top-.008,half*.84,depth),(body_top,half*.64,depth*.9)]
    verts=[]
    for z,w,d in sections:verts.extend((cx+x,y,z) for x,y in octagon(w,d,.23))
    faces=[tuple(reversed(range(8))),tuple((len(sections)-1)*8+i for i in range(8))]
    for j in range(len(sections)-1):
        for i in range(8):faces.append((j*8+i,j*8+(i+1)%8,(j+1)*8+(i+1)%8,(j+1)*8+i))
    m.solid('Continuous_forged_iron_core',verts,faces,iron,.0008,5)
    h=(body_top-body_bottom)*.44;cz=(body_top+body_bottom)*.5
    for sign in (-1,1):
        f=m.frame((cx,sign*depth*1.04,cz),(0,sign,0),(-sign,0,0))
        armour=m.strip('Solid_bronze_armour_cheek',f,octagon(half*.98,h),-.0006,.0022,bronze,.0009)
        frame_ring('Dressed_bronze_outer_frame',f,half*.94,h*.96,.0015,.0018,.0040,bronze)
        frame_ring('Fine_silver_outer_inset',f,half*.89,h*.92,.00032,.0039,.0042,silver)
        # Broad antique seal face sits below its continuous protective rim.
        pw=half*.58;ph=h*.72
        m.strip('Recessed_seal_cartouche_back',f,octagon(pw+.002,ph+.002),.0022,.0042,iron,.0003)
        plate=m.strip('Bronze_contact_seal_face',f,octagon(pw,ph),.0038,.0055,bronze,.0004)
        frame_ring('Raised_seal_frame',f,pw+.0015,ph+.0015,.0010,.0041,.0060,bronze)
        frame_ring('Silver_cartouche_hairline',f,pw+.0002,ph+.0002,.00025,.00555,.00585,silver)
        engraved_seal(plate,f,min(pw/.017,ph/.029),.0055)
        cutters=[]
        for side in (-1,1):
            for j in range(4):meander(f,side*half*.69,-h*.63+j*h*.34,.0042,cutters,side)
            for z in (-h*.79,h*.79):
                m.disk('Recessed_captive_pin',m.frame(m.pt(f,side*half*.73,z,.0020),f[3],f[1]),.00155,-.0005,.0015,bronze,32)
                m.disk('Silver_pin_center',m.frame(m.pt(f,side*half*.73,z,.0035),f[3],f[1]),.0006,0,.00015,silver,24)
        cut=m.join_group(cutters,'Joined real meander recesses');m.activate(armour)
        mod=armour.modifiers.new('Silver wires seated in cut channels','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.use_self=True;mod.object=cut
        bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
        # Distinct lateral antique copper plates keep the rail/body junction solid.
        for side in (-1,1):
            path=[m.pt(f,side*half*.84,-h*.65,.0026),m.pt(f,side*half*.98,-h*.40,.0026),m.pt(f,side*half*.98,h*.48,.0026),m.pt(f,side*half*.76,h*.85,.0026)]
            m.stroke('Continuous_bronze_corner_binding',path,.0008,bronze,10)
    # Top cap and lower collar are solid, shallow layers with restrained chasing.
    m.disk('Continuous_bronze_socket_sleeve',m.frame((cx,0,bottom+.0135),(0,0,1),(1,0,0)),half*.78,-.0065,.0065,bronze,96)
    for z,r,height in [(body_top+.001,half*.68,.0035),(bottom+.008,half*.78,.003),(bottom+.019,half*.77,.0022)]:
        m.disk('Antique_seat_cap_band',m.frame((cx,0,z),(0,0,1),(1,0,0)),r,-height/2,height/2,bronze,96)
        m.annulus('Fine_silver_band_edge',m.frame((cx,0,z+height/2),(0,0,1),(1,0,0)),r-.0007,r,.00005,.00035,silver,96)
    for i in range(16):
        a=math.tau*i/16;r=half*.78
        pts=[]
        for j in range(32):
            t=j/31;angle=a+.25*t
            pts.append((cx+(r+.0002)*math.cos(angle),(r+.0002)*math.sin(angle),bottom+.012+.0017*math.sin(t*math.tau)))
        m.stroke('Collar_cloud_chasing',pts,.00021,bronze,6)
    # Keep construction editable before UV packing and per-host 4K PBR baking.
    for obj in m.PARTS+m.ENERGY:obj['host_variant']=label
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/('AncientSeal_'+label+'_Construction.blend')))
    metal=m.join_group(m.PARTS,'AncientSeal_'+label+'_PBR');m.unwrap(metal)
    start=code.index('def bake_maps(');end=code.index('\ndef finalize(',start)
    bake=code[start:end].replace('T_FinalToll_','T_AncientSeal_'+label+'_').replace('M_FinalToll_PBR_Surface','M_AncientSeal_'+label+'_Surface')
    exec(compile(bake,'<host_specific_4k_bake>','exec'),m.__dict__);m.bake_maps(metal)
    inlay=m.join_group(m.ENERGY,'AncientSeal_'+label+'_Inlay');m.unwrap(inlay)
    out=m.join_group([metal,inlay],'SM_'+label+'Warhammer_AncientSeal_V1');out.location=(0,0,0)
    out['native_cut_planes']=[left,right,bottom];out['display_name']='破势古印座'
    m.activate(out);fbx=P/'Export'/(out.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='COPY',embed_textures=False)
    out.data.calc_loop_triangles()
    return out,{'variant':label,'mesh':out.name,'fbx':str(fbx),'triangles':len(out.data.loop_triangles),'materials':[v.name for v in out.data.materials],'location_cm':[0,0,0],'native_cut_planes_m':[left,right,bottom],'center_cm':[cx*100,0,cz*100]}

rows=[];models=[]
for args in [('Steel',steel_factory,-.04,.04,.865,.985,.929),('Runebound',bpy.data.objects['SM_RuneboundWarhammer_head_mount_factory'],-.0354452141,.0345547859,.842,.980,.916)]:
    obj,row=build_variant(*args);models.append(obj);rows.append(row);obj.hide_render=True;obj.hide_set(True)
for obj in list(bpy.context.scene.objects):
    if obj not in models:bpy.data.objects.remove(obj,do_unlink=True)
for i,obj in enumerate(models):obj.hide_render=i>0;obj.hide_set(i>0)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'AncientSealSeats_Editable.blend'))

# A true 3D line-mesh mark for the target: no opaque rectangular image card.
m.PARTS=[];markmat=m.simple_material('M_AncientSeal_TargetMark',(.40,.12,.025),0.,.6)
for path in SIGILS:
    m.stroke('Broken_mountain_target_sigil',[(x*2.2,0,y*2.2) for x,y in path],.00065,markmat,8)
for side in (-1,1):
    m.stroke('Target_seal_corner',[(side*.040,0,-.043),(side*.040,0,-.057),(side*.024,0,-.057)],.00055,markmat,8)
mark=m.join_group(m.PARTS,'SM_AncientSeal_TargetMark');m.unwrap(mark);m.activate(mark)
markfbx=P/'Export'/(mark.name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(markfbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='COPY',embed_textures=False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'AncientSealSeats_WithVFX_Editable.blend'))
(P/'production_receipt.json').write_text(json.dumps({'complete':True,'parts':rows,'target_mark_fbx':str(markfbx),'pbr_resolution':4096,'normal_convention':'OpenGL tangent normals; UE green flipped','visual_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('ANCIENT_SEAL_BOTH_NATIVE_VARIANTS_EXPORTED',flush=True)
