"""Repair the generated mother before reduction; author three closed timber meshes."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).parent;OUT=ROOT/'SolidRepair'/'Delivery';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'HarvestTimber_Editable.blend'))
master=bpy.data.objects['Poplar_GeneratedMother'];master.hide_set(False);master.hide_render=False
low=master.copy();low.data=master.data.copy();bpy.context.collection.objects.link(low);low.name='Timber_WeldedLow'
low.hide_set(False);low.hide_render=False
bm=bmesh.new();bm.from_mesh(master.data)
source={'vertices':len(bm.verts),'boundary_edges':sum(e.is_boundary for e in bm.edges)}
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-4)
source['welded_boundary_edges']=sum(e.is_boundary for e in bm.edges)
surface=BVHTree.FromBMesh(bm)
# The mother retains small non-manifold cracks even after a weld. Reconstruct
# one continuous quad surface against its outer shape instead of filling shards.
segments=96;rings=33;radius=[]
for j in range(rings):
    z=.84*j/(rings-1);row=[]
    for i in range(segments):
        angle=2*math.pi*i/segments;direction=Vector((math.cos(angle),math.sin(angle),0))
        point,_,_,_=surface.ray_cast(direction*.3+Vector((0,0,max(.008,min(.832,z)))),-direction,.6)
        r=Vector((point.x,point.y)).length if point is not None else .15
        row.append(max(.11,min(.175,r)))
    radius.append([.6*row[i]+.2*row[(i-1)%segments]+.2*row[(i+1)%segments] for i in range(segments)])
bm.free();verts=[];faces=[]
for j,row in enumerate(radius):
    for i,r in enumerate(row):
        a=2*math.pi*i/segments;verts.append((r*math.cos(a),r*math.sin(a),.84*j/(rings-1)))
for j in range(rings-1):
    for i in range(segments):
        k=(i+1)%segments;faces.append((j*segments+i,j*segments+k,(j+1)*segments+k,(j+1)*segments+i))
mesh=bpy.data.meshes.new('ContinuousTimberSurface');mesh.from_pydata(verts,[],faces);mesh.update();low.data=mesh
uv=mesh.uv_layers.new(name='UVMap')
for face in mesh.polygons:
    j,i=divmod(face.index,segments);face.use_smooth=True
    coords=[(i/segments,j/(rings-1)),((i+1)/segments,j/(rings-1)),((i+1)/segments,(j+1)/(rings-1)),(i/segments,(j+1)/(rings-1))]
    for loop,coord in zip(face.loop_indices,coords):uv.data[loop].uv=(.02+.96*coord[0],.02+.96*coord[1])
target_material=master.data.materials[0].copy();low.data.materials.append(target_material)
# Rebake the mother's appearance onto a single continuous cylindrical UV layout.
target=target_material.node_tree.nodes.new('ShaderNodeTexImage');target_material.node_tree.nodes.active=target
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.device='CPU'
scene.render.threads_mode='FIXED';scene.render.threads=10
scene.render.bake.use_selected_to_active=True;scene.render.bake.max_ray_distance=.035
scene.render.bake.cage_extrusion=.015;scene.render.bake.margin=12
bpy.ops.object.select_all(action='DESELECT');master.select_set(True);low.select_set(True);bpy.context.view_layer.objects.active=low
master.hide_set(False);low.hide_set(False)
textures={}
for kind,bake in [('BaseColor','DIFFUSE'),('Roughness','ROUGHNESS'),('Normal','NORMAL')]:
    image=bpy.data.images.new('T_PoplarSolid_'+kind,width=2048,height=2048,alpha=False)
    if kind!='BaseColor':image.colorspace_settings.name='Non-Color'
    target.image=image
    scene.render.bake.use_pass_direct=False;scene.render.bake.use_pass_indirect=False;scene.render.bake.use_pass_color=True
    bpy.ops.object.bake(type=bake)
    image.filepath_raw=str(OUT/('T_PoplarSolid_'+kind+'.png'));image.file_format='PNG';image.save();textures[kind]=image
bark=bpy.data.materials.new('TimberSolidBark');bark.use_nodes=True
bsdf=next(n for n in bark.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
for kind,socket in [('BaseColor','Base Color'),('Roughness','Roughness')]:
    tex=bark.node_tree.nodes.new('ShaderNodeTexImage');tex.image=textures[kind];bark.node_tree.links.new(tex.outputs['Color'],bsdf.inputs[socket])
tex=bark.node_tree.nodes.new('ShaderNodeTexImage');tex.image=textures['Normal']
nm=bark.node_tree.nodes.new('ShaderNodeNormalMap');bark.node_tree.links.new(tex.outputs['Color'],nm.inputs['Color']);bark.node_tree.links.new(nm.outputs['Normal'],bsdf.inputs['Normal'])
cap=bpy.data.materials['TimberEndGrain'].copy();cap.name='TimberSolidEndGrain'
report={'mother':source,'meshes':{}}
for kind,bottom,top,diameter,twist in [('A',.02,.82,.31,0),('B',.04,.77,.29,.07),('C',.025,.815,.34,-.05)]:
    obj=low.copy();obj.data=low.data.copy();bpy.context.collection.objects.link(obj);obj.name='SM_PoplarLog_Solid_'+kind
    obj.data.materials.clear();obj.data.materials.append(bark);obj.data.materials.append(cap)
    bm=bmesh.new();bm.from_mesh(obj.data)
    for cut,lower in [(bottom,True),(top,False)]:
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,
            plane_co=(0,0,cut),plane_no=(0,0,1),clear_inner=lower,clear_outer=not lower)
        edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-cut)<1e-5 for v in e.verts)]
        filled=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']
        if not filled:raise RuntimeError('Missing end cap '+kind)
        uv=bm.loops.layers.uv.verify()
        for face in filled:
            face.material_index=1;face.smooth=False
            for loop in face.loops:loop[uv].uv=(.5+loop.vert.co.x/.31,.5+loop.vert.co.y/.31)
    for v in bm.verts:
        t=(v.co.z-bottom)/(top-bottom);angle=twist*t;x,y=v.co.x,v.co.y
        v.co.x=(x*math.cos(angle)-y*math.sin(angle))*diameter/.31
        v.co.y=(x*math.sin(angle)+y*math.cos(angle))*diameter/.31
        v.co.z-=bottom
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if any(not e.is_manifold for e in bm.edges):raise RuntimeError('Timber is not closed '+kind)
    caps=[f for f in bm.faces if f.material_index==1]
    if len(caps)!=2:raise RuntimeError('Expected two complete caps '+kind)
    # Explicit triangles avoid exporter-specific n-gon tessellation.
    bmesh.ops.triangulate(bm,faces=caps,quad_method='BEAUTY',ngon_method='BEAUTY')
    report['meshes'][obj.name]={'triangles':sum(len(f.verts)-2 for f in bm.faces),
        'boundary_edges':sum(e.is_boundary for e in bm.edges),'signed_volume_m3':bm.calc_volume(signed=True)}
    bm.to_mesh(obj.data);bm.free()
    obj.data.transform(Matrix.Rotation(math.pi/2,4,'Y'))
    for v in obj.data.vertices:v.co.x-=(top-bottom)*.5
    obj.data.update()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
        apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
    report['meshes'][obj.name]['dimensions_m']=list(obj.dimensions)
master.hide_set(True);low.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT.parent/'SolidTimber_Editable.blend'))
(OUT/'authoring.json').write_text(json.dumps(report,indent=2))
print('SOLID_TIMBER_AUTHORED',json.dumps(report),flush=True)
