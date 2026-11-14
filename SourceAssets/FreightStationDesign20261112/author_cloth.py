"""A folded cotton shop cloth cut to the existing cart handle, in UE centimetres."""
from pathlib import Path
import bpy, math
from math import sin, cos, pi
root=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
# The rail spans local workshop y=213..267, at x=1070, z=73.
# Its triangular export has a 1.20 cm lateral and 0.807 cm vertical radius.
width_steps, cross_steps=30,48
verts=[];faces=[];uvs=[]
for j in range(cross_steps+1):
    s=j/cross_steps
    for i in range(width_steps+1):
        t=i/width_steps
        folds=.60*sin(5*pi*t+.4)+.32*sin(11*pi*t)+.19*sin(2*pi*t)
        if s<.55:
            f=1-s/.55; drop=f*(33.7+3.2*sin(pi*t)+2.7*t+.38*sin(11*pi*t))
            x=-(1.28+f*(2.3+1.6*folds)); z=-drop
        elif s<=.66:
            u=(s-.55)/.11
            x=-1.28*cos(pi*u);z=.88*sin(pi*u)
            f=0
        else:
            f=(s-.66)/.34;drop=f*(13.5+4.8*t+2*sin(pi*t)+.4*sin(13*pi*t))
            x=1.28+f*(1.7+1.15*folds);z=-drop
        y=(t-.5)*(28+2.3*f)+.75*f*sin(3*pi*t+.2)
        verts.append((x*.01,-y*.01,z*.01));uvs.append((t,s))
for j in range(cross_steps):
    for i in range(width_steps):
        a=j*(width_steps+1)+i;b=a+1;c=b+width_steps+1;e=c-1
        faces.append((e,c,b,a))
name='SM_CartHandleCloth'
mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
mesh.materials.append(bpy.data.materials.new('Cotton'))
uv=mesh.uv_layers.new(name='UVMap')
for face in mesh.polygons:
    face.use_smooth=True
    for li in face.loop_indices:uv.data[li].uv=uvs[mesh.loops[li].vertex_index]
bpy.context.view_layer.objects.active=ob;ob.select_set(True)
shell=ob.modifiers.new('Folded textile edges','SOLIDIFY');shell.thickness=.0011;shell.offset=0
bpy.ops.object.modifier_apply(modifier=shell.name)
bpy.ops.export_scene.fbx(filepath=str(root/(name+'.fbx')),use_selection=True,axis_forward='-Y',axis_up='Z',use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False)
