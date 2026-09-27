"""Icon-only relaxed glove pose from current native meshes, with an orthonormal camera frame.

No source mesh, worn rig, animation, pickup FBX or UE package is modified.
Both icons show one empty glove. No secondary hand overlaps the silhouette.
"""
import json
from pathlib import Path
import numpy as np
import bpy
from mathutils import Euler

P=Path(__file__).resolve().parents[2]
R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2'

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def unit(v):return np.asarray(v)/np.linalg.norm(v)

def align(a,b):
    a=unit(a);b=unit(b);v=np.cross(a,b);c=float(a@b)
    skew=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3)+skew+skew@skew/(1+c)

def display_frame(bones,anatomy,side):
    wrist=np.asarray(bones['hand_'+side]['position'])
    z=unit(anatomy[side]['dorsal'])
    y=np.asarray(bones['middle_01_'+side]['position'])-wrist
    y=unit(y-z*(y@z))
    x=-np.cross(y,z)
    # The reflection converts UE's winding convention once. Across and forward
    # are perpendicular; dotting into the old skewed basis sheared the palm.
    return np.array([x,y,z]),wrist

def posed_surface(data,bones,anatomy,side):
    frame,wrist=display_frame(bones,anatomy,side)
    positions=(np.asarray(data['positions'])-wrist)@frame.T
    heads={n:frame@(np.asarray(b['position'])-wrist) for n,b in bones.items()}
    transforms={}
    # Mild MCP/PIP/DIP flexion keeps the natural phalange lengths and fingertip
    # cascade. Splay is small, not a flat fan or a posed weapon grip.
    for finger,spread in [('index',-4),('middle',0),('ring',4),('pinky',8),('thumb',0)]:
        names=[f'{finger}_{i:02d}_{side}' for i in (1,2,3)]
        p1,p2,p3=[heads[n] for n in names]
        if finger=='thumb':
            sign=-1 if side=='r' else 1
            targets=[unit([sign*.59,.79,-.17]),unit([sign*.22,.96,-.14]),unit([sign*.18,.96,-.22])]
        else:
            s=np.radians(spread*(-1 if side=='l' else 1))
            targets=[unit([np.sin(s),np.cos(s)*np.cos(np.radians(bend)),-np.sin(np.radians(bend))])
                     for bend in (10,23,32)]
        rest=[unit(p2-p1),unit(p3-p2),unit(p3-p2)]
        target_heads=[p1,p1+targets[0]*np.linalg.norm(p2-p1)]
        target_heads.append(target_heads[1]+targets[1]*np.linalg.norm(p3-p2))
        for name,old_head,new_head,axis,direction in zip(names,[p1,p2,p3],target_heads,rest,targets):
            rotation=align(axis,direction)
            transforms[name]=(rotation,new_head-rotation@old_head)
    posed=np.zeros_like(positions)
    for vi,weights in enumerate(data['weights']):
        for bone,weight in weights.items():
            rotation,offset=transforms.get(bone,(np.eye(3),np.zeros(3)))
            posed[vi]+=(rotation@positions[vi]+offset)*weight
    faces=np.asarray(data['triangles'])
    own=np.array([sum(v for n,v in w.items() if n.endswith('_'+side))>.5 for w in data['weights']])
    selected=np.flatnonzero(own[faces].all(1))
    return posed,selected

def build(definition,material):
    brown=definition=='ue_field_gloves'
    source=R/'FullShell/M4.json' if brown else P/'SourceAssets/ModularOutfit20260925/FittedFieldGlovesV1/Authored/M4.json'
    data=read(source)
    bones=read(R/'FullShell/M4.json')['bones']
    anatomy=read(P/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json')['anatomy']
    all_positions=[];all_faces=[];uvs={k:[] for k in ('uv','uv1','uv2') if k in data}
    # A single hero glove has one unambiguous silhouette. In particular,
    # fingers, empty finger mouths and cuffs cannot merge with a second glove.
    poses=[('r',(25,28,-6),(0,0,0),1.0)] if brown else [
           ('r',(-10,18,-6),(0,0,0),1.0)]
    for side,angles,offset,scale in poses:
        positions,selected=posed_surface(data,bones,anatomy,side)
        faces=np.asarray(data['triangles'])[selected]
        used=np.unique(faces);remap={int(v):i+len(all_positions) for i,v in enumerate(used)}
        rotation=np.array(Euler(np.radians(angles),'XYZ').to_matrix())
        # Centre each glove about its palm before rigid display placement.
        centre=np.array([0,7.5,0])
        q=((positions[used]-centre)*.01*scale)@rotation.T+np.asarray(offset)
        all_positions.extend(q.tolist());all_faces.extend([[remap[int(v)] for v in f] for f in faces])
        for key in uvs:uvs[key].extend([data[key][fi] for fi in selected])
    mesh=bpy.data.meshes.new(definition+'_NaturalDisplay')
    mesh.from_pydata(all_positions,[],all_faces);mesh.update()
    obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    for key,values in uvs.items():
        name={'uv':'LeatherMetric25cm','uv1':'PalmAndEdgeDistance','uv2':'StitchArcAndLining'}[key]
        layer=mesh.uv_layers.new(name=name)
        for face,coords in zip(mesh.polygons,values):
            for loop,(u,v) in zip(face.loop_indices,coords):layer.data[loop].uv=(u,1-v) if key=='uv' else (u,v)
    for face in mesh.polygons:face.use_smooth=True
    mesh.uv_layers.active_index=0
    for i,layer in enumerate(mesh.uv_layers):layer.active_render=i==0
    if not brown:
        # The worn glove has no visible lining. Give the icon copy a thin
        # inward lining so its empty wrist reads as an opening, not a skin cap.
        lining=obj.modifiers.new('IconOnlyLeatherLining','SOLIDIFY')
        lining.thickness=.0007;lining.offset=-1
    obj['SourceMesh']=str(source)
    obj['Contract']='One empty right glove; no skin or secondary glove; current native mesh; bone lengths preserved; icon-only pose'
    obj['IconPose']=json.dumps(poses)
    return obj

def brown_seams(material):
    """Render the existing glove's edge-distance/stitch fields and dark lining."""
    nodes=material.node_tree.nodes;links=material.node_tree.links
    bsdf=nodes.get('Principled BSDF')
    colour=bsdf.inputs['Base Color'].links[0].from_socket
    def math(op,a,b=None):
        n=nodes.new('ShaderNodeMath');n.operation=op
        for i,value in enumerate([a,b] if b is not None else [a]):
            if isinstance(value,(int,float)):n.inputs[i].default_value=value
            else:links.new(value,n.inputs[i])
        return n.outputs[0]
    def uv(name):
        n=nodes.new('ShaderNodeUVMap');n.uv_map=name
        s=nodes.new('ShaderNodeSeparateXYZ');links.new(n.outputs['UV'],s.inputs[0])
        return s.outputs
    def gaussian(value,centre,width):
        q=math('DIVIDE',math('SUBTRACT',value,centre),width)
        return math('EXPONENT',math('MULTIPLY',math('MULTIPLY',q,q),-1))
    fields=uv('PalmAndEdgeDistance');details=uv('StitchArcAndLining')
    band=gaussian(fields['Y'],.25,.045)
    periodic=math('ABSOLUTE',math('SUBTRACT',math('FRACT',math('DIVIDE',details['X'],.26)),.5))
    thread=math('MULTIPLY',band,math('LESS_THAN',periodic,.34))
    thread=math('MULTIPLY',thread,math('SUBTRACT',1,details['Y']))
    dark=nodes.new('ShaderNodeMixRGB');dark.blend_type='MULTIPLY';dark.inputs[0].default_value=1
    links.new(colour,dark.inputs[1]);links.new(math('SUBTRACT',1,math('MULTIPLY',details['Y'],.38)),dark.inputs[2])
    stitch=nodes.new('ShaderNodeMixRGB');stitch.blend_type='MIX'
    links.new(math('MULTIPLY',thread,.66),stitch.inputs[0]);links.new(dark.outputs[0],stitch.inputs[1])
    stitch.inputs[2].default_value=(.21,.12,.054,1);links.new(stitch.outputs[0],bsdf.inputs['Base Color'])
    return material

def black_seams(material):
    """Use the existing V7 glove construction mask instead of drawing new seams."""
    nodes=material.node_tree.nodes;links=material.node_tree.links
    bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    colour=bsdf.inputs['Base Color'].links[0].from_socket
    rough=bsdf.inputs['Roughness'].links[0].from_socket
    tex=nodes.new('ShaderNodeTexImage')
    tex.image=bpy.data.images.load(str(P/'SourceAssets/ModularOutfit20260925/FieldGlovesLeatherV1/T_FieldGloves_LeatherRegions.png'),check_existing=True)
    tex.image.colorspace_settings.name='Non-Color'
    channels=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],channels.inputs[0])
    def math(op,a,b):
        n=nodes.new('ShaderNodeMath');n.operation=op
        for i,value in enumerate((a,b)):
            if isinstance(value,(int,float)):n.inputs[i].default_value=value
            else:links.new(value,n.inputs[i])
        return n.outputs[0]
    tone=math('SUBTRACT',1,math('MULTIPLY',channels.outputs['Blue'],.224))
    mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
    links.new(colour,mix.inputs[1]);links.new(tone,mix.inputs[2]);links.new(mix.outputs[0],bsdf.inputs['Base Color'])
    field=math('ADD',math('ADD',.42,math('MULTIPLY',channels.outputs['Green'],.21)),math('MULTIPLY',rough,.24))
    links.new(field,bsdf.inputs['Roughness'])
    return material
