"""Three paired steel heads, joined to the actual factory neck boundaries."""
import bpy,bmesh,json,math,sys
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[3];sys.path.insert(0,str(P))
from catalog import OPTIONS
for folder in ('Export','Textures'): (P/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets/SteelWarhammer20261014/ModulesV1/Warhammer_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
factory=bpy.data.objects['SM_Warhammer_hammer_heads_factory'];source=factory.data.copy();source.update()
old_mat=source.materials[0];cut=.075
# Reuse the actual shared hammer steel and its packed PBR maps.
with bpy.data.libraries.load(str(ROOT/'SourceAssets/CommonHammerHeads20261014/DesignBuildV2/CommonHammerHeads_DesignV2_Editable.blend'),link=False) as (src,dst):
    dst.materials=['M_CommonHammerHeadSteel']
mat=dst.materials[0]

def clip(poly,axis,limit,positive):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0][axis]-limit)*(1 if positive else -1);db=(b[0][axis]-limit)*(1 if positive else -1)
        if da>=0:out.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);out.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return out

source.calc_loop_triangles();normals=[n.vector.copy() for n in source.corner_normals]
verts=[];faces=[];corners=[]
for tri in source.loop_triangles:
    poly=[(source.vertices[source.loops[i].vertex_index].co.copy(),source.uv_layers[0].data[i].uv.copy(),normals[i]) for i in tri.loops]
    poly=clip(clip(poly,0,-cut,True),0,cut,False)
    for k in range(1,len(poly)-1):
        triangle=[poly[0],poly[k],poly[k+1]]
        if (triangle[1][0]-triangle[0][0]).cross(triangle[2][0]-triangle[0][0]).length<1e-12:continue
        faces.append(tuple(range(len(verts),len(verts)+3)))
        for item in triangle:verts.append(item[0]);corners.append(item)
connector=bpy.data.meshes.new('Factory head necks');connector.from_pydata(verts,[],faces);connector.update()
connector.materials.append(old_mat);connector.materials.append(mat)
uv0=connector.uv_layers.new(name='UVMap');uv1=connector.uv_layers.new(name='SteelUV')
stored=connector.attributes.new('SurfaceNormal',type='FLOAT_VECTOR',domain='CORNER')
color=connector.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
for f in connector.polygons:
    f.use_smooth=True
    for i in f.loop_indices:
        item=corners[connector.loops[i].vertex_index];uv0.data[i].uv=item[1];uv1.data[i].uv=item[1]
        stored.data[i].vector=item[2].normalized();color.data[i].color=(0,0,0,1)
for obj in list(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)

# Successive solid cross-sections define shoulders, bevels, rims and recessed faces.
# None is the unchanged tangent continuation at the real factory neck boundary.
PROFILES={
 'pointed_hammer':[
  (.078,None,0),(.084,(.0295,.0305),0),
  (.086,(.032,.033),0),(.091,(.032,.033),0),(.094,(.0295,.0305),0),
  (.099,(.034,.035),.25),(.106,(.045,.047),.8),(.111,(.048,.050),1),
  (.117,(.046,.048),1),(.143,(.034,.0355),1),(.171,(.021,.022),1),
  (.190,(.012,.0125),.9),(.196,(.009,.0095),.45),(.199,(.008,.0085),0),
  (.213,(.0007,.0007),0)]
}

# Eight broad crests with recessed longitudinal channels. Ray/polygon intersection
# preserves planar facets rather than making a wavy circular cone.
PROFILE_SECTOR=[(0,1.0),(3,1.0),(7,.95),(16,.79),(22.5,.77),(29,.79),(38,.95),(42,1.0),(45,1.0)]
def radius_shape(kind,theta,ry,rz,flange):
    a=theta%(math.pi/4)
    rays=[(math.radians(deg),Vector((r*math.cos(math.radians(deg)),r*math.sin(math.radians(deg))))) for deg,r in PROFILE_SECTOR]
    direction=Vector((math.cos(a),math.sin(a)))
    radius=1.
    for (aa,p),(bb,q) in zip(rays,rays[1:]):
        if aa-1e-8<=a<=bb+1e-8:
            edge=q-p
            cross=direction.x*edge.y-direction.y*edge.x
            radius=(p.x*edge.y-p.y*edge.x)/cross
            break
    # End cap is an eight-sided clean taper; flutes gently close before it.
    oct_radius=math.cos(math.pi/8)/math.cos(a-math.pi/8)
    r=oct_radius*(1-flange)+radius*flange
    return Vector((0,ry*math.cos(theta)*r,rz*math.sin(theta)*r))

receipts=[];interfaces={}
for option in OPTIONS:
    kind=option['id'];data=connector.copy();bm=bmesh.new();bm.from_mesh(data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000005);bm.normal_update()
    normals_layer=bm.loops.layers.float_vector['SurfaceNormal'];u0=bm.loops.layers.uv['UVMap'];u1=bm.loops.layers.uv['SteelUV'];col=bm.loops.layers.float_color['Color']
    all_new=[];caps=[];stored_boundary={};rings_receipt=[]
    for sign in (-1,1):
        edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.x-sign*cut)<3e-6 for v in e.verts)]
        graph={}
        for edge in edges:
            for v in edge.verts:graph.setdefault(v,[]).append(edge.other_vert(v))
        if not graph or any(len(v)!=2 for v in graph.values()):raise RuntimeError('Factory neck boundary is not a single ring: '+kind)
        start=min(graph,key=lambda v:tuple(v.co));ring=[start];previous=None;current=start
        while True:
            nxt=next(v for v in graph[current] if v!=previous)
            if nxt==start:break
            if nxt in ring:raise RuntimeError('Factory neck ring folds onto itself')
            ring.append(nxt);previous,current=current,nxt
        area=sum(a.co.y*b.co.z-b.co.y*a.co.z for a,b in zip(ring,ring[1:]+ring[:1]))
        if area*sign<0:ring.reverse()
        center=Vector((sign*cut,(min(v.co.y for v in ring)+max(v.co.y for v in ring))*.5,(min(v.co.z for v in ring)+max(v.co.z for v in ring))*.5))
        original=[v.co.copy() for v in ring];angles=[math.atan2(v.co.z-center.z,v.co.y-center.y) for v in ring]
        old_uv=[];old_norm=[]
        for v in ring:
            loops=[loop for face in v.link_faces for loop in face.loops if loop.vert==v]
            old_uv.append(loops[0][u0].uv.copy());old_norm.append(sum((Vector(l[normals_layer]) for l in loops),Vector()).normalized())
            stored_boundary[v]=old_norm[-1]
        rings_receipt.append({'side':sign,'cut_x_m':sign*cut,'boundary_local_m':[list(v.co) for v in ring]})
        n=len(ring);previous_ring=ring
        unwrapped=np.unwrap(np.array(angles));direction=1. if unwrapped[-1]>unwrapped[0] else -1.
        for stage,(x,dims,flange) in enumerate(PROFILES[kind]):
            new_ring=[]
            for j in range(n):
                if dims is None:
                    radial=Vector((0,original[j].y-center.y,original[j].z-center.z)).normalized()
                    denom=old_norm[j].dot(radial)
                    slope=max(-1.,min(1.,-old_norm[j].x*sign/denom)) if abs(denom)>.1 else 0.
                    point=original[j]+Vector((sign*(x-cut),0,0))+radial*(x-cut)*slope
                else:point=Vector((sign*x,center.y,center.z))+radius_shape(kind,angles[j],*dims,flange)
                new_ring.append(bm.verts.new(point))
            for j in range(n):
                k=(j+1)%n;face=bm.faces.new((previous_ring[j],previous_ring[k],new_ring[k],new_ring[j]));face.material_index=1;face.smooth=True;all_new.append(face)
                for loop,index in zip(face.loops,(j,k,k,j)):
                    blend=min(1.,max(0.,(abs(loop.vert.co.x)-cut)/.025))
                    angle=unwrapped[index]+(direction*math.tau if index==0 and j==n-1 else 0.)
                    new_uv=Vector(((abs(loop.vert.co.x)-cut)/.12,(angle-unwrapped[0])*.05/.12))
                    loop[u1].uv=new_uv;loop[u0].uv=old_uv[index].lerp(new_uv,blend);loop[col]=(blend,0,0,1)
            previous_ring=new_ring
        cap_center=bm.verts.new(Vector((sign*(PROFILES[kind][-1][0]+.0007),center.y,center.z)))
        for j in range(n):
            face=bm.faces.new((previous_ring[j],previous_ring[(j+1)%n],cap_center));face.material_index=1;face.smooth=False;caps.append(face);all_new.append(face)
            for loop in face.loops:
                loop[u0].uv=((loop.vert.co.y-center.y)/.12+.5,(loop.vert.co.z-center.z)/.12+.5);loop[u1].uv=loop[u0].uv;loop[col]=(1,0,0,1)
    bm.normal_update()
    for face in all_new:
        for loop in face.loops:loop[normals_layer]=stored_boundary.get(loop.vert,face.normal if face in caps or abs(loop.vert.co.x)>.104 else loop.vert.normal)
    bmesh.ops.triangulate(bm,faces=all_new);bm.to_mesh(data);bm.free();data.update()
    data.normals_split_custom_set([tuple(n.vector) for n in data.attributes['SurfaceNormal'].data])
    name='SM_CommonHammerHeads_pointed_hammer_V1';obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
    data.calc_loop_triangles();receipts.append({'id':kind,'name':option['name'],'mesh':name,'triangles':len(data.loop_triangles),'location_cm':[0,0,92.5000011920929],'materials':[m.name for m in data.materials]})
    interfaces[kind]=rings_receipt;obj.location.z=.925;obj.hide_render=True;obj.hide_set(True)
first=bpy.data.objects[receipts[0]['mesh']];first.hide_render=False;first.hide_set(False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'PointedHammer_Editable.blend'))
(P/'exports.json').write_text(json.dumps({'parts':receipts,'source_interface':'warhammer_factory_v1','design_reference':'../ConceptV4/faceted-double-spike-design.png','revision':'PointedHammerV1','tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
(P/'interfaces.json').write_text(json.dumps({'original_mounts':'SteelWarhammer20261014/ModulesV1/interfaces.json','new_neck_boundaries':interfaces},indent=2),encoding='utf-8')
print('POINTED_HAMMER_AUTHORED',json.dumps(receipts,ensure_ascii=False))
