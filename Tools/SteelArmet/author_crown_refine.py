"""Reshape the active V5 crown in place, preserving lower plates and source UVs."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

P=Path('D:/FPS3D/FPSGAME')
BASE=P/'SourceAssets/SteelArmet20261019/ReferenceMatchV5'
OUT=P/'SourceAssets/SteelArmet20261019/CrownRefine20261020'
for folder in ('Authored','Exports'):(OUT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Exports/SteelArmet_Detailed.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
parts=[ob for ob in scene.objects if ob.type=='MESH' and
       not any(c.name.startswith('REFERENCE_') for c in ob.users_collection)]

# Above the temples, reduce the dome shoulders and form a sloping crown.
# The monotone cubic fields carry shell, reinforcement, edging, lining and
# upper hinge straps together. Below 5.5 cm above the eyes nothing moves.
heights=[4.,5.5,8.,10.3,11.8,12.8,13.5,13.8,14.4]
new_heights=[4.,5.5,8.8,12.1,14.15,15.4,16.2,16.55,17.15]
x_scales=[1.,1.,.94,.78,.60,.48,.40,.40,.40]
y_scales=[1.,1.,.96,.92,.87,.76,.66,.66,.66]

def curve(values,z):
    slopes=[(values[i+1]-values[i])/(heights[i+1]-heights[i])
            for i in range(len(heights)-1)]
    tangents=[slopes[0]]
    for i in range(1,len(heights)-1):
        left,right=slopes[i-1],slopes[i]
        a,b=heights[i]-heights[i-1],heights[i+1]-heights[i]
        tangents.append((3*(a+b))/((2*b+a)/left+(b+2*a)/right) if left*right>0 else 0.)
    tangents.append(slopes[-1])
    if z>=heights[-1]:return values[-1]+(z-heights[-1])*tangents[-1]
    i=next(i for i in range(len(heights)-1) if z<=heights[i+1])
    h=heights[i+1]-heights[i];t=(z-heights[i])/h
    return ((2*t**3-3*t*t+1)*values[i]+(t**3-2*t*t+t)*h*tangents[i]+
            (-2*t**3+3*t*t)*values[i+1]+(t**3-t*t)*h*tangents[i+1])

changed=[]
for ob in parts:
    matrix=ob.matrix_world
    inverse=matrix.inverted()
    moved=0
    for vertex in ob.data.vertices:
        p=matrix@vertex.co
        z=p.z*100
        if z<=5.5:continue
        p.x*=curve(x_scales,z)
        p.y*=curve(y_scales,z)
        p.z=curve(new_heights,z)*.01
        vertex.co=inverse@p
        moved+=1
    if not moved:continue
    if ob.data.has_custom_normals:
        ob.data.normals_split_custom_set([(0.,0.,0.)]*len(ob.data.loops))
    # The reinforcement shares the median fold of the two skull halves.
    # Keep its existing worked perimeter bevels and thickness.
    if ob.name=='Swept crown reinforcement':
        for edge in ob.data.edges:
            a,b=[matrix@ob.data.vertices[i].co for i in edge.vertices]
            if abs(a.x)<.000001 and abs(b.x)<.000001:
                edge.use_edge_sharp=True
    ob.data.update()
    changed.append(dict(part=ob.name,moved_vertices=moved))

materials=['ForgedSteel','CharcoalLining','WorkedEdges','DarkenedSteel','WaxedStitch']
def export_mesh(path,view=None):
    positions=[];triangles=[];normals=[];uv=[];slots=[]
    deps=bpy.context.evaluated_depsgraph_get()
    for ob in parts:
        evaluated=ob.evaluated_get(deps);me=evaluated.to_mesh()
        me.calc_loop_triangles();offset=len(positions)
        matrix=ob.matrix_world;normal_matrix=matrix.to_3x3().inverted().transposed()
        for vertex in me.vertices:
            p=matrix@vertex.co
            if view:
                q=view@p;positions.append([-q.z*100,q.x*100,q.y*100])
            else:positions.append([p.x*100,-p.y*100,p.z*100])
        layer=me.uv_layers.active
        for triangle in me.loop_triangles:
            triangles.append([offset+i for i in triangle.vertices])
            slots.append(materials.index(ob.data.materials[triangle.material_index].name))
            ns=[];coords=[]
            for li in triangle.loops:
                n=(normal_matrix@me.corner_normals[li].vector).normalized()
                if view:
                    q=view.to_3x3()@n;ns.append([-q.z,q.x,q.y])
                else:ns.append([n.x,-n.y,n.z])
                a,b=layer.data[li].uv;coords.append([a,1-b])
            normals.append(ns);uv.append(coords)
        evaluated.to_mesh_clear()
    data=dict(profile='SteelArmetCrownRefine',positions=positions,triangles=triangles,
              normals=normals,uv=uv,triangle_materials=slots,material_slots=materials)
    path.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    return len(triangles)

cam=scene.camera
cam.location=(.59,-.85,.22)
cam.rotation_euler=(Vector((0,-.012,.004))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=.41
bpy.context.view_layer.update()
count=export_mesh(OUT/'Authored/helmet.json')
export_mesh(OUT/'Authored/display.json',cam.matrix_world.inverted())
bpy.ops.object.select_all(action='DESELECT')
for ob in parts:ob.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.export_scene.fbx(filepath=str(OUT/'Exports/SteelArmet_CrownRefine.fbx'),
    use_selection=True,object_types={'MESH'},bake_anim=False,axis_forward='-Y',
    axis_up='Z',mesh_smooth_type='FACE')
scene['design_reference']='Original UserReference.png: peaked, folded upper crown'
scene['asset_status']='CrownRefine20261020; runtime testing remains user-side'
scene.render.resolution_x=640;scene.render.resolution_y=640
scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.render.filepath=str(OUT/'ue_steel_armet.png')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Exports/SteelArmet_CrownRefine.blend'))
# The catalog icon is a required game asset, not a review render.
bpy.ops.render.render(write_still=True)
(OUT/'authored.json').write_text(json.dumps(dict(completed=True,
    base_revision='ReferenceMatchV5',geometry_revision='crown-fold-20261020',
    source_reference='SourceAssets/SteelArmet20261019/Design/UserReference.png',
    triangles=count,parts=len(parts),changed_parts=changed,
    old_crown_peak_cm=13.8,new_crown_peak_cm=16.55,warp_starts_cm=5.5,
    material_slots=materials,uv_preserved=True,topology_preserved=True,
    first_person_overlay_changed=False,runtime_tested=False),indent=2),encoding='utf-8')
print('STEEL_ARMET_CROWN_AUTHORED',count,len(changed),flush=True)
