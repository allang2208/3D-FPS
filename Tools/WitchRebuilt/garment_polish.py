"""Clean the retained robe surface and weight hanging sleeves by their arm chain."""
import bpy,bmesh,math
from pathlib import Path
from mathutils import Vector

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3.-2.*t)

def fabric_material(o,name,texture_folder):
    m=bpy.data.materials.new(name);m.use_nodes=True;nodes=m.node_tree.nodes;nodes.clear();links=m.node_tree.links
    bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial');links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    for semantic in ('base_color','normal','roughness'):
        n=nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(Path(texture_folder)/('texture_urls_0_'+semantic+'.png')),check_existing=True)
        if semantic=='base_color':links.new(n.outputs['Color'],bs.inputs['Base Color'])
        elif semantic=='normal':
            n.image.colorspace_settings.name='Non-Color';normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.4
            links.new(n.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bs.inputs['Normal'])
        else:
            n.image.colorspace_settings.name='Non-Color';rough=nodes.new('ShaderNodeMath');rough.operation='MULTIPLY_ADD'
            rough.inputs[1].default_value=.25;rough.inputs[2].default_value=.65
            links.new(n.outputs['Color'],rough.inputs[0]);links.new(rough.outputs[0],bs.inputs['Roughness'])
    bs.inputs['Metallic'].default_value=0;bs.inputs['Specular IOR Level'].default_value=.28
    o.data.materials.clear();o.data.materials.append(m)

def clean(o):
    bm=bmesh.new();bm.from_mesh(o.data)
    before=(len(bm.verts),len(bm.faces))
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    bmesh.ops.dissolve_degenerate(bm,dist=.000001,edges=list(bm.edges))
    bm.verts.index_update();seen=set();duplicates=[]
    for f in bm.faces:
        key=tuple(sorted(v.index for v in f.verts))
        if key in seen or f.calc_area()<1e-11:duplicates.append(f)
        seen.add(key)
    if duplicates:bmesh.ops.delete(bm,geom=duplicates,context='FACES_ONLY')
    todo=set(bm.verts);components=[]
    while todo:
        v=todo.pop();part={v};stack=[v]
        while stack:
            for e in stack.pop().link_edges:
                for n in e.verts:
                    if n in todo:todo.remove(n);part.add(n);stack.append(n)
        faces={f for n in part for f in n.link_faces}
        components.append((sum(f.calc_area() for f in faces),part))
    components.sort(key=lambda x:-x[0])
    discarded=[v for _,part in components[1:] for v in part]
    if discarded:bmesh.ops.delete(bm,geom=discarded,context='VERTS')
    # The source already contains folded inner/outer surfaces. A second global
    # Solidify shell doubles those intersections; back faces use two-sided fabric.
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(o.data);bm.free();o.data.update()
    for p in o.data.polygons:p.use_smooth=True
    return {'before_vertices_faces':before,'after_vertices_faces':(len(o.data.vertices),len(o.data.polygons)),
            'removed_components':len(components)-1,'second_solidify_shell':False}

def mix(a,b,t):return {n:a.get(n,0)*(1-t)+b.get(n,0)*t for n in a.keys()|b.keys()}

def sleeve_weights(p,rest,transfer):
    side='l' if p.x>0 else 'r'
    names=['upperarm_'+side,'lowerarm_'+side,'hand_'+side]
    a,b,c=[rest[n].translation for n in names]
    def segment(x,y):
        t=max(0,min(1,(p-x).dot(y-x)/(y-x).length_squared));return t,(p-x.lerp(y,t)).length
    t1,d1=segment(a,b);t2,d2=segment(b,c)
    length1=(b-a).length;length2=(c-b).length
    along=t1*length1 if d1<d2 else length1+t2*length2
    elbow=smooth((along-length1+.085)/.17)
    cuff=smooth((along-length1-length2+.035)/.055)*.3
    arm={names[0]:1-elbow,names[1]:elbow*(1-cuff),names[2]:elbow*cuff}
    # Height alone must not anchor a hanging sleeve to the pelvis.
    arm_share=smooth((abs(p.x)-.14)/.13)*(1-smooth((p.z-1.47)/.17))
    torso={n:w for n,w in transfer(p).items() if n in ('pelvis','neck_01','neck_02','head') or n.startswith('spine_')}
    if sum(torso.values())<1e-8:torso={'spine_03':1}
    total=sum(torso.values());torso={n:w/total for n,w in torso.items()}
    waist=smooth((p.z-rest['pelvis'].translation.z-.02)/.15)
    torso=mix({'pelvis':1},torso,waist)
    return mix(torso,arm,arm_share)

def smooth_weights(o,values):
    adjacent=[set() for v in o.data.vertices]
    for e in o.data.edges:
        a,b=e.vertices;adjacent[a].add(b);adjacent[b].add(a)
    for _ in range(7):
        old=values;values=[]
        for i,neighbors in enumerate(adjacent):
            if not neighbors:values.append(old[i]);continue
            avg={}
            for j in neighbors:
                for n,w in old[j].items():avg[n]=avg.get(n,0)+w/len(neighbors)
            values.append(mix(old[i],avg,.45))
    return values
