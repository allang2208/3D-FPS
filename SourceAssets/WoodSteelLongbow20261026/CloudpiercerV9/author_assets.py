"""Cloudpiercer: native longbow interfaces, continuous silver ridges, inherited rig."""
from pathlib import Path
import bpy, math, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).parent; S=P.parent
(P/'Export').mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'WoodSteelLongbow_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
body=bpy.data.objects['SK_WoodSteelLongbow_Original']; rig=body.parent
for obj in list(bpy.data.objects):
    if obj not in (body,rig): bpy.data.objects.remove(obj,do_unlink=True)
body.hide_set(False);body.hide_render=False;rig.hide_set(False)
body.name='SK_HighlandLongbow_Cloudpiercer';body.data=body.data.copy()
for im in bpy.data.images:
    path=S/'Textures'/(im.name.split('.')[0]+'.png')
    if path.exists():im.filepath=str(path);im.reload()
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)

bins={}
for v in body.data.vertices:bins.setdefault(round(v.co.z),[]).append(v.co.copy())
def original_center(z):
    vs=bins[round(z)];return (min(v.x for v in vs)+max(v.x for v in vs))*.5

mask_values=[]
for v in body.data.vertices:
    z=abs(v.co.z);upper=v.co.z>=0;start,end=(29.,78.) if upper else (22.,68.)
    q=smooth((z-start)/12.)*(1-smooth((z-end)/7.))
    cx=original_center(v.co.z)
    # Central grip/rest/sight and terminal nock regions retain their exact source coordinates.
    v.co.x=cx+(v.co.x-cx)*(1+.18*q)-.55*q*math.sin(math.pi*(z-start)/(end+7-start))
    v.co.y*=1+.08*q
    mask_values.append(smooth((z-(17 if upper else 14))/12.)*(1-smooth((z-(80 if upper else 70))/6.)))
body.data.update()

# The existing UV, normal and packed metal/rough maps remain the source of surface detail.
# Vertex colour limits the walnut tint to the limb body, preserving source interface finishes.
mask=body.data.color_attributes.new(name='CloudpiercerWoodMask',type='BYTE_COLOR',domain='CORNER')
body.data.color_attributes.active_color=mask
for loop in body.data.loops:mask.data[loop.index].color=(mask_values[loop.vertex_index],0,0,1)
original=bpy.data.materials['M_WoodSteelLongbow_PBR']
walnut=original.copy();walnut.name='M_Cloudpiercer_Walnut'
nodes=walnut.node_tree.nodes;links=walnut.node_tree.links
shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
base=shader.inputs['Base Color'].links[0].from_socket
tint=(.65,.46,.36)
multiply=nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1
multiply.inputs[2].default_value=(*tint,1);links.new(base,multiply.inputs[1])
attribute=nodes.new('ShaderNodeVertexColor');attribute.layer_name=mask.name
channel=nodes.new('ShaderNodeSeparateColor');links.new(attribute.outputs['Color'],channel.inputs['Color'])
nonmetal=nodes.new('ShaderNodeMath');nonmetal.operation='SUBTRACT';nonmetal.inputs[0].default_value=1
if shader.inputs['Metallic'].is_linked:links.new(shader.inputs['Metallic'].links[0].from_socket,nonmetal.inputs[1])
else:nonmetal.inputs[1].default_value=shader.inputs['Metallic'].default_value
weight=nodes.new('ShaderNodeMath');weight.operation='MULTIPLY';links.new(channel.outputs[0],weight.inputs[0]);links.new(nonmetal.outputs[0],weight.inputs[1])
blend=nodes.new('ShaderNodeMixRGB');blend.blend_type='MIX';links.new(weight.outputs[0],blend.inputs[0]);links.new(base,blend.inputs[1]);links.new(multiply.outputs[0],blend.inputs[2]);links.new(blend.outputs[0],shader.inputs['Base Color'])
for i,material in enumerate(body.data.materials):
    if material==original:body.data.materials[i]=walnut

finishes={
 'M_Cloudpiercer_SatinSteel':{'color':[.48,.50,.52],'metallic':.92,'roughness':.31},
 'M_Cloudpiercer_RecessSteel':{'color':[.075,.080,.085],'metallic':.82,'roughness':.46},
 'M_Cloudpiercer_AshEdge':{'color':[.36,.24,.12],'metallic':0.,'roughness':.61},
}
materials={}
for name,finish in finishes.items():
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=(*finish['color'],1)
    bs.inputs['Metallic'].default_value=finish['metallic'];bs.inputs['Roughness'].default_value=finish['roughness']
    materials[name]=mat

body.data.calc_loop_triangles()
triangles=[tuple(t.vertices) for t in body.data.loop_triangles]
coords=[v.co.copy() for v in body.data.vertices]
bvh=BVHTree.FromPolygons(coords,triangles,all_triangles=True)
source_weights=[{body.vertex_groups[g.group].name:g.weight for g in v.groups} for v in body.data.vertices]
samples={}
for v in coords:samples.setdefault(round(v.z*2),[]).append(v)
def profile(z):
    vs=[]
    for key in range(round(z*2)-2,round(z*2)+3):vs.extend(samples.get(key,[]))
    lo=min(v.x for v in vs);hi=max(v.x for v in vs)
    return (lo+hi)*.5,(hi-lo)*.5,min(v.y for v in vs),max(v.y for v in vs)
def surface(x,z,face):
    origin=Vector((x,face*40,z));direction=Vector((0,-face,0))
    hit,normal,index,distance=bvh.ray_cast(origin,direction,80)
    if hit:return hit.y
    p=profile(z);return p[2] if face<0 else p[3]

def attach_weights(obj):
    groups={g.name:obj.vertex_groups.new(name=g.name) for g in body.vertex_groups}
    for vertex in obj.data.vertices:
        point,normal,index,distance=bvh.find_nearest(vertex.co)
        if index is None:raise RuntimeError('No source surface for '+obj.name)
        ids=triangles[index];a,b,c=[coords[j] for j in ids]
        e0=b-a;e1=c-a;e2=point-a
        d00=e0.dot(e0);d01=e0.dot(e1);d11=e1.dot(e1);d20=e2.dot(e0);d21=e2.dot(e1)
        denominator=d00*d11-d01*d01
        if abs(denominator)<1.e-12:
            blend_weights=[1.,0.,0.]
        else:
            v=(d11*d20-d01*d21)/denominator;w=(d00*d21-d01*d20)/denominator
            blend_weights=[max(0.,1-v-w),max(0.,v),max(0.,w)]
        accumulated={}
        for idx,factor in zip(ids,blend_weights):
            for name,weight in source_weights[idx].items():accumulated[name]=accumulated.get(name,0.)+weight*factor
        total=sum(accumulated.values())
        for name,weight in accumulated.items():
            if weight>1.e-8:groups[name].add([vertex.index],weight/total,'REPLACE')

parts=[]
uv_name=body.data.uv_layers.active.name
def mesh(name,verts,faces,material,bevel_width=.035):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.materials.append(material);data.update()
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    for polygon in data.polygons:polygon.use_smooth=True
    if bevel_width>0:
        bevel=obj.modifiers.new('Narrow forged bevel','BEVEL');bevel.width=bevel_width;bevel.segments=3;bevel.limit_method='ANGLE'
    normals=obj.modifiers.new('Weighted shoulder normals','WEIGHTED_NORMAL');normals.keep_sharp=True
    for modifier in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.025)
    bpy.ops.object.mode_set(mode='OBJECT');obj.data.uv_layers.active.name=uv_name
    attach_weights(obj);parts.append(obj);return obj

def ridge(name,z0,z1,edge,face,width_scale,height,material):
    vertices=[];count=110
    for j in range(count):
        t=j/(count-1);z=z0+(z1-z0)*t;cx,half,_,_=profile(z)
        taper=.32+.68*math.sin(math.pi*t)**.45
        x=cx+edge*half
        width=min(.32,half*.18)*width_scale*taper
        for dx,depth in [(-width,-.025),(width,-.025),(width*.68,height),(-width*.68,height)]:
            vertices.append((x+dx,surface(x+dx,z,face)+face*depth,z))
    # Forge uninterrupted rails over the source surface's small sculpted undulations.
    # Smooth along the limb only; retain cross-section thickness and terminal caps.
    for iteration in range(3):
        previous=vertices[:]
        for j in range(1,count-1):
            for corner in range(4):
                neighbors=[(max(0,min(count-1,j+delta)),4-abs(delta)) for delta in range(-3,4)]
                total=sum(weight for _,weight in neighbors)
                x=sum(previous[row*4+corner][0]*weight for row,weight in neighbors)/total
                y=sum(previous[row*4+corner][1]*weight for row,weight in neighbors)/total
                vertices[j*4+corner]=(x,y,previous[j*4+corner][2])
    faces=[]
    for j in range(count-1):
        for k in range(4):faces.append((4*j+k,4*j+(k+1)%4,4*(j+1)+(k+1)%4,4*(j+1)+k))
    faces.extend([(3,2,1,0),tuple(range(4*(count-1),4*count))])
    # Ensure coherent outward winding regardless of lower-limb direction / view face.
    obj=mesh(name,vertices,faces,material,bevel_width=0.)
    import bmesh
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    return obj

for side,z0,z1 in [('Upper',25.,82.),('Lower',-18.,-72.)]:
    for face in (-1,1):
        for edge in (-.50,.50):
            ridge(f'{side}_InlaidRecess_{face}_{edge}',z0,z1,edge,face,1.28,.075,materials['M_Cloudpiercer_RecessSteel'])
            ridge(f'{side}_ContinuousSilverRidge_{face}_{edge}',z0,z1,edge,face,.78,.16,materials['M_Cloudpiercer_SatinSteel'])
        # One narrow, pale laminate line follows each outside edge on both faces.
        for edge in (-.78,.78):
            ridge(f'{side}_AshLaminate_{face}_{edge}',z0+(.8 if z0>0 else -.8),z1,edge,face,.30,.055,materials['M_Cloudpiercer_AshEdge'])

def diamond(name,z,face,halfwidth,height,material,offset):
    cx,_,_,_=profile(z)
    outline=[(cx,z+height),(cx+halfwidth,z),(cx,z-height),(cx-halfwidth,z)]
    vertices=[]
    for depth in (offset-.03,offset+.10):
        for x,zz in outline:vertices.append((x,surface(x,zz,face)+face*depth,zz))
    faces=[(3,2,1,0),(4,5,6,7)]+[(j,(j+1)%4,(j+1)%4+4,j+4) for j in range(4)]
    obj=mesh(name,vertices,faces,material)
    import bmesh
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
for z in (24.,-17.):
    for face in (-1,1):
        diamond('SculptedRootShield',z,face,.75,2.65,materials['M_Cloudpiercer_SatinSteel'],.08)
        diamond('InsetDiamond',z,face,.26,1.10,materials['M_Cloudpiercer_RecessSteel'],.20)

bpy.ops.object.select_all(action='DESELECT');body.select_set(True)
for obj in parts:obj.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
tri=body.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(body.name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,add_leaf_bones=False,bake_anim=False,use_tspace=True,mesh_smooth_type='FACE',colors_type='LINEAR')
bpy.ops.wm.save_as_mainfile(filepath=str(P/'HighlandLongbow_Cloudpiercer_Production.blend'))
record={'mesh':body.name,'materials':[m.name for m in body.data.materials],
 'triangles':sum(len(p.vertices)-2 for p in body.data.polygons),'bones':[b.name for b in rig.data.bones],
 'source':str(S/'WoodSteelLongbow_Editable.blend'),
 'concept':str(S/'CloudpiercerConceptV8/Cloudpiercer_BowBody_Concept_v1.png'),
 'finishes':finishes,'walnut_tint':list(tint),'wood_mask':'CloudpiercerWoodMask.R * (1 - metallic)',
 'new_geometry_weights':'Barycentric interpolation from nearest original source triangle',
 'retained_interfaces':['grip','arrow_rest','sight','nock_upper','nock_lower'],
 'gameplay_tested':False}
(P/'authoring.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('CLOUDPIERCER_AUTHORED '+str(record['triangles']),flush=True)
