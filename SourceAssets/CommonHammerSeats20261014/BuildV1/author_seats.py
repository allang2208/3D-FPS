"""Model the three approved center seats on unchanged real factory interfaces."""
import bpy,bmesh,math,json,sys,runpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2];sys.path.insert(0,str(P))
from catalog import OPTIONS
for folder in ('Export','IconSources'):(P/folder).mkdir(parents=True,exist_ok=True)
FACTORY=ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend'
HEADS=ROOT/'SourceAssets/CommonHammerHeads20261014/DesignBuildV2/CommonHammerHeads_DesignV2_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(FACTORY));bpy.context.preferences.filepaths.save_version=0
original=bpy.data.objects['SM_Warhammer_head_mount_factory'].data.copy();original.update();old=original.materials[0]
with bpy.data.libraries.load(str(HEADS),link=False) as (src,dst):
    dst.materials=['M_CommonHammerHeadSteel']
steel=dst.materials[0]
dark=steel.copy();dark.name='M_CommonHammerSeatDarkSteel'
shader=next(n for n in dark.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
base=shader.inputs['Base Color'];link=base.links[0]
mult=dark.node_tree.nodes.new('ShaderNodeMixRGB');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=1
mult.inputs[2].default_value=(.38,.38,.38,1);dark.node_tree.links.new(link.from_socket,mult.inputs[1]);dark.node_tree.links.new(mult.outputs[0],base)
damper=bpy.data.materials.new('M_CommonHammerSeatDamping');damper.use_nodes=True
shader=next(n for n in damper.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
shader.inputs['Base Color'].default_value=(.025,.025,.025,1);shader.inputs['Roughness'].default_value=.74
normal_image=next(n.image for n in steel.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.name.startswith('T_CommonHammerSteel_Normal'))
uv=damper.node_tree.nodes.new('ShaderNodeUVMap');uv.uv_map='SteelUV'
sample=damper.node_tree.nodes.new('ShaderNodeTexImage');sample.image=normal_image
normal=damper.node_tree.nodes.new('ShaderNodeNormalMap');normal.uv_map='SteelUV';normal.inputs['Strength'].default_value=.25
damper.node_tree.links.new(uv.outputs[0],sample.inputs['Vector']);damper.node_tree.links.new(sample.outputs['Color'],normal.inputs['Color']);damper.node_tree.links.new(normal.outputs[0],shader.inputs['Normal'])
MATS=[old,steel,dark,damper]

# Retain the actual side contact cheeks, lower joining collar and top cap.
# The interior rectangle is rebuilt; UV and corner normals are interpolated at its cuts.
def clip(poly,axis,limit,positive):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0][axis]-limit)*(1 if positive else -1);db=(b[0][axis]-limit)*(1 if positive else -1)
        if da>=0:out.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);out.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return out
original.calc_loop_triangles();normals=[n.vector.copy() for n in original.corner_normals]
vertices=[];faces=[];corners=[]
planes=[(0,-.0375,True),(0,.0375,False),(2,.887,True),(2,.972,False)]
for tri in original.loop_triangles:
    remaining=[(original.vertices[original.loops[i].vertex_index].co.copy(),original.uv_layers[0].data[i].uv.copy(),normals[i]) for i in tri.loops]
    pieces=[]
    for axis,limit,inside in planes:
        outside=clip(remaining,axis,limit,not inside)
        if outside:pieces.append(outside)
        remaining=clip(remaining,axis,limit,inside)
        if not remaining:break
    for polygon in pieces:
        for i in range(1,len(polygon)-1):
            triangle=[polygon[0],polygon[i],polygon[i+1]]
            if (triangle[1][0]-triangle[0][0]).cross(triangle[2][0]-triangle[0][0]).length<1e-12:continue
            faces.append(tuple(range(len(vertices),len(vertices)+3)))
            for item in triangle:vertices.append(item[0]);corners.append(item)
connector=bpy.data.meshes.new('Factory interfaces and collars');connector.from_pydata(vertices,[],faces);connector.update()
for mat in MATS:connector.materials.append(mat)
u0=connector.uv_layers.new(name='UVMap');u1=connector.uv_layers.new(name='SteelUV')
stored=connector.attributes.new('SurfaceNormal',type='FLOAT_VECTOR',domain='CORNER')
color=connector.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
for face in connector.polygons:
    face.use_smooth=True
    for i in face.loop_indices:
        co,tex,n=corners[connector.loops[i].vertex_index];u0.data[i].uv=tex;u1.data[i].uv=tex
        stored.data[i].vector=n.normalized();color.data[i].color=(0,0,0,1)
bm=bmesh.new();bm.from_mesh(connector)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
new=bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)['faces']
bm.normal_update();stored=bm.loops.layers.float_vector['SurfaceNormal'];uv0=bm.loops.layers.uv['UVMap'];uv1=bm.loops.layers.uv['SteelUV'];col=bm.loops.layers.float_color['Color']
for face in new:
    face.material_index=1;face.smooth=False
    for loop in face.loops:
        co=loop.vert.co;axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(face.normal[i]))]
        t=(co[axes[0]]/.12,co[axes[1]]/.12);loop[uv0].uv=t;loop[uv1].uv=t
        loop[col]=(1,0,0,1);loop[stored]=face.normal
bmesh.ops.triangulate(bm,faces=new);bm.to_mesh(connector);bm.free();connector.update()
connector.normals_split_custom_set([tuple(n.vector) for n in connector.attributes['SurfaceNormal'].data])
for obj in list(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)

def active(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj

def finish(obj,mat,width=.001,segments=3):
    active(obj);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    obj.data.materials.clear();obj.data.materials.append(mat)
    for poly in obj.data.polygons:poly.material_index=0
    if width:
        mod=obj.modifiers.new('Machined edge bevel','BEVEL');mod.width=width;mod.segments=segments
        mod.limit_method='ANGLE';mod.angle_limit=math.radians(35);mod.use_clamp_overlap=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for poly in obj.data.polygons:poly.use_smooth=True
    obj.data.set_sharp_from_angle(angle=math.radians(40))
    mod=obj.modifiers.new('Face weighted machining normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    uv0=obj.data.uv_layers.get('UVMap') or obj.data.uv_layers.new(name='UVMap')
    uv1=obj.data.uv_layers.get('SteelUV') or obj.data.uv_layers.new(name='SteelUV')
    color=obj.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
    for poly in obj.data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(poly.normal[i]))]
        for index in poly.loop_indices:
            co=obj.data.vertices[obj.data.loops[index].vertex_index].co
            coord=(co[axes[0]]/.12,co[axes[1]]/.12);uv0.data[index].uv=coord;uv1.data[index].uv=coord;color.data[index].color=(1,0,0,1)
    return obj

def box(name,loc,size,mat=steel,width=.001):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);obj=bpy.context.object;obj.name=name;obj.scale=size
    return finish(obj,mat,width)

def cylinder(name,loc,radius,depth,mat=steel,axis='Y',width=.0004):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=radius,depth=depth,location=loc,
        rotation=(math.pi/2,0,0) if axis=='Y' else (0,0,0))
    obj=bpy.context.object;obj.name=name;return finish(obj,mat,width)

def prism(name,points,y,thickness):
    n=len(points);verts=[(x,y+s*thickness/2,z) for s in (-1,1) for x,z in points]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj);return obj

def window_plate(sign):
    # Four closed triangular holes, cut through a solid plate before edge finishing.
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,sign*.038,.929));plate=bpy.context.object
    plate.name='Light triangular-window plate';plate.scale=(.075,.008,.086)
    active(plate);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    triangles=[((- .022,.033),(.022,.033),(0,.010)),((-.022,-.033),(0,-.010),(.022,-.033)),
               ((-.028,-.024),(-.028,.024),(-.010,0)),((.028,-.024),(.010,0),(.028,.024))]
    for points in triangles:
        cutter=prism('Window cutter',[(x,z+.929) for x,z in points],sign*.038,.024)
        active(plate);mod=plate.modifiers.new('True triangular opening','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
        bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    bm=bmesh.new();bm.from_mesh(plate.data);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7);bm.to_mesh(plate.data);bm.free()
    return finish(plate,steel,.0008)

def rivet(parts,x,z,y,r=.0031):
    sign=1 if y>0 else -1
    parts.append(cylinder('Rivet recessed washer',(x,y,z),r*1.35,.0012,dark))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=1,location=(x,y+sign*.00065,z))
    obj=bpy.context.object;obj.name='Domed steel rivet';obj.scale=(r,r*.55,r)
    parts.append(finish(obj,steel,0))

rows=[];models=[]
for option in OPTIONS:
    kind=option['id'];root=bpy.data.objects.new('Factory interfaces '+kind,connector.copy());bpy.context.scene.collection.objects.link(root);parts=[root]
    depth=.077 if kind=='reinforced_block' else .047 if kind=='ribbed_light' else .063
    parts.append(box('Continuous load-bearing core',(0,0,.929),(.076,depth,.087),dark if kind=='ribbed_light' else steel,.002))
    for sign in (-1,1):
        if kind=='reinforced_block':
            parts.append(box('Stepped reinforcing shoulder',(0,sign*.039,.929),(.078,.010,.091),steel,.002))
            parts.append(box('Thick outer cover',(0,sign*.047,.929),(.073,.010,.084),steel,.0015))
            parts.append(box('Recessed darker face',(0,sign*.052,.929),(.061,.002,.073),dark,.001))
            surface=sign*.0535
            for x in (-.023,.023):
                for z in (.902,.956):rivet(parts,x,z,surface)
        elif kind=='ribbed_light':
            parts.append(window_plate(sign));surface=sign*.043
            # Standoffs join the open outer plate to the continuous inner core.
            for x in (-.032,.032):parts.append(box('Outer support rail',(x,sign*.030,.929),(.010,.016,.084),steel,.001))
            for z in (.890,.968):parts.append(box('Top and bottom bridge',(0,sign*.030,z),(.073,.016,.008),steel,.001))
        else:
            for index,(y,w,h) in enumerate(((.034,.078,.091),(.041,.074,.087),(.048,.069,.082))):
                parts.append(box('Laminate steel layer '+str(index),(0,sign*y,.929),(w,.005,h),steel,.001))
                if index<2:parts.append(box('Thin damping layer '+str(index),(0,sign*(y+.0035),.929),(w-.002,.002,h-.002),damper,.0005))
            parts.append(box('Inset central cover',(0,sign*.0515,.929),(.059,.002,.072),dark,.0007));surface=sign*.053
            for x in (-.030,.030):
                for z in (.894,.964):
                    parts.append(cylinder('Tie rod outer washer',(x,sign*.0505,z),.0051,.003,dark))
                    parts.append(cylinder('Tie rod socket head',(x,sign*.053,z),.0038,.0035,steel))
            for x in (-.022,.022):
                for z in (.903,.955):rivet(parts,x,z,sign*.053,.0015)
        parts.append(cylinder('Central boss dark seating ring',(0,surface,.929),.0095,.0015,dark))
        rivet(parts,0,.929,surface+sign*.001,.0078)
    if kind=='laminated_damper':
        for x in (-.030,.030):
            for z in (.894,.964):parts.append(cylinder('Continuous through tie rod',(x,0,z),.0023,.104,steel,width=.0002))
    if kind=='ribbed_light':
        parts.append(box('Compact top bridge',(0,0,.974),(.065,.064,.004),steel,.001))
    active(root)
    for obj in parts:obj.select_set(True)
    bpy.ops.object.join();root.name='SM_CommonHammerSeat_'+kind+'_V1'
    active(root);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    # Freeze triangulation for the exported mesh without changing authoring coordinates.
    triangulate=root.modifiers.new('Export triangles','TRIANGULATE');triangulate.keep_custom_normals=True
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(root.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
    root.data.calc_loop_triangles();rows.append({'id':kind,'name':option['name'],'mesh':root.name,'triangles':len(root.data.loop_triangles),
        'location_cm':[0,0,0],'materials':[m.name for m in root.data.materials]})
    models.append(root);root.hide_render=True;root.hide_set(True)
models[0].hide_render=False;models[0].hide_set(False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'CommonHammerSeats_Editable.blend'))
(P/'exports.json').write_text(json.dumps({'parts':rows,'interface':'warhammer_factory_v1','slot':'head_mount','root_pivot_m':[0,0,0],
    'preserved_source':str(FACTORY),'source_keep':{'side_cheeks_abs_x_min':.0375,'bottom_z_max':.887,'top_z_min':.972},
    'design_reference':'../DesignV1/common-hammer-seats-design-v1.png','game_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('COMMON_HAMMER_SEATS_EXPORTED '+json.dumps(rows,ensure_ascii=False))
