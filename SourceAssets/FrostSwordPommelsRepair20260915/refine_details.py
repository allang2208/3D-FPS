"""Reconstruct the reference rune inlay and use clean glass surface normals."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon
P=Path(__file__).parent;KEY=sys.argv[sys.argv.index('--')+1];OUT=P/KEY
bpy.ops.wm.open_mainfile(filepath=str(OUT/'FrostPommel_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
obj=bpy.data.objects['SM_FrostPommel_'+KEY];data=obj.data
report=json.loads((OUT/'authoring.json').read_text())
if KEY=='ballast_magic_orb':
    mat=next(m for m in data.materials if 'FrostPommel_Crystal' in m.name)
    bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    for link in list(bsdf.inputs['Normal'].links):mat.node_tree.links.remove(link)
    report['crystal_surface']='zero metallic, blade blue, no invalid tangent normal bake on the glass'
if KEY=='ballast_rune':
    # Align a broad lobe with the reference front, leaving the stock mount fixed.
    data.calc_loop_triangles()
    tree=BVHTree.FromPolygons([v.co for v in data.vertices],[t.vertices for t in data.loop_triangles],all_triangles=True)
    zmid=(min(v.co.z for v in data.vertices)-.014)/2
    choices=[]
    for i in range(181):
        theta=-math.pi/2-math.pi/4+math.pi/2*i/180
        radial=Vector((math.cos(theta),math.sin(theta),0))
        hit,normal,index,distance=tree.ray_cast(radial*.12+Vector((0,0,zmid)),-radial,.12)
        if hit:choices.append((Vector((hit.x,hit.y,0)).length,theta))
    rotation=-math.pi/2-max(choices)[1]
    normals=[n.vector.copy() for n in data.corner_normals]
    for v in data.vertices:
        t=max(0,min(1,(-v.co.z-.004)/.010));angle=rotation*t*t*(3-2*t)
        v.co=Matrix.Rotation(angle,3,'Z')@v.co
    for loop in data.loops:
        z=data.vertices[loop.vertex_index].co.z;t=max(0,min(1,(-z-.004)/.010))
        normals[loop.index]=Matrix.Rotation(rotation*t*t*(3-2*t),3,'Z')@normals[loop.index]
    data.update();data.normals_split_custom_set(normals)
    data.calc_loop_triangles();tree=BVHTree.FromPolygons([v.co for v in data.vertices],[t.vertices for t in data.loop_triangles],all_triangles=True)
    # Polygon outlines traced from the original front panel: fork, branches,
    # center diamond and lower fork. These are editable physical inlay surfaces.
    paths=[[(291,305),(291,367),(302,383),(314,367),(314,306),(334,328),(334,381),(314,408),(314,438),(423,533),(423,508),(451,537),(437,552),(426,541),(426,574),(307,465),(293,465),(174,574),(174,541),(162,553),(145,536),(174,507),(174,533),(283,438),(283,408),(264,382),(264,328)],
           [(301,478),(321,499),(310,515),(310,582),(328,611),(328,666),(315,682),(315,620),(303,601),(291,620),(291,682),(276,666),(276,612),(294,584),(294,516),(282,503),(281,497)]]
    depth=-min(v.co.z for v in data.vertices)
    def planar(poly):return [Vector(((x-300)*.070/550,-.014-(y-260)/455*(depth-.014),0)) for x,y in poly]
    def expanded(poly,d):
        signed=sum(a.x*b.y-b.x*a.y for a,b in zip(poly,poly[1:]+poly[:1]));out=[]
        for i,p in enumerate(poly):
            e0=(p-poly[i-1]).normalized();e1=(poly[(i+1)%len(poly)]-p).normalized()
            n0=Vector((e0.y,-e0.x,0))*(1 if signed>0 else -1);n1=Vector((e1.y,-e1.x,0))*(1 if signed>0 else -1)
            bis=(n0+n1).normalized();offset=bis*min(d*3,d/max(.25,bis.dot(n0)));out.append(p+offset)
        return out
    def material(name,color,metallic,rough,emission=0):
        m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF')
        b.inputs['Base Color'].default_value=(*color,1);b.inputs['Metallic'].default_value=metallic;b.inputs['Roughness'].default_value=rough
        b.inputs['Emission Color'].default_value=(*color,1);b.inputs['Emission Strength'].default_value=emission;return m
    silver=material('M_FrostPommel_SilverInlay',(.75,.83,.90),.25,.24,.60)
    border=material('M_FrostPommel_InlayBorder',(.15,.070,.023),.82,.40)
    made=[]
    for side in [-1,1]:
        for kind,mat,offset,width in [('Border',border,.00010,.00050),('Silver',silver,.00019,0)]:
            verts=[];faces=[];lookup={};ns=[]
            def project(p):
                key=(round(p.x,8),round(p.y,8))
                if key in lookup:return lookup[key]
                origin=Vector((p.x,side*.15,p.y));hit,n,idx,d=tree.ray_cast(origin,Vector((0,-side,0)),.15)
                if hit is None:raise RuntimeError('Rune point lies outside the generated lobe: '+str(p))
                at=len(verts);lookup[key]=at;verts.append(hit+n*offset);ns.append(n);return at
            def emit(tri):
                if max((tri[i]-tri[(i+1)%3]).length for i in range(3))>.0010:
                    a,b,c=tri;ab=(a+b)*.5;bc=(b+c)*.5;ca=(c+a)*.5
                    for child in [(a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)]:emit(child)
                    return
                ids=[project(p) for p in tri]
                a,b,c=[verts[i] for i in ids]
                if (b-a).cross(c-a).y*side<0:ids.reverse()
                faces.append(ids)
            for path in paths:
                poly=planar(path)
                if width:poly=expanded(poly,width)
                for tri in tessellate_polygon([poly]):emit([poly[i] for i in tri])
            mesh=bpy.data.meshes.new('Reference_'+kind);mesh.from_pydata(verts,[],faces);mesh.materials.append(mat);mesh.update()
            uv=mesh.uv_layers.new(name='UVMap')
            for f in mesh.polygons:
                f.use_smooth=True
                for i in f.loop_indices:
                    p=mesh.vertices[mesh.loops[i].vertex_index].co;uv.data[i].uv=(p.x/.070+.5,-p.z/depth)
            mesh.normals_split_custom_set([ns[l.vertex_index] for l in mesh.loops])
            part=bpy.data.objects.new('Rune'+kind+str(side),mesh);bpy.context.collection.objects.link(part);made.append(part)
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    for part in made:part.select_set(True)
    bpy.ops.object.join()
    report['rune_reconstruction']={'source':'original three_views.png front panel','method':'fork branches and diamond traced as conforming silver inlay geometry, front and back','body_rotation_degrees':math.degrees(rotation),'geometry':'continuous on the generated lobed body; original mounting rim retained'}
bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FrostPommel_Editable.blend'))
report['final_triangles']=sum(len(f.vertices)-2 for f in obj.data.polygons)
report['final_material_faces']={m.name:sum(f.material_index==i for f in obj.data.polygons) for i,m in enumerate(obj.data.materials)}
(OUT/'authoring.json').write_text(json.dumps(report,indent=2));print('DETAILS_REBUILT',KEY,flush=True)
