"""Fit the socket to the original grip and give each interlocked link a rigid guide."""
from pathlib import Path
import json
import math
import bpy
from mathutils import Vector

here = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(here.parent/'Integration/ForgedSteelGreatsword_Modular_Editable.blend'))
bpy.context.preferences.filepaths.save_version = 0
grip = bpy.data.objects['SM_ForgedSteelGreatsword_Grip_V1']
lowest = min(v.co.z for v in grip.data.vertices)
rim = {tuple(round(c*100,6) for c in v.co[:2]) for v in grip.data.vertices if abs(v.co.z-lowest)<.000002}
cx = (max(x for x,y in rim)+min(x for x,y in rim))*.5
cy = (max(y for x,y in rim)+min(y for x,y in rim))*.5
rim = sorted(rim,key=lambda p:math.atan2(p[1]-cy,p[0]-cx))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
vertices,faces,loops,bindings = [],[],[],[]
def grid(grid_points,slot,segment,wrap_u,wrap_v):
    # Input grid is periodic on the closed axes. Per-corner UVs preserve the seam.
    nu,nv=len(grid_points),len(grid_points[0])
    start=len(vertices)
    vertices.extend(tuple(c*.01 for c in p) for row in grid_points for p in row)
    ucount=nu if wrap_u else nu-1
    vcount=nv if wrap_v else nv-1
    for i in range(ucount):
        for j in range(vcount):
            corners=((i,j),(i+1,j),(i+1,j+1),(i,j+1))
            faces.append(tuple(start+(a%nu)*nv+(b%nv) for a,b in corners))
            loops.append([(slot*.5+.012+.476*a/ucount,.01+.98*b/vcount) for a,b in corners])
            bindings.append((slot,segment))

def tube(center,axis,side,radius_x,radius_z,wire,segment,slot):
    # Long links are rounded rectangles with two short straight sides.
    center,axis,side=Vector(center),Vector(axis).normalized(),Vector(side).normalized()
    plane_normal=side.cross(axis).normalized()
    path=[]
    for half in (0,1):
        for i in range(29):
            a=math.pi*(half+i/28)
            p=side*(math.cos(a)*radius_x)+axis*(math.sin(a)*radius_x+(1 if half==0 else -1)*(radius_z-radius_x))
            outward=side*math.cos(a)+axis*math.sin(a)
            if radius_x==radius_z and i==28:continue
            path.append((p,outward))
    rows=[]
    for p,radial in path:
        rows.append([center+p+wire*(radial*math.cos(j*math.tau/14)+plane_normal*math.sin(j*math.tau/14)) for j in range(14)])
    grid(rows,slot,segment,True,True)

# The first lip follows every contact vertex of the actual factory handle.
bands=[(.00,1.),(-.10,1.035),(-.23,1.05),(-.32,1.005),(-1.02,.97),
       (-1.30,1.04),(-1.47,1.045),(-1.58,.98),(-1.84,.79),(-2.00,.60)]
rows=[]
for x,y in rim:
    rows.append([Vector((cx+(x-cx)*scale,cy+(y-cy)*scale,z)) for z,scale in bands])
grid(rows,0,0,True,False)
# Cap both ends and seat the fixed oval in its wide lower shoulder.
for bottom in (False,True):
    row=-1 if bottom else 0
    face=[i*len(bands)+(row%len(bands)) for i in range(len(rim))]
    if bottom:face.reverse()
    faces.append(tuple(face));bindings.append((0,0))
    loops.append([(.25+(vertices[i][0]*5),.5+vertices[i][1]*10) for i in face])
ring_center=Vector((cx,cy,-3.48))
tube(ring_center,(0,0,1),(1,0,0),1.90,2.00,.295,0,0)

# At the bottom of the ring the first link is edge-on to the ring. Rigid
# rotations use the contact point between adjacent links as their hinge.
anchor=ring_center+Vector((.35,0,-1.97))
guides=[anchor]
for i in range(7):
    direction=Vector((.20+.055*i, .026*math.sin(i),-1)).normalized()
    guides.append(guides[-1]+1.23*direction)
    length=guides[-1]-guides[-2]
    tangent=Vector((0,1,0))
    if i%2:tangent=length.cross(tangent).normalized()
    else:tangent=(tangent-length.normalized()*length.normalized().dot(tangent)).normalized()
    tube((guides[-2]+guides[-1])*.5,length,tangent,.39,.78,.135,i,1)

name='SM_ForgedSteelGreatsword_RingChainPommel'
mesh=bpy.data.meshes.new(name)
mesh.from_pydata(vertices,[],faces);mesh.update()
uv=mesh.uv_layers.new(name='Surface')
skin=mesh.uv_layers.new(name='RigidLink')
for label in ('Socket','Links'):
    mat=bpy.data.materials.new('M_RingChain_'+label);mat.use_nodes=True
    nodes=mat.node_tree.nodes;link=mat.node_tree.links.new;bs=nodes.get('Principled BSDF')
    for key in ('BaseColor','ORM','Normal'):
        image=bpy.data.images.load(str(here/('T_RingChain_'+key+'.png')),check_existing=True)
        if key!='BaseColor':image.colorspace_settings.name='Non-Color'
        node=nodes.new('ShaderNodeTexImage');node.image=image
        if key=='BaseColor':link(node.outputs['Color'],bs.inputs['Base Color'])
        elif key=='ORM':
            split=nodes.new('ShaderNodeSeparateColor');link(node.outputs['Color'],split.inputs['Color'])
            link(split.outputs['Green'],bs.inputs['Roughness']);link(split.outputs['Blue'],bs.inputs['Metallic'])
        else:
            norm=nodes.new('ShaderNodeNormalMap');link(node.outputs['Color'],norm.inputs['Color']);link(norm.outputs['Normal'],bs.inputs['Normal'])
    mesh.materials.append(mat)
for face,data,(slot,segment) in zip(mesh.polygons,loops,bindings):
    face.material_index=slot;face.use_smooth=len(face.vertices)==4
    for li,p in zip(face.loop_indices,data):
        mesh.uv_layers['Surface'].data[li].uv=p
        mesh.uv_layers['RigidLink'].data[li].uv=(segment,0)
obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
obj.select_set(True);bpy.context.view_layer.objects.active=obj
# Recalculate outward winding on the closed ferrule and each closed interlocking link.
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
mesh.uv_layers.active_index=0
mesh.uv_layers[0].active_render=True
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1.
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(here/'RingChainPommel.blend'))
bpy.ops.export_scene.fbx(filepath=str(here/(name+'.fbx')),use_selection=True,object_types={'MESH'},
                         axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,
                         mesh_smooth_type='FACE',use_tspace=True,use_triangles=True)
def ue(v):return [round(v.x,5),round(-v.y,5),round(v.z,5)]
caps=[[cx,-cy,-.5,cx,-cy,14.,1.47],[cx,-cy,-1.65,cx,-cy,-.5,1.35]]
for j in range(12):
    a=math.tau*j/12;b=math.tau*(j+1)/12
    if math.sin((a+b)/2)<-.85:continue
    def shell(u):return ue(ring_center+Vector((1.90*math.cos(u),0,2.*math.sin(u))))
    caps.append(shell(a)+shell(b)+[.27])
spec={'guides_cm':[ue(p) for p in guides],'skin_uv_channel':1,'particle_radius_cm':.22,
      'inverse_masses':[0,1,1,1,1,1,1,.88],'damping_per_second':5.5,
      'heavy_damping_per_second':5.5,'collision_capsules_cm':caps}
(here/'dynamics.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
