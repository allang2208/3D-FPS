"""Keep exact stock rim appearance, blend new neck into a bronze-only atlas patch."""
import bpy,json,math,sys
from mathutils import Vector
from pathlib import Path
P=Path(__file__).parent;KEY=sys.argv[sys.argv.index('--')+1];OUT=P/KEY
bpy.ops.wm.open_mainfile(filepath=str(OUT/'FrostPommel_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
obj=bpy.data.objects['SM_FrostPommel_'+KEY];data=obj.data
uv0=data.uv_layers[0];uv1=data.uv_layers[1]
color=data.color_attributes.get('PommelFinish') or data.color_attributes.new(name='PommelFinish',type='FLOAT_COLOR',domain='CORNER')
data.color_attributes.active_color=color
patch=json.loads((P.parent/'MeleeGuards20260915/finish_patch.json').read_text());lo=patch['uv_min'];hi=patch['uv_max']
for f in data.polygons:
    for index in f.loop_indices:
        p=data.vertices[data.loops[index].vertex_index].co
        t=max(0,min(1,(-p.z-.002)/.002));t=t*t*(3-2*t)
        color.data[index].color=(t,t,t,1) if f.material_index==0 else (0,0,0,1)
        if f.material_index==0:
            u=(math.atan2(p.y,p.x)+math.pi)/(2*math.pi);v=max(0,min(1,-p.z/.020))
            uv1.data[index].uv=(lo[0]+u*(hi[0]-lo[0]),lo[1]+v*(hi[1]-lo[1]))
    if f.material_index==0:
        below=all(data.vertices[data.loops[i].vertex_index].co.z<=-.003999 for i in f.loop_indices)
        cap=all(abs(data.vertices[data.loops[i].vertex_index].co.z)<.000001 for i in f.loop_indices)
        if below:
            # New transition needs an unfolded UV instead of a nearest-point
            # projection that can collapse entire triangles to one texel.
            us=[uv1.data[i].uv.x for i in f.loop_indices]
            if max(us)-min(us)>(hi[0]-lo[0])*.5:
                for i in f.loop_indices:
                    if uv1.data[i].uv.x<(lo[0]+hi[0])*.5:uv1.data[i].uv.x+=hi[0]-lo[0]
            for i in f.loop_indices:uv0.data[i].uv=uv1.data[i].uv
        if cap:
            # The concealed installation cap had one UV for every corner.
            for i in f.loop_indices:
                p=data.vertices[data.loops[i].vertex_index].co
                uv0.data[i].uv=(lo[0]+(p.x/.08+.5)*(hi[0]-lo[0]),lo[1]+(p.y/.08+.5)*(hi[1]-lo[1]));uv1.data[i].uv=uv0.data[i].uv
                color.data[i].color=(1,1,1,1)
# Repair isolated collapsed texture triangles without moving any vertex or
# re-unwrapping the baked body/inlay. Keep the same atlas sample at their center.
repaired=0
for f in data.polygons:
    ids=list(f.loop_indices)
    if len(ids)!=3:continue
    a,b,c=[uv0.data[i].uv.copy() for i in ids]
    if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>1e-12:continue
    p0,p1,p2=[data.vertices[data.loops[i].vertex_index].co for i in ids]
    axis=(p1-p0).normalized();normal=(p1-p0).cross(p2-p0).normalized();other=normal.cross(axis)
    local=[Vector((0,0)),Vector(((p1-p0).length,0)),Vector(((p2-p0).dot(axis),(p2-p0).dot(other)))]
    radius=max(v.length for v in local)
    if radius<1e-10:continue
    center=(a+b+c)/3;mean=sum(local,Vector((0,0)))/3
    for i,p in zip(ids,local):uv0.data[i].uv=center+(p-mean)*(1/4096/radius)
    repaired+=1
old=data.materials[0];images={}
for n in old.node_tree.nodes:
    if n.type=='TEX_IMAGE':
        name=n.image.name.lower();tag='normal' if 'normal' in name else 'metallic' if 'metallic' in name else 'roughness' if 'roughness' in name else 'base';images[tag]=n.image
mat=bpy.data.materials.new('M_FrostPommel_Collar');mat.use_nodes=True
n=mat.node_tree.nodes;l=mat.node_tree.links;b=n.get('Principled BSDF')
vcol=n.new('ShaderNodeVertexColor');vcol.layer_name='PommelFinish'
u0=n.new('ShaderNodeUVMap');u0.uv_map=uv0.name;u1=n.new('ShaderNodeUVMap');u1.uv_map=uv1.name
for kind,target in [('base','Base Color'),('metallic','Metallic'),('roughness','Roughness')]:
    a=n.new('ShaderNodeTexImage');a.image=images[kind];l.new(u0.outputs['UV'],a.inputs['Vector'])
    c=n.new('ShaderNodeTexImage');c.image=images[kind];l.new(u1.outputs['UV'],c.inputs['Vector'])
    mix=n.new('ShaderNodeMixRGB');l.new(vcol.outputs['Color'],mix.inputs[0]);l.new(a.outputs['Color'],mix.inputs[1]);l.new(c.outputs['Color'],mix.inputs[2]);l.new(mix.outputs[0],b.inputs[target])
tex=n.new('ShaderNodeTexImage');tex.image=images['normal'];l.new(u0.outputs['UV'],tex.inputs['Vector'])
mix=n.new('ShaderNodeMixRGB');mix.inputs[2].default_value=(.5,.5,1,1);l.new(vcol.outputs['Color'],mix.inputs[0]);l.new(tex.outputs[0],mix.inputs[1])
normal=n.new('ShaderNodeNormalMap');normal.uv_map=uv0.name;l.new(mix.outputs[0],normal.inputs['Color']);l.new(normal.outputs[0],b.inputs['Normal'])
data.materials[0]=mat;data.uv_layers.active_index=0;data.uv_layers[0].active_render=True
# A few sliver faces in the generated body have unusable tangent frames even
# with nonzero UV area. Give only those corners a well-conditioned local frame.
# The factory mounting rim and the body vertex positions remain untouched.
data.calc_tangents(uvmap=uv0.name)
bad_faces=[f for f in data.polygons if any(data.loops[i].tangent.length<.0001 for i in f.loop_indices)]
if bad_faces:
    normals=[n.vector.copy() for n in data.corner_normals]
    for f in bad_faces:
        ids=list(f.loop_indices);center=sum((uv0.data[i].uv for i in ids),Vector((0,0)))/len(ids)
        for j,i in enumerate(ids):
            angle=2*math.pi*j/len(ids)
            uv0.data[i].uv=center+Vector((math.cos(angle),math.sin(angle)))/4096
            normals[i]=f.normal.copy()
    data.free_tangents();data.normals_split_custom_set(normals)
bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FrostPommel_Editable.blend'))
report=json.loads((OUT/'authoring.json').read_text());report['collar_finish']='Original UV and normal at rim; smoothly blends into stock bronze patch across 2-4 mm below rim; vertex color PommelFinish'
report['collapsed_uv_triangles_repaired']=repaired
report['sliver_tangent_faces_repaired']=len(bad_faces)
(OUT/'authoring.json').write_text(json.dumps(report,indent=2));print('COLLAR_FINISHED',KEY,flush=True)
