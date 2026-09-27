"""London-pattern reference revision: one welded head/horn/body, no stacked plate."""
from pathlib import Path
import bpy,bmesh,json,math
from mathutils import Vector

HERE=Path(__file__).parent;ROOT=HERE.parent;OUT=HERE/'Authored';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authored/CastingStation_Source.blend'))
bpy.context.preferences.filepaths.save_version=0
for name in ['Anvil foot','Anvil waisted body','Anvil working face','Anvil round horn']:
    ob=bpy.data.objects.get(name)
    if ob is None:raise RuntimeError('Missing source '+name)
    bpy.data.objects.remove(ob,do_unlink=True)
PARTS=[]
def co(v):return Vector((v[0]*.01,-v[1]*.01,v[2]*.01))
def activate(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
def normals(ob):
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
def mesh(name,verts,faces):
    me=bpy.data.meshes.new(name);me.from_pydata([co(v) for v in verts],[],faces);me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);normals(ob);return ob
def loft(name,rings):
    n=len(rings[0]);vs=[v for r in rings for v in r];fs=[tuple(reversed(range(n)))]
    for j in range(len(rings)-1):
        for i in range(n):k=(i+1)%n;fs.append((j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i))
    fs.append(tuple(range((len(rings)-1)*n,len(rings)*n)))
    return mesh(name,vs,fs)
def boolean(ob,tool,op):
    activate(ob);m=ob.modifiers.new(op,'BOOLEAN');m.operation=op;m.solver='EXACT';m.object=tool
    bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(tool,do_unlink=True)
def cube(name,center,size):
    bpy.ops.mesh.primitive_cube_add(size=1,location=co(center));ob=bpy.context.object;ob.name=name;ob.dimensions=Vector(size)*.01
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return ob
def cylinder(center,r,depth,axis='Z',vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r*.01,depth=depth*.01,location=co(center));ob=bpy.context.object
    if axis=='X':ob.rotation_euler[1]=math.pi/2
    if axis=='Y':ob.rotation_euler[0]=math.pi/2
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);return ob

# Cross-sections are shared from the rounded horn tip through the step and heel.
# Top of horn is nearly horizontal; its underside rises naturally to the tip.
# No capped cone at the root and no extra face plate intersecting the shoulder.
head_keys=[(-23,.12,88.30,88.56,2),(-21.5,.65,87.0,88.60,2),(-18,1.6,84.8,88.60,2),
    (-14,2.65,82.5,88.55,2),(-9,4.0,79.9,88.45,2),(-3,5.7,77.4,88.25,2.2),
    (2,7.0,76.4,88.10,3),(5,7.8,76.5,88.10,5),(8.8,8.0,77.0,88.10,18),
    (10,8.0,77.6,88.10,36),(10.18,8.05,77.7,90.82,36),(10.38,8.1,77.8,91,36),
    (14,8.1,78.1,91,36),(23,8.1,79.4,91,36),(32,8.1,80.4,91,36),
    (40,8.1,82.0,91,36),(48,8.1,84.4,91,36),(52.7,8.1,85.0,91,36),(53,7.95,85.12,90.88,36)]
head_rings=[]
for j in range(len(head_keys)-1):
    a,b=head_keys[j],head_keys[j+1]
    steps=4 if b[0]-a[0]>1 else 1
    for k in range(steps):
        t=k/steps;x,w,lo,hi,n=[p+(q-p)*t for p,q in zip(a,b)]
        row=[]
        for i in range(64):
            ang=math.tau*i/64;c,s=math.cos(ang),math.sin(ang)
            zz=(hi+lo)/2+(hi-lo)/2*math.copysign(abs(s)**(2/n),s)
            if n>=35 and abs(s)>.38:zz=hi if s>0 else lo
            row.append((x,22+w*math.copysign(abs(c)**(2/n),c),zz))
        head_rings.append(row)
x,w,lo,hi,n=head_keys[-1]
head_rings.append([(x,22+w*math.copysign(abs(math.cos(math.tau*i/64))**(2/n),math.cos(math.tau*i/64)),
    (hi+lo)/2+(hi-lo)/2*math.copysign(abs(math.sin(math.tau*i/64))**(2/n),math.sin(math.tau*i/64))) for i in range(64)])
head=loft('Anvil V3 integral horn step and head',head_rings)

def rounded_ring(z,cx,hx,hy,r):
    row=[]
    for x,y,a in [(cx+hx-r,22+hy-r,0),(cx-hx+r,22+hy-r,90),(cx-hx+r,22-hy+r,180),(cx+hx-r,22-hy+r,270)]:
        for k in range(7):
            ang=math.radians(a+k*90/6);row.append((x+r*math.cos(ang),y+r*math.sin(ang),z))
    return row
# Broad flat-sided waist and distinct low feet, with restricted edge rounding.
body_keys=[(62,27,19.6,13.3,.65),(63.6,27,19.8,13.3,.8),(65,27,18.7,12.6,1),
    (66.2,27,16.5,10.8,1.25),(68,26.8,13.4,8.8,1.5),(70.5,26.4,11.5,7.9,1.6),
    (73,26.0,11.1,7.7,1.6),(77,26,11.2,7.7,1.6),(79,26,12.0,7.9,1.4),
    (81,26,14.0,8.05,1.2),(83,26,16.3,8.05,.9),(86,26,17.0,8.05,.5)]
body=loft('Anvil V3 single forged solid',[rounded_ring(*k) for k in body_keys])
boolean(body,head,'UNION')
boolean(body,cylinder((27,22,61.8),2.1,70,'X'),'DIFFERENCE')
boolean(body,cylinder((27,22,61.8),2.8,50,'Y'),'DIFFERENCE')
boolean(body,cube('Hardy cutter',(46.4,23.3,89),(2.8,2.8,16)),'DIFFERENCE')
boolean(body,cylinder((49.5,17.3,89),.72,16),'DIFFERENCE')
PARTS.append(body)

for y in [8.3,35.7]:
    PARTS.append(cube('Anvil V3 forged fixing lug',(27,y,63.45),(6.8,4.5,1.45)))
    bolt=cylinder((27,y,64.5),.8,.65,vertices=6);bolt.name='Anvil V3 fixing bolt';PARTS.append(bolt)

# One surface uses the physically authored wear mask, so horn roots have no colour seam.
mat=bpy.data.materials.new('AnvilSteel');mat.use_nodes=True
nodes,links=mat.node_tree.nodes,mat.node_tree.links;nodes.clear()
bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial');links.new(bs.outputs['BSDF'],out.inputs['Surface'])
wear=nodes.new('ShaderNodeVertexColor');wear.layer_name='AnvilWear'
lib=ROOT.parent/'BlastFurnace20260923/Authored/Textures'
def tex(path):
    n=nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(path),check_existing=True)
    n.image.colorspace_settings.name='sRGB' if path.stem.endswith('BaseColor') else 'Non-Color'
    return n
iron=tex(lib/'BlastFurnace_WroughtIron_BaseColor.png')
worked=tex(HERE/'Textures/T_Anvil_Worked_BaseColor.png')
dark=nodes.new('ShaderNodeMixRGB');dark.blend_type='MULTIPLY';dark.inputs[0].default_value=1;dark.inputs[2].default_value=(.5,.5,.5,1);links.new(iron.outputs['Color'],dark.inputs[1])
mix=nodes.new('ShaderNodeMixRGB');links.new(wear.outputs['Color'],mix.inputs[0]);links.new(dark.outputs[0],mix.inputs[1]);links.new(worked.outputs['Color'],mix.inputs[2]);links.new(mix.outputs[0],bs.inputs['Base Color'])
# Keep the editable source's actual PBR channels, including DirectX-to-Blender normals.
orm=tex(HERE/'Textures/T_Anvil_Worked_ORM.png')
sep=nodes.new('ShaderNodeSeparateColor');links.new(orm.outputs['Color'],sep.inputs[0])
def math_node(op,source,value):
    n=nodes.new('ShaderNodeMath');n.operation=op;links.new(source,n.inputs[0]);n.inputs[1].default_value=value;return n.outputs[0]
for field,channel,mult,offset in [('Roughness','Green',.36,.44),('Metallic','Blue',.68,.18)]:
    b=tex(lib/('BlastFurnace_WroughtIron_'+field+'.png'))
    scalar=math_node('ADD',math_node('MULTIPLY',b.outputs['Color'],mult),offset)
    m=nodes.new('ShaderNodeMixRGB');links.new(wear.outputs['Color'],m.inputs[0]);links.new(scalar,m.inputs[1]);links.new(sep.outputs[channel],m.inputs[2])
    links.new(m.outputs[0],bs.inputs[field])
normal_outputs=[]
for path,strength in [(lib/'BlastFurnace_WroughtIron_Normal.png',.5),(HERE/'Textures/T_Anvil_Worked_Normal.png',1.)]:
    t=tex(path);s=nodes.new('ShaderNodeSeparateColor');links.new(t.outputs['Color'],s.inputs[0])
    inv=nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;links.new(s.outputs['Green'],inv.inputs[1])
    combine=nodes.new('ShaderNodeCombineColor');links.new(s.outputs['Red'],combine.inputs['Red']);links.new(inv.outputs[0],combine.inputs['Green']);links.new(s.outputs['Blue'],combine.inputs['Blue'])
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=strength;links.new(combine.outputs[0],normal.inputs['Color']);normal_outputs.append(normal.outputs['Normal'])
nmix=nodes.new('ShaderNodeMixRGB');links.new(wear.outputs['Color'],nmix.inputs[0]);links.new(normal_outputs[0],nmix.inputs[1]);links.new(normal_outputs[1],nmix.inputs[2])
unit=nodes.new('ShaderNodeVectorMath');unit.operation='NORMALIZE';links.new(nmix.outputs[0],unit.inputs[0]);links.new(unit.outputs[0],bs.inputs['Normal'])

# Current approved geometry keeps its own aged surface on subsequent authoring runs.
import sys
sys.path.insert(0,str(HERE))
from aged_material_blender import make_aged_material
make_aged_material(mat,HERE)

for ob in PARTS:
    activate(ob);normals(ob)
    ob.data.materials.clear();ob.data.materials.append(mat)
    for p in ob.data.polygons:p.material_index=0
    bevel=ob.modifiers.new('Small forged edge radii','BEVEL');bevel.width=.0011 if ob==body else .0008
    bevel.segments=3;bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(36);bevel.harden_normals=True
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    tri=ob.modifiers.new('Stable triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    for p in ob.data.polygons:p.use_smooth=True
    ob.data.set_sharp_from_angle(angle=math.radians(48))
    weighted=ob.modifiers.new('Preserve flat striking face','WEIGHTED_NORMAL');weighted.keep_sharp=True;weighted.weight=20
    bpy.ops.object.modifier_apply(modifier=weighted.name)
    while len(ob.data.uv_layers):ob.data.uv_layers.remove(ob.data.uv_layers[0])
    uv=ob.data.uv_layers.new(name='AnvilPhysical50cm');uv.active_render=True
    col=ob.data.color_attributes.new(name='AnvilWear',type='FLOAT_COLOR',domain='CORNER')
    ob.data.color_attributes.active_color=col
    for p in ob.data.polygons:
        # Every shell uses the same physical texel density, never scaled to UV bounds.
        axis=max(range(3),key=lambda i:abs(p.normal[i]))
        for li in p.loop_indices:
            v=ob.matrix_world@ob.data.vertices[ob.data.loops[li].vertex_index].co
            x,y,z=v.x*100,-v.y*100,v.z*100
            if axis==2:pair=(x,y)
            elif axis==1:pair=(x,z)
            else:pair=(y,z)
            uv.data[li].uv=(pair[0]/50,pair[1]/50)
            amount=.02
            if ob==body:
                if x>=10.15 and z>90.45:amount=1.
                elif x<10.15:
                    horn_use=max(0,min(1,(z-79)/9))
                    tip_use=max(0,min(1,(9-x)/22))
                    amount=.1+.55*horn_use+.25*tip_use
                elif z>89.5:amount=.45
                elif z<65 and (abs(x-27)>18 or abs(y-22)>12.3):amount=.32
            else:amount=.15
            col.data[li].color=(amount,amount,amount,1)

manifest=json.loads((ROOT/'Authored/manifest.json').read_text(encoding='utf8'))
manifest['revision']='AnvilReferenceV3';manifest['assets']={}
manifest['construction']={'body':'Boolean-unified forging with continuous horn-to-head topology',
    'base_z_cm':62,'workface_z_cm':91,'workface_x_cm':[10.38,52.7],'workface_width_cm':16.2,
    'uv_span_cm':50,'material':'Normandy oxidized iron blended with worked steel using AnvilWear vertex colours'}

def export(name,objects,pivot):
    copies=[]
    for src in objects:
        ob=src.copy();ob.data=src.data.copy();bpy.context.collection.objects.link(ob);copies.append(ob)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in copies:ob.select_set(True)
    bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();ob=bpy.context.object;ob.name=name
    bpy.context.scene.cursor.location=co(pivot);bpy.ops.object.origin_set(type='ORIGIN_CURSOR');ob.location=(0,0,0)
    tri=ob.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    path=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,
        mesh_smooth_type='FACE',use_tspace=True,colors_type='LINEAR',add_leaf_bones=False,bake_anim=False)
    points=[ob.matrix_world@v.co for v in ob.data.vertices]
    expected_size=[(max(p[i] for p in points)-min(p[i] for p in points))*100 for i in range(3)]
    manifest['assets'][name]={'fbx':str(path),'pivot_ue_cm':pivot,'material_slots':[m.name for m in ob.data.materials],
        'dimensions_cm':expected_size,'fbx_units':'centimetres baked into transforms; UnitScaleFactor=1',
        'triangles':sum(len(p.vertices)-2 for p in ob.data.polygons)}
    bpy.data.objects.remove(ob,do_unlink=True)
export('SM_CastingStation',[ob for ob in bpy.context.scene.objects if ob.type=='MESH'],(0,0,0))
export('SM_CastingAnvil',PARTS,(27,22,62))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'CastingStation_AnvilReference_Source.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print('ANVIL_REFERENCE_AUTHORED '+json.dumps(manifest['assets']),flush=True)
