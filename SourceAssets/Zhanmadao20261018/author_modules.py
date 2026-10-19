"""Split the fitted source at its real fittings and export unchanged UV/PBR parts."""
import bpy, bmesh, json
from pathlib import Path
from mathutils import Vector

P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Zhanmadao_Fitted_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
whole=bpy.data.objects['SM_Zhanmadao_Complete_V1']
data=whole.data
data.calc_loop_triangles()
uv=data.uv_layers[0].data
normals=[n.vector.copy() for n in data.corner_normals]
manifest=json.loads((P/'fit_manifest.json').read_text(encoding='utf-8'))
cuts={k:v/100 for k,v in manifest['cuts_z_cm'].items()}

def clip(poly,z,above):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[0].z-z)*(1 if above else -1);db=(b[0].z-z)*(1 if above else -1)
        if da>=0:out.append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);out.append(tuple(x.lerp(y,t) for x,y in zip(a,b)))
    return out

parts=[]
for slot,label,lo,hi,pivot in [
    ('blade_1','Blade',cuts['blade_guard'],2,Vector()),
    ('guard','Guard',cuts['guard_grip'],cuts['blade_guard'],Vector()),
    ('grip','Grip',cuts['grip_pommel'],cuts['guard_grip'],Vector((0,0,cuts['guard_grip']))),
    ('pommel','Pommel',-2,cuts['grip_pommel'],Vector((0,0,cuts['grip_pommel']))),
]:
    verts=[];faces=[];corners=[]
    for tri in data.loop_triangles:
        zs=[data.vertices[i].co.z for i in tri.vertices]
        if max(zs)<lo or min(zs)>hi:continue
        poly=[(data.vertices[data.loops[i].vertex_index].co.copy(),uv[i].uv.copy(),normals[i].copy()) for i in tri.loops]
        poly=clip(poly,lo,True)
        if poly:poly=clip(poly,hi,False)
        for k in range(1,len(poly)-1):
            triangle=[poly[0],poly[k],poly[k+1]]
            if (triangle[1][0]-triangle[0][0]).cross(triangle[2][0]-triangle[0][0]).length<1e-12:continue
            face=[]
            for co,tex,normal in triangle:
                face.append(len(verts));verts.append(co-pivot);corners.append((tex,normal))
            faces.append(face)
    name='SM_Zhanmadao_'+label+'_V1'
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(data.materials[0]);mesh.update()
    layer=mesh.uv_layers.new(name='UVMap');attr=mesh.attributes.new('AuthoredNormal','FLOAT_VECTOR','CORNER')
    for face in mesh.polygons:
        face.use_smooth=True
        for li in face.loop_indices:
            tex,normal=corners[mesh.loops[li].vertex_index];layer.data[li].uv=tex;attr.data[li].vector=normal
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.0000001)
    edges=[e for e in bm.edges if e.is_boundary and any(all(abs(v.co.z-(z-pivot.z))<2e-6 for v in e.verts) for z in [lo,hi])]
    if edges:
        filled=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']
        nl=bm.loops.layers.float_vector['AuthoredNormal'];ul=bm.loops.layers.uv[0]
        for face in filled:
            face.smooth=False;face.normal_update()
            adjacent=next((rad[ul].uv.copy() for loop in face.loops for rad in [loop.link_loop_radial_next] if rad.face!=face),Vector((.5,.5)))
            for loop in face.loops:loop[nl]=face.normal;loop[ul].uv=adjacent
    bm.to_mesh(mesh);bm.free();mesh.update()
    mesh.normals_split_custom_set([tuple(n.vector.normalized()) for n in mesh.attributes['AuthoredNormal'].data])
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);obj.location=pivot
    parts.append({'slot':slot,'mesh':name,'location_cm':[float(x*100) for x in pivot],
                  'triangles':sum(len(f.vertices)-2 for f in mesh.polygons)})

def export(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    loc=obj.location.copy();obj.location=Vector()
    bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    obj.location=loc

for row in parts:export(bpy.data.objects[row['mesh']])
export(whole);whole.hide_render=True;whole.hide_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Zhanmadao_Modular_Editable.blend'))
manifest.update(ue_root='/Game/Weapons/Zhanmadao20261018/V1',parts=parts,world_mesh=whole.name,
                animation_policy='Direct shared two-handed sword animations; original clocks and native bare-arm profile',
                mesh_policy='No decimation; preserve the user-selected source silhouette, UV and PBR')
tip=max((v.co for v in whole.data.vertices),key=lambda p:p.z)
base_band=[v.co for v in whole.data.vertices if cuts['blade_guard']<=v.co.z<=cuts['blade_guard']+.003]
base=Vector(tuple((min(v[i] for v in base_band)+max(v[i] for v in base_band))*.5 for i in range(3)))
base.z=cuts['blade_guard']
manifest['trace_base_cm']=[float(v*100) for v in base]
manifest['trace_tip_cm']=[float(v*100) for v in tip]
(P/'exports.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ZHANMADAO_MODULES_EXPORTED',flush=True)
