"""Keep grip interfaces; author segmented suspension with rigid pendant weights."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
S=json.loads((P/'surfaces.json').read_text(encoding='utf-8'))
TAILS=['ice_soul_pendant','thunder_bell','purification_vine','flame_pendant']
names=['SM_Staff_grip_lining_'+k for k in S]+['SM_Staff_tail_charm_'+k for k in TAILS]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
with bpy.data.libraries.load(str(P.parent/'BarkRebuildV21/Staff_NaturalBark_V21.blend'),link=False) as (src,dst):dst.objects=names
objects={o.name:o for o in dst.objects}
for o in objects.values():bpy.context.scene.collection.objects.link(o)
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def material(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    return m
for key,s in S.items():
    o=objects['SM_Staff_grip_lining_'+key]
    m=material('MI_StaffGripCraft_'+key,s['color'],s['metallic'],s['roughness'])
    if not s['metallic']:
        ns=m.node_tree.nodes;lk=m.node_tree.links;bs=ns.get('Principled BSDF')
        uv=ns.new('ShaderNodeTexCoord');scale=ns.new('ShaderNodeVectorMath');scale.operation='MULTIPLY'
        scale.inputs[1].default_value=s['uv_scale'];lk.new(uv.outputs['UV'],scale.inputs[0])
        images={}
        for kind in ['BaseColor','Normal','RHAOM']:
            im=bpy.data.images.load(str(P.parent/'SolidRepairV19/Inputs'/('T_WoodSurface_00A_'+kind+'.png')),check_existing=True)
            im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';im.pack()
            n=ns.new('ShaderNodeTexImage');n.image=im;lk.new(scale.outputs[0],n.inputs['Vector']);images[kind]=n
        tint=ns.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1
        contrast=ns.new('ShaderNodeMixRGB');contrast.inputs[0].default_value=s['grain_contrast'];contrast.inputs[1].default_value=(.18,.135,.083,1)
        lk.new(images['BaseColor'].outputs['Color'],contrast.inputs[2])
        tint.inputs[2].default_value=(*s['color'],1);lk.new(contrast.outputs[0],tint.inputs[1]);lk.new(tint.outputs[0],bs.inputs['Base Color'])
        packed=ns.new('ShaderNodeSeparateColor');lk.new(images['RHAOM'].outputs['Color'],packed.inputs[0])
        rough=ns.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=s['roughness']-.5*s['roughness_variation']
        rough.inputs['To Max'].default_value=s['roughness']+.5*s['roughness_variation']
        lk.new(packed.outputs['Red'],rough.inputs['Value']);lk.new(rough.outputs[0],bs.inputs['Roughness'])
        # Source normal is DirectX. Blender converts green once; UE uses it directly.
        split=ns.new('ShaderNodeSeparateColor');lk.new(images['Normal'].outputs['Color'],split.inputs[0])
        inv=ns.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;lk.new(split.outputs['Green'],inv.inputs[1])
        join=ns.new('ShaderNodeCombineColor');lk.new(split.outputs['Red'],join.inputs['Red']);lk.new(inv.outputs[0],join.inputs['Green']);lk.new(split.outputs['Blue'],join.inputs['Blue'])
        n=ns.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=s['pore_normal']
        lk.new(join.outputs[0],n.inputs['Color']);lk.new(n.outputs['Normal'],bs.inputs['Normal'])
    o.data.materials.clear();o.data.materials.append(m)
    for f in o.data.polygons:f.material_index=0

specs={}
for key in TAILS:
    o=objects['SM_Staff_tail_charm_'+key]
    # Find the connected suspension, distinct from fixed clamp and pendant cap.
    bm=bmesh.new();bm.from_mesh(o.data);seen=set();groups=[]
    for v in bm.verts:
        if v in seen:continue
        group=[];todo=[v];seen.add(v)
        while todo:
            v=todo.pop();group.append(v)
            for e in v.link_edges:
                other=e.other_vert(v)
                if other not in seen:seen.add(other);todo.append(other)
        groups.append(group)
    suspension=next(g for g in groups if max(v.co.z for v in g)-min(v.co.z for v in g)>8)
    # Original loft stores ten vertices per ring, with the attachment ring first.
    ring=sorted(suspension,key=lambda v:v.index)[:10];pin=sum((v.co for v in ring),Vector())/10
    bmesh.ops.delete(bm,geom=suspension,context='VERTS');bm.to_mesh(o.data);bm.free()
    tip={'ice_soul_pendant':-77.15,'thunder_bell':-76.2,'purification_vine':-76.9,'flame_pendant':-76.8}[key]
    guides=[pin,Vector((3.35,0,-64.6)),Vector((4.1,0,-65.8)),Vector((4.7,0,-67.6)),
            Vector((5.2,0,-69.2)),Vector((5.2,0,-71)),Vector((5.2,0,-72.8)),Vector((5.2,0,tip))]
    # Rebuild only the short metal suspension with enough rings to bend smoothly.
    path=[]
    for a,b in zip(guides[:6],guides[1:7]):
        steps=max(1,math.ceil((b-a).length/.24));path.extend(a.lerp(b,i/steps) for i in range(steps))
    path.append(guides[6]);verts=[];faces=[];sides=12
    for i,p in enumerate(path):
        tangent=(path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized()
        normal=tangent.cross(Vector((0,1,0))).normalized();other=tangent.cross(normal).normalized()
        verts.extend(p+.135*(math.cos(j*math.tau/sides)*normal+math.sin(j*math.tau/sides)*other) for j in range(sides))
    for i in range(len(path)-1):
        for j in range(sides):faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(path)-1)*sides+j for j in range(sides))])
    me=bpy.data.meshes.new('FlexibleSuspension');me.from_pydata(verts,[],faces);me.update();me.materials.append(o.data.materials[0])
    uv=me.uv_layers.new(name='UVMap')
    for f in me.polygons:
        f.use_smooth=True
        for li in f.loop_indices:
            v=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(v.x/4,v.z/4)
    tube=bpy.data.objects.new('Suspension',me);bpy.context.scene.collection.objects.link(tube)
    active(o);tube.select_set(True);bpy.ops.object.join()
    # Use UV1 for skinning, red vertex color for fixed/moving region.
    while len(o.data.uv_layers)>1:o.data.uv_layers.remove(o.data.uv_layers[-1])
    skin=o.data.uv_layers.new(name='TailSkin')
    for attr in list(o.data.color_attributes):o.data.color_attributes.remove(attr)
    mask=o.data.color_attributes.new(name='TailMotion',type='FLOAT_COLOR',domain='CORNER')
    # Fixed clamp is the only connected piece crossing both sides of the shaft.
    adj=[[] for _ in o.data.vertices]
    for e in o.data.edges:a,b=e.vertices;adj[a].append(b);adj[b].append(a)
    seen=set();fixed=set();rigid=set()
    for v in o.data.vertices:
        if v.index in seen:continue
        ids=[];todo=[v.index];seen.add(v.index)
        while todo:
            i=todo.pop();ids.append(i)
            for j in adj[i]:
                if j not in seen:seen.add(j);todo.append(j)
        if min(o.data.vertices[i].co.x for i in ids)<0:fixed.update(ids)
        elif max(o.data.vertices[i].co.z for i in ids)<-72.3:rigid.update(ids)
    for li,loop in enumerate(o.data.loops):
        v=o.data.vertices[loop.vertex_index];weight=0.;idx=0
        moving=v.index not in fixed
        if v.index in rigid:idx=6
        elif moving:
            best=1.e20
            for i,(a,b) in enumerate(zip(guides[:6],guides[1:7])):
                d=b-a;t=max(0.,min(1.,(v.co-a).dot(d)/d.length_squared));dist=(v.co-a-t*d).length_squared
                if dist<best:best=dist;idx=i;weight=t*t*(3-2*t)
        skin.data[li].uv=(idx,weight);mask.data[li].color=(float(moving),0,0,1)
    for i,old in enumerate(list(o.data.materials)):
        # Each pendant owns its rest-space shader; shared elemental mats stay intact.
        m=old.copy();m.name='M_StaffTailCraft_'+key+('_Metal' if i==0 else '_Element');o.data.materials[i]=m
    specs[o.name]={'guides_cm':[list(v) for v in guides],
        'inverse_masses':[0,1,1,1,1,.7,.18 if key=='thunder_bell' else .25,.18 if key=='thunder_bell' else .25],
        'collision_capsules_cm':[[0,0,-81,0,0,-65,2.65]],
        'fixed_clamp':True,'rigid_pendant_segment':6,'uv1':'segment index / blend; FBX V flips once',
        'vertex_red':'0=fixed clamp; 1=moving suspension or pendant'}

entries=[]
for name,o in objects.items():
    active(o);file=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,apply_scale_options='FBX_SCALE_ALL',path_mode='AUTO')
    entries.append({'name':name,'fbx':str(file),'materials':[m.name for m in o.data.materials],
                    'triangles':sum(len(p.vertices)-2 for p in o.data.polygons),'tail_dynamics':name in specs})
(OUT/'meshes.json').write_text(json.dumps(entries,indent=2),encoding='utf-8')
(OUT/'tail-dynamics.json').write_text(json.dumps(specs,indent=2),encoding='utf-8')
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Staff_GripTailRefinement.blend'))
print('STAFF_GRIP_TAIL_AUTHORED meshes=8 rendered=false',flush=True)
