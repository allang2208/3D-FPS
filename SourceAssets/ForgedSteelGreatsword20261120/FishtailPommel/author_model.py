"""Author the independent fish-tail candidate against the actual forged sword grip rim."""
import json
import math
from pathlib import Path
import bpy
from mathutils import Vector

batch = Path(__file__).resolve().parent
source = batch.parent
bpy.ops.wm.open_mainfile(filepath=str(source/'Integration/ForgedSteelGreatsword_Modular_Editable.blend'))
grip = bpy.data.objects['SM_ForgedSteelGreatsword_Grip_V1']
plane_z = min(p.co.z for p in grip.data.vertices)
rim = {tuple(round(c * 100, 6) for c in p.co[:2]) for p in grip.data.vertices if abs(p.co.z-plane_z)<.000002}
cx,cy = [(min(p[k] for p in rim)+max(p[k] for p in rim))/2 for k in (0,1)]
rim = sorted(rim,key=lambda p: math.atan2(p[1]-cy,p[0]-cx))
mount_z = (grip.matrix_world @ Vector((0,0,plane_z))).z
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0

# The first ring matches the wrist-end leather. The face develops a subdued
# central ridge, two wide forged facets and a slender radiused terminal edge.
# Each ring describes height, half-width, half-depth, central relief and arch.
profiles = [
    (0,0,0,0,0),(.10,0,0,0,0),(.19,0,0,0,0),
    (.30,1.61,1.44,.04,0),(.48,1.59,1.37,.07,0),
    (.74,1.60,1.32,.10,0),(1.14,1.66,1.30,.13,.02),
    (1.85,1.82,1.24,.19,.04),(2.65,2.08,1.16,.23,.10),
    (3.40,2.40,1.06,.27,.20),(4.12,2.75,.94,.29,.37),
    (4.65,3.05,.81,.30,.51),(4.91,3.19,.69,.27,.60),
    (5.02,3.23,.60,.24,.63),(5.11,3.20,.53,.21,.65),
    (5.18,3.14,.44,.16,.66),(5.22,3.08,.38,.12,.66)
]
verts=[]; faces=[]; uvs=[]
angles=[math.atan2(y-cy,x-cx) for x,y in rim]
for j,(z,width,depth,ridge,arch) in enumerate(profiles):
    for (x0,y0),a in zip(rim,angles):
        if j<3:
            s=(1.,1.016,1.002)[j]
            x,y=cx+(x0-cx)*s,cy+(y0-cy)*s
            h=z
        else:
            c,sn=math.cos(a),math.sin(a)
            xx=abs(c)
            # A shallow ridge catches a thin highlight. Broad side planes roll
            # into the outer edge instead of forming a sharp perimeter flange.
            yface=depth*(.93-.22*xx)*min(1.,abs(sn)/.51)+ridge*max(0.,1.-xx/.85)
            x,y=cx+width*c,cy+math.copysign(yface,sn)
            h=z+arch*(1.-xx**1.8)
            if j in (3,4,5):
                w=(.33,.67,1.)[j-3]
                x=cx+(x0-cx)*(1.-w)+(x-cx)*w
                y=cy+(y0-cy)*(1.-w)+(y-cy)*w
        verts.append((x*.01,y*.01,-h*.01))

n=len(rim)
for j in range(len(profiles)-1):
    for i in range(n):
        nx=(i+1)%n
        ids=(j*n+i,(j+1)*n+i,(j+1)*n+nx,j*n+nx)
        faces.append(ids)
        # Develop the section around the full perimeter. The atlas seam sits
        # on the thin side; the two visible faces share the base-sword steel.
        along=(angles[i]+math.pi)/math.tau
        nextalong=(angles[nx]+math.pi)/math.tau+(1 if nx==0 else 0)
        coords=[]
        for ix,step in zip(ids,(along,along,nextalong,nextalong)):
            x,y,z=verts[ix]
            coords.append(((2775.-z*1730.)/4096.,1.-(3470.+(1.-abs(2*step-1.))*31.)/4096.))
        uvs.append(coords)
# Fan triangulation follows the curved distal edge without a flat shelf.
for row,sign in ((0,1),(len(profiles)-1,-1)):
    ring=verts[row*n:(row+1)*n]
    center=len(verts)
    verts.append((cx*.01,cy*.01,0. if sign>0 else -.0593))
    for i in range(n):
        ids=(row*n+i,row*n+(i+1)%n,center)
        if sign<0:ids=ids[::-1]
        faces.append(ids)
        uvs.append([((2828+verts[k][0]*1500)/4096.,1.-(3486+verts[k][1]*850)/4096.) for k in ids])
name='SM_ForgedSteelGreatsword_FishtailPommel'
mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
uv=mesh.uv_layers.new(name='UVMap')
for poly,coords in zip(mesh.polygons,uvs):
    poly.use_smooth=poly.index<n*(len(profiles)-1)
    for k,value in zip(poly.loop_indices,coords):uv.data[k].uv=value
mat=bpy.data.materials.new('M_ForgedSteelGreatsword_Surface_V1')
mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF')
nodes=mat.node_tree.nodes
link=mat.node_tree.links.new
for channel,path,cs in [('base',source/'BladeFinish/ForgedSteelGreatsword_BaseColor.png','sRGB'),('orm',source/'BladeFinish/ForgedSteelGreatsword_MetallicRoughness.png','Non-Color'),('normal',source/'Integration/Textures/ForgedSteelGreatsword_Normal.jpg','Non-Color')]:
    tex=nodes.new('ShaderNodeTexImage')
    tex.image=bpy.data.images.load(str(path))
    tex.image.colorspace_settings.name=cs
    if channel=='base':link(tex.outputs['Color'],bs.inputs['Base Color'])
    elif channel=='orm':
        sep=nodes.new('ShaderNodeSeparateColor');link(tex.outputs['Color'],sep.inputs['Color'])
        link(sep.outputs['Green'],bs.inputs['Roughness']);link(sep.outputs['Blue'],bs.inputs['Metallic'])
    else:
        nm=nodes.new('ShaderNodeNormalMap');link(tex.outputs['Color'],nm.inputs['Color']);link(nm.outputs['Normal'],bs.inputs['Normal'])
mesh.materials.append(mat)
obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(batch/'FishtailPommel.blend'),compress=True)
bpy.ops.export_scene.fbx(filepath=str(batch/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,use_triangles=True,add_leaf_bones=False,bake_anim=False)
(batch/'candidate.json').write_text(json.dumps({'status':'visual_candidate','socket':'forged_steel_greatsword_hilt_v1','mesh':name,'mount_z_cm':round(mount_z*100,3),'rim_vertices':n,'width_cm':round((max(x for x,y,z in verts)-min(x for x,y,z in verts))*100,2),'length_cm':round(-min(z for x,y,z in verts)*100,2),'material_slot':mat.name},indent=2))
