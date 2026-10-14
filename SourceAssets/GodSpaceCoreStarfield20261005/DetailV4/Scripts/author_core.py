"""Two-ring starfield core. Exact legacy pivot, center, orientation and sphere radius."""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector,Euler,Matrix
ROOT=Path(__file__).resolve().parents[1] if Path(__file__).parent.name=='Scripts' else Path(__file__).parent
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
C=Vector((0,28.6,5.));created=[];ring_objects=[]
def material(name,col,metal=0,rough=.3,texture=None):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    if texture:
        t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(OUT/'Textures'/texture));m.node_tree.links.new(t.outputs['Color'],p.inputs['Base Color'])
    return m
star=material('Core_Starfield',(.008,.018,.065),.05,.19,'T_CoreStarfield_BaseColor.png')
gold=material('Core_EngravedGold',(.58,.36,.14),.9,.29,'T_CoreGold_BaseColor.png')
gem=material('Core_Sapphire',(.004,.085,.36),.1,.12)
# Dense smooth sphere; spherical UV is recreated after merging, independent of old planar export UV.
bpy.ops.mesh.primitive_uv_sphere_add(segments=160,ring_count=80,radius=1.5,location=C)
sphere=bpy.context.object;sphere.name='Core_StarfieldSphere_3m';sphere.data.materials.append(star)
sphere.data.uv_layers[0].name='SurfaceUV'
for p in sphere.data.polygons:p.use_smooth=True
created.append(sphere)
def mesh(name,vertices,faces,mat,uvs=None):
    m=bpy.data.meshes.new(name);m.from_pydata(vertices,[],faces);m.update();o=bpy.data.objects.new(name,m);s.collection.objects.link(o);o.data.materials.append(mat)
    bm=bmesh.new();bm.from_mesh(m);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(m);bm.free()
    layer=m.uv_layers.new(name='SurfaceUV')
    for p in m.polygons:
        for li in p.loop_indices:layer.data[li].uv=uvs[m.loops[li].vertex_index] if uvs else (.5,.5)
    for p in m.polygons:p.use_smooth=True
    created.append(o);ring_objects.append(o);return o
def band(name,r,w,t,euler):
    # Rounded closed band: 6.4/4.6 cm radial breadth, 2.4/2.0 cm axial thickness.
    rot=Euler(euler).to_matrix();bevel=.0015
    section=[(w-bevel,t),(-w+bevel,t),(-w,t-bevel),(-w,-t+bevel),(-w+bevel,-t),(w-bevel,-t),(w,-t+bevel),(w,t-bevel)]
    N=640;verts=[];uv=[]
    for i in range(N+1):
        a=2*math.pi*i/N;er=Vector((math.cos(a),math.sin(a),0))
        for rr,zz in section:
            verts.append(C+rot@(er*(r+rr)+Vector((0,0,zz))));uv.append((i/N*32,(rr/w+1)*.5))
    faces=[]
    for i in range(N):
        for j in range(8):faces.append((i*8+j,i*8+(j+1)%8,(i+1)*8+(j+1)%8,(i+1)*8+j))
    o=mesh(name,verts,faces,gold,uv)
    # Preserve geometry; unwrap cross-section by actual arclength, including sidewalls.
    lengths=[math.hypot(section[(j+1)%8][0]-section[j][0],section[(j+1)%8][1]-section[j][1]) for j in range(8)]
    arc=[0.0]
    for length in lengths:arc.append(arc[-1]+length)
    for poly in o.data.polygons:
        indices=[o.data.loops[li].vertex_index%8 for li in poly.loop_indices]
        seam=0 in indices and 7 in indices
        for li in poly.loop_indices:
            idx=o.data.loops[li].vertex_index;j=idx%8
            cross=arc[8] if seam and j==0 else arc[j]
            o.data.uv_layers.active.data[li].uv=(idx//8/N*32,cross/(2*w))

    # Sparse inset sapphire markers, four on each face, with fitted gold bezels.
    for face in [-1,1]:
        for k in range(4):
            a=2*math.pi*(k/4+.0625);er=Vector((math.cos(a),math.sin(a),0));et=Vector((-math.sin(a),math.cos(a),0));ez=Vector((0,0,1));p0=C+rot@(er*r+ez*(face*(t+.0004)))
            rw=.017 if name.endswith('A') else .014;rl=.024
            verts=[];faces=[]
            for i in range(32):
                a2=2*math.pi*i/32
                for rr,hh in [(1.15,0),(1.15,.005),(1,.006),(1,.001)]:verts.append(p0+rot@(er*(math.cos(a2)*rw*rr)+et*(math.sin(a2)*rl*rr)+ez*(face*hh)))
            for i in range(32):
                for j in range(4):faces.append((i*4+j,((i+1)%32)*4+j,((i+1)%32)*4+(j+1)%4,i*4+(j+1)%4))
            bezel=mesh(name+'_Bezel_'+str(k)+'_'+str(face),verts,faces,gold)
            for poly in bezel.data.polygons:
                indices=[bezel.data.loops[li].vertex_index for li in poly.loop_indices]
                seam=any(i//4==0 for i in indices) and any(i//4==31 for i in indices)
                for li in poly.loop_indices:
                    idx=bezel.data.loops[li].vertex_index;angle=idx//4
                    if seam and angle==0:angle=32
                    # Small bezel gets a dedicated unwrapped cross-section, no constant-UV faces.
                    j=idx%4;cs=[0.,.16,.23,.40]
                    wrap=0 in [v%4 for v in indices] and 3 in [v%4 for v in indices]
                    bezel.data.uv_layers.active.data[li].uv=(angle/32*.15,.55 if wrap and j==0 else cs[j])

            # Closed faceted cabochon, domed top with no detached floating jewels.
            verts=[];faces=[];NN=32;rows=[(1.,.002),(.88,.009),(.52,.013),(.001,.014)]
            for rr,hh in rows:
                for i in range(NN):
                    a2=2*math.pi*i/NN;verts.append(p0+rot@(er*(math.cos(a2)*rw*rr)+et*(math.sin(a2)*rl*rr)+ez*(face*hh)))
            for j in range(len(rows)-1):
                for i in range(NN):faces.append((j*NN+i,j*NN+(i+1)%NN,(j+1)*NN+(i+1)%NN,(j+1)*NN+i))
            faces.extend([tuple(reversed(range(NN))),tuple((len(rows)-1)*NN+i for i in range(NN))]);mesh(name+'_Sapphire_'+str(k)+'_'+str(face),verts,faces,gem)
    return o
band('OrbitBand_A',2.15,.032,.012,(math.pi/2,.4,0))
band('OrbitBand_B',2.35,.023,.010,(.5,.25,0))
# Keep all ring detail inside the existing union AABB; do not resize the 3 m sphere.
contract=Vector((1.0*2.3182497406,2.086307373,2.184941864))
maximum=Vector((0,0,0))
for o in ring_objects:
    for v in o.data.vertices:
        d=o.matrix_world@v.co-C
        for axis in range(3):maximum[axis]=max(maximum[axis],abs(d[axis]))
fit=min(1.,*(contract[i]/maximum[i] for i in range(3)))
for o in ring_objects:
    for v in o.data.vertices:v.co=C+(v.co-C)*fit
bpy.context.view_layer.update()
# Package editable source with texture bytes; save before producing reflected FBX copy.
for img in bpy.data.images:
    if img.source=='FILE':img.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GodSpaceCore_BaseGeometry.blend'))
bpy.ops.object.select_all(action='DESELECT')
for o in created:o.select_set(True)
bpy.context.view_layer.objects.active=sphere;bpy.ops.object.join();o=bpy.context.object;o.name='SM_GodSpaceCore_Starfield_V4'
o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
# Rebuild proper spherical UV only on sphere material; keep ring strips' longitudinal UV.
uv=o.data.uv_layers.active or o.data.uv_layers.new(name='SurfaceUV')
assert len(o.data.uv_layers)==1 and uv.name=='SurfaceUV'
for p in o.data.polygons:
    if o.data.materials[p.material_index]!=star:continue
    coords=[]
    for li in p.loop_indices:
        d=(o.data.vertices[o.data.loops[li].vertex_index].co-C).normalized();coords.append([(math.atan2(d.y,d.x)+math.pi)/(2*math.pi),(math.asin(max(-1,min(1,d.z)))+math.pi/2)/math.pi])
    us=[a[0] for a in coords]
    if max(us)-min(us)>.5:
        for a in coords:
            if a[0]<.5:a[0]+=1
    for li,a in zip(p.loop_indices,coords):uv.data[li].uv=a
counts={m.name:sum(len(p.vertices)-2 for p in o.data.polygons if o.data.materials[p.material_index]==m) for m in o.data.materials}
bb=[v.co.copy() for v in o.data.vertices];lo=[min(v[i] for v in bb)*100 for i in range(3)];hi=[max(v[i] for v in bb)*100 for i in range(3)]
assert abs((lo[1]+hi[1])/2-2860)<.05 and abs((lo[2]+hi[2])/2-500)<.05
o.data.transform(Matrix.Diagonal((1,-1,1,1)))
for p in o.data.polygons:p.flip()
fbx=OUT/'SM_GodSpaceCore_Starfield_V4.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',add_leaf_bones=False)
report={'fbx':str(fbx),'sphere_diameter_cm':300,'ring_count':2,'ring_uniform_fit':fit,'bounds_cm_before_export_reflection':{'min':lo,'max':hi},'legacy_pivot_cm':[0,0,0],'legacy_center_cm':[0,2860,500],'legacy_extent_cm':list(contract*100),'material_triangles':counts,'triangles':sum(counts.values()),'objects_before_merge':len(created),'sapphire_markers':16,'concept_added_supports':False}
(OUT/'model_receipt.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
