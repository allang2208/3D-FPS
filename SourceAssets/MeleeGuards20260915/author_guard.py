"""Fit generated quillons to the original V saddle; preserve blade, grip and rig."""
import bpy,bmesh,json,sys,math
import numpy as np
from pathlib import Path
from collections import Counter,defaultdict
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent
ID=sys.argv[sys.argv.index('--')+1]
OUT=P/ID
SOURCE=P.parent/'MeshyMelee20260915/FrostCrystalSword_Manny_Editable.blend'
spec=json.loads((P/'mount_source.json').read_text())
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P/'OriginalGuardReference.blend'))
original=bpy.data.objects['FrostCrystalSword_Blade'];original.data.update()
old=original.data
old_normals=[n.vector.copy() for n in old.corner_normals]
guard_faces=set(spec['guard_faces']);retained=set(spec['retained_guard_faces'])

def subset(name,face_ids):
    indices=sorted(set(v for fi in face_ids for v in old.polygons[fi].vertices));mapping={v:i for i,v in enumerate(indices)}
    faces=[old.polygons[i] for i in face_ids]
    data=bpy.data.meshes.new(name)
    data.from_pydata([old.vertices[i].co[:] for i in indices],[],[[mapping[i] for i in f.vertices] for f in faces]);data.update()
    data.materials.append(old.materials[0])
    uv=data.uv_layers.new(name='UVMap');normals=[]
    for src,dst in zip(faces,data.polygons):
        dst.use_smooth=src.use_smooth
        for a,b in zip(src.loop_indices,dst.loop_indices):
            uv.data[b].uv=old.uv_layers.active.data[a].uv;normals.append(old_normals[a])
    data.normals_split_custom_set(normals)
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    return obj

outer_faces=set()
for f in old.polygons:
    c=sum((old.vertices[v].co for v in f.vertices),Vector())/len(f.vertices)
    if abs(c.x)>.060 and -.048<c.z<.065:outer_faces.add(f.index)
body=subset('FrostCrystalSword_Blade',[f.index for f in old.polygons if f.index not in outer_faces])
# The combined Meshy asset encodes the bronze/crystal boundary in its texture.
# Cut the icon's isolated saddle at that boundary, not at triangle centroids.
# The assembled sword keeps the unmodified central geometry in `body`.
def isolate_saddle():
    texture=next(n.image for n in old.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and not any(s in n.image.name for s in ['normal','metallic','roughness']))
    pixels=np.empty(len(texture.pixels),np.float32);texture.pixels.foreach_get(pixels)
    w,h=texture.size;pixels=pixels.reshape((h,w,4))
    def density(uv):
        r,g,b=pixels[min(h-1,max(0,int(uv.y*h))),min(w-1,max(0,int(uv.x*w))),:3]
        return min(float(r-g*1.10),float(r-b*1.20))
    verts=[];faces=[];uvs=[];normals=[]
    def emit(tri):
        samples=[(*v,density(v[1])) for v in tri];poly=[]
        for a,b in zip(samples,samples[1:]+samples[:1]):
            if a[3]>=0:poly.append(a[:3])
            if (a[3]>=0)!=(b[3]>=0):
                t=a[3]/(a[3]-b[3]);poly.append(tuple(a[k].lerp(b[k],t) for k in range(3)))
        for i in range(1,len(poly)-1):
            face=[]
            for p,uv,n in [poly[0],poly[i],poly[i+1]]:
                face.append(len(verts));verts.append(p);uvs.append(uv);normals.append(n.normalized())
            faces.append(face)
    def divide(tri,depth):
        if depth==0:return emit(tri)
        a,b,c=tri
        ab=tuple(a[k].lerp(b[k],.5) for k in range(3));bc=tuple(b[k].lerp(c[k],.5) for k in range(3));ca=tuple(c[k].lerp(a[k],.5) for k in range(3))
        for t in [(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]:divide(t,depth-1)
    for f in old.polygons:
        center=sum((old.vertices[v].co for v in f.vertices),Vector())/3
        if f.index in outer_faces or not -.034<center.z<.055:continue
        tri=[(old.vertices[old.loops[i].vertex_index].co.copy(),old.uv_layers.active.data[i].uv.copy(),old_normals[i]) for i in f.loop_indices]
        density_values=[density(v[1]) for v in tri]
        if min(density_values)>=0:emit(tri)
        elif max(density_values)>=0:divide(tri,3)
    data=bpy.data.meshes.new('Original bronze saddle isolated along texture edge');data.from_pydata(verts,[],faces);data.update()
    data.materials.append(old.materials[0]);uv=data.uv_layers.new(name='UVMap')
    for f in data.polygons:
        f.use_smooth=True
        for i in f.loop_indices:uv.data[i].uv=uvs[data.loops[i].vertex_index]
    data.normals_split_custom_set(normals)
    obj=bpy.data.objects.new('Retained_Original_V_Saddle',data);bpy.context.collection.objects.link(obj)
    return obj
collar=isolate_saddle()
original.hide_render=True;original.hide_set(True)

def key(v):return tuple(round(c,6) for c in v)
def ring(mesh,sign,cut=None):
    # Use physical edge positions so UV seam duplicates do not break the loop.
    counts=Counter();positions={}
    for f in mesh.polygons:
        ids=list(f.vertices)
        for a,b in zip(ids,ids[1:]+ids[:1]):
            ka,kb=key(mesh.vertices[a].co),key(mesh.vertices[b].co)
            positions[ka]=mesh.vertices[a].co.copy();positions[kb]=mesh.vertices[b].co.copy()
            counts[tuple(sorted((ka,kb)))]+=1
    edges=[]
    for (a,b),n in counts.items():
        if n!=1:continue
        if cut is None:
            include=sign*positions[a].x>.055 and sign*positions[b].x>.055
        else:include=abs(positions[a].x-sign*cut)<.00002 and abs(positions[b].x-sign*cut)<.00002
        if include:edges.append((a,b))
    graph=defaultdict(list)
    for a,b in edges:graph[a].append(b);graph[b].append(a)
    if not graph:raise RuntimeError('No mount boundary for '+str(sign))
    if cut is None:
        pts=[positions[k] for k in graph]
        center=Vector(tuple((min(p[a] for p in pts)+max(p[a] for p in pts))/2 for a in range(3)))
        return pts,center
    loops=[];remaining=set(graph)
    while remaining:
        start=next(iter(remaining));ordered=[start];previous=None;current=start
        for _ in range(len(graph)+1):
            options=[v for v in graph[current] if v!=previous]
            if not options:break
            nxt=options[0]
            if nxt==start:break
            if nxt in ordered:break
            ordered.append(nxt);previous,current=current,nxt
        remaining.difference_update(ordered);loops.append(ordered)
    chosen=max(loops,key=len)
    pts=[positions[k] for k in chosen]
    center=sum(pts,Vector())/len(pts)
    # A monotonic section-angle ordering gives a consistent seam winding.
    pts.sort(key=lambda p:math.atan2(p.z-center.z,p.y-center.y))
    return pts,center

stock_rings={s:ring(body.data,s) for s in (-1,1)}
before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(OUT/'textured_master_00001_.glb'))
generated=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in generated:o.select_set(True)
bpy.context.view_layer.objects.active=generated[0]
if len(generated)>1:bpy.ops.object.join()
master=bpy.context.object
master.data.transform(master.matrix_world);master.matrix_world=Matrix.Identity(4)
master.name='TRELLIS_Textured_Master'
coords=[v.co for v in master.data.vertices]
minimum=Vector(tuple(min(p[a] for p in coords) for a in range(3)))
maximum=Vector(tuple(max(p[a] for p in coords) for a in range(3)))
size=maximum-minimum;center=(minimum+maximum)/2
span={'bastion_guard':.24,'riposte_guard':.24,'light_guard':.228}[ID]
height={'bastion_guard':.085,'riposte_guard':.115,'light_guard':.074}[ID]
depth={'bastion_guard':.047,'riposte_guard':.042,'light_guard':.040}[ID]
for v in master.data.vertices:
    p=v.co-center
    v.co=(p.x*span/size.x,p.y*depth/size.y,p.z*height/size.z)
master.data.update()

sys.path.insert(0,str(P))
from retopology_guard import build_guard
profile=json.loads((OUT/'retopology_profile.json').read_text())
high=build_guard(profile,stock_rings,ID,False)
low=build_guard(profile,stock_rings,ID,True)
# Transfer the actual stock quillon's bronze texture coordinates. This retains
# its patina and roughness variation across all three replacement assemblies.
finish=json.loads((P/'finish_patch.json').read_text())
def transfer_finish(obj):
    layer=obj.data.uv_layers.new(name='StockBronzeUV')
    zmin=min(v.co.z for v in obj.data.vertices);zmax=max(v.co.z for v in obj.data.vertices)
    xmax=max(abs(v.co.x) for v in obj.data.vertices)
    uvmin=Vector(finish['uv_min']);uvmax=Vector(finish['uv_max'])
    for f in obj.data.polygons:
        for li in f.loop_indices:
            p=obj.data.vertices[obj.data.loops[li].vertex_index].co
            u=min(1,max(0,(abs(p.x)-.055)/(xmax-.055)))
            v=min(1,max(0,(p.z-zmin)/(zmax-zmin)))
            layer.data[li].uv=(uvmin.x+u*(uvmax.x-uvmin.x),uvmin.y+v*(uvmax.y-uvmin.y))
low.data.uv_layers.new(name='BakeUV')
for obj in [high,low]:transfer_finish(obj)
for obj in [master,collar]:obj.hide_set(True);obj.hide_render=True
mat=bpy.data.materials.new('M_FrostGuard_Bronze_'+ID);mat.use_nodes=True
nodes=mat.node_tree.nodes;links=mat.node_tree.links
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
# Use an actual bronze swatch from the original guard, through the original
# texture nodes' color-space handling. All three guards share these values.
coord=nodes.new('ShaderNodeUVMap');coord.uv_map='StockBronzeUV'
for suffix,socket in [('texture','Base Color'),('metallic','Metallic'),('roughness','Roughness')]:
    old_nodes=[n for n in old.materials[0].node_tree.nodes if n.type=='TEX_IMAGE']
    image=next(n.image for n in old_nodes if (suffix in n.image.name if suffix!='texture' else not any(s in n.image.name for s in ['normal','metallic','roughness'])))
    n=nodes.new('ShaderNodeTexImage');n.image=image;links.new(coord.outputs['UV'],n.inputs['Vector']);links.new(n.outputs['Color'],bsdf.inputs[socket])
low.data.materials.clear();low.data.materials.append(mat)
high.data.materials.clear();high.data.materials.append(mat.copy())
bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
low.data.uv_layers.active_index=0
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.bake.use_selected_to_active=True;scene.render.bake.max_ray_distance=.0008;scene.render.bake.cage_extrusion=.0002;scene.render.bake.margin=12
scene.render.bake.use_clear=False
detail_uv=nodes.new('ShaderNodeUVMap');detail_uv.uv_map='BakeUV'
for obj in scene.objects:obj.hide_render=obj not in (low,high)
for kind in ['NORMAL','AO']:
    image=bpy.data.images.new('T_Guard_'+ID+'_'+kind,width=2048,height=2048,alpha=False)
    image.colorspace_settings.name='Non-Color';image.generated_color=(.5,.5,1,1) if kind=='NORMAL' else (1,1,1,1)
    n=nodes.new('ShaderNodeTexImage');n.image=image;nodes.active=n;links.new(detail_uv.outputs['UV'],n.inputs['Vector'])
    bpy.ops.object.select_all(action='DESELECT');high.select_set(True);low.select_set(True);bpy.context.view_layer.objects.active=low
    bpy.ops.object.bake(type=kind)
    image.filepath_raw=str(OUT/(kind.lower()+'.png'));image.file_format='PNG';image.save()
    if kind=='NORMAL':
        normal=nodes.new('ShaderNodeNormalMap');normal.uv_map='BakeUV';links.new(n.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bsdf.inputs['Normal'])
low.data.uv_layers.active_index=0
high.hide_render=True;high.hide_set(True)
collar.hide_render=False

# Produce the actual-model UI icon, using the shared bronze finish.
scene.render.bake.use_selected_to_active=False
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG'
for o in scene.objects:
    if o.type in {'LIGHT','CAMERA'}:o.hide_render=False
camera=scene.camera
guard_min=Vector(tuple(min(v.co[a] for v in low.data.vertices) for a in range(3)))
guard_max=Vector(tuple(max(v.co[a] for v in low.data.vertices) for a in range(3)))
target=(guard_min+guard_max)/2
camera.location=target+Vector((0,-2,0));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=max((guard_max-guard_min).x,(guard_max-guard_min).z)/.83
scene.render.filepath=str(OUT/'guard_icon.png');bpy.ops.render.render(write_still=True)

def export(path,objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[-1]
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},
       axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
export(OUT/('SM_Guard_'+ID+'.fbx'),[collar,low])
export(OUT/('SM_FrostCrystalSword_'+ID+'.fbx'),[body,low])
with bpy.data.libraries.load(str(SOURCE),link=False) as (src,dst):
    dst.objects=['SK_RuneSword_Rig','SK_Manny_Arms_Export']
for o in dst.objects:
    if o:o.hide_set(False);scene.collection.objects.link(o)
rig=bpy.data.objects['SK_RuneSword_Rig'];arms=bpy.data.objects['SK_Manny_Arms_Export']
rig.animation_data_clear();rig.data.pose_position='REST'
rest=rig.data.bones['WPN_root'].matrix_local.copy()
for o in [body,low]:
    o.data.transform(rest);o.parent=rig;o.matrix_parent_inverse=Matrix.Identity(4)
    o.vertex_groups.clear();g=o.vertex_groups.new(name='WPN_root');g.add(list(range(len(o.data.vertices))),1,'REPLACE')
    mod=o.modifiers.new('Rigid WPN_root binding','ARMATURE');mod.object=rig
export(OUT/('SK_FrostCrystalSword_'+ID+'.fbx'),[arms,body,low,rig])
for o in [body,low,arms,rig]:o.hide_render=False
for o in [master,high,collar,original]:o.hide_set(True);o.hide_render=True
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('FrostCrystalSword_'+ID+'_Editable.blend')))
(OUT/'authoring.json').write_text(json.dumps({'id':ID,'generated_master':str(OUT/'textured_master_00001_.glb'),
  'original_reference':str(SOURCE),'source_triangles':len(master.data.polygons),'guard_triangles':len(low.data.polygons),
  'guard_high_triangles':len(high.data.polygons),'mount_half_width_cm':6,
  'processing':'5080 surface projection -> local contour retopology and bevels -> original-interface root sleeves',
  'root_overlap_mm':3,'original_central_geometry_preserved':True,
  'blade_grip_body_triangles':len(body.data.polygons),'guard_bounds_cm':{'min':list(guard_min*100),'max':list(guard_max*100)},
  'material_sample_uv':spec['material_sample_uv'],'material':'UV1 stock bronze surface transfer; UV0 baked normal and AO with matching export tangents',
  'render_scope':'existing guard reference requested by user and actual-model inventory icon authoring only',
  'gameplay_testing':'Not run'},indent=2))
print('GUARD_ASSETS_AUTHORED',ID,flush=True)
