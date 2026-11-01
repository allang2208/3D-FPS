"""Precision solid reconstruction from Design/GuanLei_Design.png in the factory frame."""
import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;OUT=P/'Export';TEX=P/'Textures'
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as (a,b):
    b.objects=['SM_ThunderGodHammer_head_mount_factory']
bpy.context.collection.objects.link(b.objects[0])
bpy.context.preferences.filepaths.save_version=0
base=bpy.data.objects['SM_ThunderGodHammer_head_mount_factory'];source=base.data.copy();source.calc_loop_triangles()
oldmat=base.data.materials[0]
for o in list(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
# Keep the three physical interface bands exactly, including UVs and normals.
normals=[n.vector.copy() for n in source.corner_normals];corners=[];verts=[];faces=[]
def clip(poly,axis,value,positive):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0][axis]-value)*(1 if positive else -1);db=(b[0][axis]-value)*(1 if positive else -1)
        if da>=0:out.append(a)
        if (da>=0)!=(db>=0):out.append(tuple(x.lerp(y,da/(da-db)) for x,y in zip(a,b)))
    return out
for t in source.loop_triangles:
    poly=[(source.vertices[source.loops[i].vertex_index].co.copy(),source.uv_layers[0].data[i].uv.copy(),normals[i]) for i in t.loops]
    for axis,value,positive in [(0,-.0614452141,False),(0,.0605547859,True),(2,.853,False)]:
        cut=clip(poly,axis,value,positive)
        for k in range(1,len(cut)-1):
            tri=[cut[0],cut[k],cut[k+1]]
            if (tri[1][0]-tri[0][0]).cross(tri[2][0]-tri[0][0]).length<1.e-12:continue
            faces.append(tuple(range(len(verts),len(verts)+3)))
            for c in tri:verts.append(c[0]);corners.append(c)
mesh=bpy.data.meshes.new('OriginalMountingBands');mesh.from_pydata(verts,[],faces);mesh.update();uv=mesh.uv_layers.new(name='UVMap')
for poly in mesh.polygons:
    poly.use_smooth=True
    for i in poly.loop_indices:uv.data[i].uv=corners[mesh.loops[i].vertex_index][1]
mesh.normals_split_custom_set([tuple(corners[l.vertex_index][2]) for l in mesh.loops]);mesh.materials.append(oldmat)
interfaces=bpy.data.objects.new('FactoryInterfaces_UNCHANGED',mesh);bpy.context.collection.objects.link(interfaces)
parts=[];materials=[]
def material(name,color,metal,rough,emission=False):
    m=bpy.data.materials.new(name);m.use_nodes=True;ns=m.node_tree.nodes;ls=m.node_tree.links;bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
    noise=ns.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=640;noise.inputs['Detail'].default_value=3.2
    coord=ns.new('ShaderNodeTexCoord');ls.new(coord.outputs['Position'] if 'Position' in coord.outputs else coord.outputs['Generated'],noise.inputs['Vector'])
    # Generated coordinates provide subtle forged grain; all shape details are geometry.
    ramp=ns.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.12;ramp.color_ramp.elements[0].color=(*(c*.72 for c in color),1)
    ramp.color_ramp.elements[1].position=.88;ramp.color_ramp.elements[1].color=(*color,1);ls.new(noise.outputs['Fac'],ramp.inputs[0]);ls.new(ramp.outputs['Color'],bs.inputs['Base Color'])
    bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    bump=ns.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.14;bump.inputs['Distance'].default_value=.000018;ls.new(noise.outputs['Fac'],bump.inputs['Height']);ls.new(bump.outputs['Normal'],bs.inputs['Normal'])
    if emission:bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=3.0
    materials.append(m);return m
steel=material('Author_ForgedBlueSteel',(.065,.088,.11),.92,.38)
silver=material('Author_TurnedSilver',(.48,.51,.54),.96,.27)
dark=material('Author_DarkEnamel',(.012,.023,.035),.4,.32)
cyan=material('Author_ConductiveInlay',(.008,.38,.70),.65,.24,True)
def finish(o,mat,bevel=.0007):
    o.data.materials.append(mat);bpy.context.view_layer.objects.active=o
    if bevel:
        mod=o.modifiers.new('Machined rounded arris','BEVEL');mod.width=bevel;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in o.data.polygons:p.use_smooth=True
    mod=o.modifiers.new('Area weighted corner normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=50;bpy.ops.object.modifier_apply(modifier=mod.name)
    parts.append(o);return o
def plate(name,polygon,y,depth,mat,bevel=.0007):
    n=len(polygon);vs=[(x,y+d,z) for d in (-depth/2,depth/2) for x,z in polygon]
    fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);return finish(o,mat,bevel)
def box(name,loc,size,mat,bevel=.0008):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return finish(o,mat,bevel)
def cylinder(name,radius,depth,loc,mat,axis='Y',segments=96,bevel=.0005):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=radius,depth=depth,location=loc,rotation=(math.pi/2,0,0) if axis=='Y' else (0,0,0));o=bpy.context.object;o.name=name;return finish(o,mat,bevel)
def ring(name,profile,z,sign,mat):
    # Profile is radius/outward-depth; lathed around local Y, true turned geometry.
    N=128;vs=[(r*math.cos(2*math.pi*i/N),sign*y,z+r*math.sin(2*math.pi*i/N)) for r,y in profile for i in range(N)]
    fs=[(j*N+i,j*N+(i+1)%N,((j+1)%len(profile))*N+(i+1)%N,((j+1)%len(profile))*N+i) for j in range(len(profile)) for i in range(N)]
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);return finish(o,mat,0)
def stroke_polygon(points,width):
    pts=[Vector(p) for p in points];left=[];right=[]
    for i,p in enumerate(pts):
        before=(p-pts[max(0,i-1)]).normalized() if i else (pts[1]-p).normalized()
        after=(pts[min(len(pts)-1,i+1)]-p).normalized() if i<len(pts)-1 else before
        tangent=(before+after).normalized();normal=Vector((-tangent.y,tangent.x));den=max(.55,normal.dot(Vector((-before.y,before.x))))
        left.append(tuple(p+normal*width*.5/den));right.append(tuple(p-normal*width*.5/den))
    return left+right[::-1]
def groove(host,name,points,sign,face_y,width=.0023):
    cutter=plate(name+'_cutter',stroke_polygon(points,width),sign*(face_y-.0003),.003,dark,0)
    bpy.context.view_layer.objects.active=host;mod=host.modifiers.new('Recessed lightning channel','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name)
    parts.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)
    plate(name+'_enamel_trench',stroke_polygon(points,width*.90),sign*(face_y-.00125),.00045,dark,.00015)
    plate(name+'_flush_cyan',stroke_polygon(points,width*.36),sign*(face_y-.00090),.00035,cyan,.00010)
def braid(name,zc,sign,y,width=.064,height=.008):
    # Flattened interlaced ribbons rise/fall at crossings, not round wire ornaments.
    for j in range(2):
        pts=[]
        for i in range(129):
            t=i/128;phase=t*math.pi*6+j*math.pi
            pts.append(Vector(((t-.5)*width,sign*(y+.00055*math.cos(phase)),zc+height*.5*math.sin(phase))))
        vs=[]
        for i,p in enumerate(pts):
            tangent=(pts[min(i+1,128)]-pts[max(i-1,0)]).normalized();side=Vector((-tangent.z,0,tangent.x)).normalized()*.00060
            for s,d in [(-1,-1),(1,-1),(1,1),(-1,1)]:vs.append(p+side*s+Vector((0,d*.00025,0)))
        fs=[]
        for i in range(128):
            for k in range(4):fs.append((i*4+k,i*4+(k+1)%4,(i+1)*4+(k+1)%4,(i+1)*4+k))
        fs.extend([(3,2,1,0),(512,513,514,515)])
        me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);finish(o,silver,.00010)
# Main load-bearing core and small lower coupling merge under the preserved bands.
body=plate('Continuous forged core',[(-.0625,.867),(-.052,.855),(.052,.855),(.0625,.867),(.0625,.960),(.051,.981),(-.051,.981),(-.0625,.960)],0,.100,steel,.0022)
cylinder('Lower socket',.027,.024,(0,0,.855),steel,'Z',96,.001)
cylinder('Turned coupling rim',.0285,.004,(0,0,.854),silver,'Z',96,.0006)
plate('Upper solid crown',[(-.061,.982),(-.055,1.000),(.055,1.000),(.061,.982)],0,.112,steel,.0017)
# Deliberate eight-sided silhouette with broad plate surfaces and fine inset tracks.
for sign in (-1,1):
    cylinder('Recessed dark badge field',.043,.010,(0,sign*.057,.922),dark)
    ring('Double turned badge bezel',[(.042,.060),(.042,.064),(.043,.066),(.047,.066),(.049,.064),(.049,.060),(.047,.058),(.043,.058)],.922,sign,silver)
    ring('Outer dark hairline',[(.0470,.066),(.0470,.06635),(.0476,.06635),(.0476,.066)],.922,sign,dark)
    ring('Inner bright lip',[(.0421,.0640),(.0421,.0652),(.0428,.0657),(.0433,.0652),(.0433,.0640)],.922,sign,silver)
    for i in range(8):
        a=2*math.pi*i/8;x=.0457*math.cos(a);z=.922+.0457*math.sin(a)
        cylinder('Flush bezel rivet socket',.0031,.0008,(x,sign*.0664,z),dark,segments=32,bevel=.00015)
        cylinder('Domed silver rivet',.0023,.0018,(x,sign*.0671,z),silver,segments=32,bevel=.0006)
    # Single Thurisaz-inspired heraldic mark: faceted staff and one triangular branch.
    plate('Thunder rune staff',[(-.006,.889),(-.001,.895),(-.001,.950),(-.007,.958),(-.007,.895)],sign*.064,.0035,silver,.00065)
    plate('Thunder rune upper branch',[(-.002,.942),(.022,.924),(.015,.924),(-.002,.935)],sign*.064,.0035,silver,.00065)
    plate('Thunder rune lower branch',[(-.002,.906),(.022,.924),(.015,.924),(-.002,.913)],sign*.064,.0035,silver,.00065)
    # Cyan inner bevel is a narrow inset accent, not another overlaid symbol.
    plate('Rune inner light',stroke_polygon([(.001,.915),(.013,.924),(.001,.933)],.00065),sign*.0622,.0005,cyan,.00012)
    for sx in (-1,1):
        poly=[(sx*x,z) for x,z in [(.040,.861),(.052,.861),(.061,.875),(.059,.955),(.053,.982),(.041,.982),(.047,.951),(.047,.881)]]
        cheek=plate('Beveled load cheek',poly,sign*.052,.012,silver,.0012)
        path=[(sx*x,z) for x,z in [(.047,.867),(.047,.881),(.053,.888),(.052,.902),(.056,.913),(.052,.924),(.053,.941),(.049,.952),(.046,.973)]]
        groove(cheek,'Recessed lightning cheek',path,sign,.058,.0028)
        plate('Crown clamp',[(sx*x,z) for x,z in [(.035,.979),(.047,.978),(.049,1.001),(.037,1.001)]],sign*.056,.010,silver,.001)
        # Crown fins are thick wedge plates tied to the continuous crown.
        fin=plate('Crown tapered ear',[(sx*.049,.983),(sx*.061,.984),(sx*.064,.992),(sx*.051,1.000)],sign*.044,.018,steel,.001)
        groove(fin,'Crown fine inlay',[(sx*.053,.988),(sx*.059,.992),(sx*.054,.996)],sign,.053,.0017)
    for z,w,h in [(.989,.068,.014),(.8615,.068,.014)]:
        box('Engraving panel border',(0,sign*.055,z),(w+.003,.006,h+.003),silver,.0009)
        box('Engraving recessed ground',(0,sign*.058,z),(w,.001,h),dark,.0005)
        braid('Woven silver relief',z,sign,.0592,w-.005,h-.004)
    plate('Crest pointed keystone',[(-.006,.973),(0,.980),(.006,.973),(.003,.968),(-.003,.968)],sign*.054,.010,silver,.00065)
# Apply stable transforms, join new geometry, then bake PBR atlas without modifying interface UVs.
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join();new=bpy.context.object;new.name='GuanLei_ForgedAssembly'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
tri=new.modifiers.new('Stable export tangents','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.render.bake.margin=12
for layer in scene.view_layers:layer.material_override=None
scene.use_nodes=False
interfaces.hide_render=True
original_outputs={};original_nodes={}
for m in new.data.materials:
    out=next(n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL');original_outputs[m.name]=out
    original_nodes[m.name]=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
def bake(kind):
    im=bpy.data.images.new('T_GuanLeiV2_'+kind,2048,2048,alpha=False);im.colorspace_settings.name='sRGB' if kind in ('BaseColor','Emissive') else 'Non-Color'
    for m in new.data.materials:
        ns=m.node_tree.nodes;ls=m.node_tree.links;out=original_outputs[m.name];bs=original_nodes[m.name]
        node=ns.new('ShaderNodeTexImage');node.image=im;ns.active=node;node.select=True
        if kind=='Normal':ls.new(bs.outputs['BSDF'],out.inputs['Surface']);continue
        em=ns.new('ShaderNodeEmission')
        if kind=='BaseColor':ls.new(bs.inputs['Base Color'].links[0].from_socket,em.inputs['Color'])
        elif kind=='ORM':em.inputs['Color'].default_value=(1,bs.inputs['Roughness'].default_value,bs.inputs['Metallic'].default_value,1)
        else:em.inputs['Color'].default_value=bs.inputs['Emission Color'].default_value if bs.inputs['Emission Strength'].default_value>0 else (0,0,0,1)
        ls.new(em.outputs[0],out.inputs['Surface'])
    bpy.ops.object.bake(type='NORMAL' if kind=='Normal' else 'EMIT')
    im.filepath_raw=str(TEX/(im.name+'.png'));im.file_format='PNG';im.save();return im
maps={k:bake(k) for k in ['BaseColor','ORM','Emissive','Normal']}
atlas=bpy.data.materials.new('M_GuanLeiSeatV2');atlas.use_nodes=True;ns=atlas.node_tree.nodes;ls=atlas.node_tree.links;bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
nodes={}
for k,im in maps.items():n=ns.new('ShaderNodeTexImage');n.image=im;nodes[k]=n
ls.new(nodes['BaseColor'].outputs['Color'],bs.inputs['Base Color']);sep=ns.new('ShaderNodeSeparateColor');ls.new(nodes['ORM'].outputs['Color'],sep.inputs[0]);ls.new(sep.outputs['Green'],bs.inputs['Roughness']);ls.new(sep.outputs['Blue'],bs.inputs['Metallic'])
nm=ns.new('ShaderNodeNormalMap');ls.new(nodes['Normal'].outputs['Color'],nm.inputs['Color']);ls.new(nm.outputs['Normal'],bs.inputs['Normal'])
ls.new(nodes['Emissive'].outputs['Color'],bs.inputs['Emission Color']);bs.inputs['Emission Strength'].default_value=3.0
new.data.materials.clear();new.data.materials.append(atlas)
for f in new.data.polygons:f.material_index=0
interfaces.hide_render=False;interfaces.select_set(True);bpy.context.view_layer.objects.active=new;bpy.ops.object.join();new.name='SM_ThunderHammer_GuanLeiSeatV2'
new.data.calc_loop_triangles()
bpy.ops.export_scene.fbx(filepath=str(OUT/(new.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'GuanLeiSeatV2_Editable.blend'))
(P/'model_manifest.json').write_text(json.dumps({'mesh':new.name,'design':'Design/GuanLei_Design.png','triangles':len(new.data.loop_triangles),'materials':[m.name for m in new.data.materials],'textures':[im.name for im in maps.values()],'interface':'thunder_god_hammer_modular_v1','retained_bands_m':{'left':[-.0654452141,-.0614452141],'right':[.0605547859,.0645547859],'neck':[.842,.853]},'author_units':'metres','design_fit':'Original 130 mm side span and 842 mm neck station retained; crown height 1001 mm, original head axis 916 mm','runtime_tested':False},indent=2),encoding='utf-8')
print('GUANLEI_V2_MODEL_SAVED',flush=True)
