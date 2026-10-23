"""Split the supplied factory hammer at shared mounting surfaces; no gameplay tests."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
SOURCE=P.parent/'RuneboundWarhammer_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
original=bpy.data.objects['SM_RuneboundWarhammer']
source=original.data.copy();source.update()
# Measured factory collars, in the unchanged WPN author frame (metres).
CUTS={'tail':(2,-.085),'wrap':(2,.405),'shaft':(2,.780),'neck':(2,.842),'left':(0,-.0354452141),'right':(0,.0345547859)}
PIVOTS={'head_mount':(0,0,0),'hammer_heads':(0,0,.916),'neck':(0,0,.842),
        'shaft':(0,0,.780),'grip':(0,0,.405),'pommel':(0,0,-.085)}
RULES={'head_mount':[[('neck',True),('left',True),('right',False)]],
       'hammer_heads':[[('neck',True),('left',False)],[('neck',True),('right',True)]],
       'neck':[[('shaft',True),('neck',False)]],
       'shaft':[[('wrap',True),('shaft',False)]],
       'grip':[[('tail',True),('wrap',False)]], 'pommel':[[('tail',False)]]}
LABELS={'head_mount':'中央锤座','hammer_heads':'双侧锤头','neck':'锤颈套箍','shaft':'金属长柄','grip':'握持包覆','pommel':'柄尾配重'}

def distance(point,key):
    axis,value=CUTS[key];return point[axis]-value

def clip(poly,key,positive):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=distance(a[0],key)*(1 if positive else -1);db=distance(b[0],key)*(1 if positive else -1)
        if da>=0:result.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);result.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return result

source.calc_loop_triangles();normals=[n.vector.copy() for n in source.corner_normals]
triangles=[]
for tri in source.loop_triangles:
    triangles.append([(source.vertices[source.loops[i].vertex_index].co.copy(),source.uv_layers[0].data[i].uv.copy(),normals[i]) for i in tri.loops])
for o in list(bpy.context.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
rows=[];interfaces={}
for slot,pivot_values in PIVOTS.items():
    pivot=Vector(pivot_values);vertices=[];faces=[];corners=[]
    for triangle in triangles:
        for rule in RULES[slot]:
            poly=triangle
            for key,positive in rule:
                poly=clip(poly,key,positive)
                if not poly:break
            for i in range(1,len(poly)-1):
                tri=[poly[0],poly[i],poly[i+1]]
                if (tri[1][0]-tri[0][0]).cross(tri[2][0]-tri[0][0]).length<1e-12:continue
                faces.append(tuple(range(len(vertices),len(vertices)+3)))
                for corner in tri:vertices.append(corner[0]-pivot);corners.append(corner)
    name='SM_RuneboundWarhammer_'+slot+'_factory';mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    mesh.materials.append(source.materials[0]);uv=mesh.uv_layers.new(name='UVMap')
    stored=mesh.attributes.new('SurfaceNormal',type='FLOAT_VECTOR',domain='CORNER')
    for poly in mesh.polygons:
        poly.use_smooth=True
        for i in poly.loop_indices:
            corner=corners[mesh.loops[i].vertex_index];uv.data[i].uv=corner[1];stored.data[i].vector=corner[2].normalized()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000005)
    mounts=[];surface_normal=bm.loops.layers.float_vector['SurfaceNormal'];uvlayer=bm.loops.layers.uv[0]
    keys=sorted({key for rule in RULES[slot] for key,_ in rule})
    for key in keys:
        edges=[e for e in bm.edges if e.is_boundary and all(abs(distance(v.co+pivot,key))<.000003 for v in e.verts)]
        if not edges:continue
        mounts.append({'cut':key,'segments_m':[[list(v.co+pivot) for v in e.verts] for e in edges]})
        caps=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']
        if caps:caps=bmesh.ops.triangulate(bm,faces=caps)['faces']
        axis=CUTS[key][0];plane=[i for i in range(3) if i!=axis]
        for face in caps:
            face.smooth=False;face.normal_update()
            for loop in face.loops:
                loop[surface_normal]=face.normal
                co=loop.vert.co+pivot;loop[uvlayer].uv=(.5+co[plane[0]]*.1,.5+co[plane[1]]*.1)
    bm.to_mesh(mesh);bm.free();mesh.update()
    mesh.normals_split_custom_set([tuple(n.vector) for n in mesh.attributes['SurfaceNormal'].data])
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
    obj.location=pivot
    mount=bpy.data.objects.new('Mount_'+slot,None);bpy.context.scene.collection.objects.link(mount);mount.location=pivot;mount.empty_display_type='ARROWS';mount.empty_display_size=.02
    interfaces[slot]={'pivot_m':list(pivot),'interfaces':mounts,'rules':RULES[slot]}
    mesh.calc_loop_triangles();rows.append({'slot':slot,'name':LABELS[slot],'mesh':name,'id':'factory',
        'location_cm':[pivot.x*100,-pivot.y*100,pivot.z*100],'triangles':len(mesh.loop_triangles)})
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'RuneboundWarhammer_Modular_Editable.blend'))
(P/'interfaces.json').write_text(json.dumps({'interface':'runebound_warhammer_modular_v1','units':'metres; UE offsets in centimetres','cuts':CUTS,'parts':interfaces},ensure_ascii=False,indent=2),encoding='utf-8')
(P/'exports.json').write_text(json.dumps({'source':str(SOURCE),'parts':rows,'tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('WARHAMMER_FACTORY_MODULES_EXPORTED',json.dumps(rows,ensure_ascii=False),flush=True)
