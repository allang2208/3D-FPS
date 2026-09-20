"""Focused source diagnosis for the reported right-thumb clipping/twist."""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE=ROOT/'SourceAssets/AxeTwoHandPose20260919/H4/Axe_TwoHand_H4_Idle_Equip_Editable.blend'
if '--delivered' in sys.argv:
    SOURCE=HERE/'Fixed/Axe_ThumbFix_Idle_Equip_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig=bpy.data.objects['SK_Harvest_Axe_Rig']
arms=bpy.data.objects['SK_Manny_Arms_Export']
axe=bpy.data.objects['Harvest_Axe']
scene=bpy.context.scene
rig.animation_data.action=bpy.data.actions['A_Harvest_Axe_Idle']
rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
names=['thumb_01_r','thumb_02_r','thumb_03_r']
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
pose={b.name:b.matrix.copy() for b in rig.pose.bones}
prefix='delivered' if '--delivered' in sys.argv else 'before'
if '--corrected' in sys.argv:
    prefix='after'
    rig.animation_data_clear()
    fitted=json.loads((HERE/'thumb_fit.json').read_text(encoding='utf-8'))
    for n in names:
        parent=rig.pose.bones[n].parent.name
        pose[n]=pose['hand_r']@Matrix(fitted['hand_relative_thumb'][n])
        local_rest=rest[parent].inverted()@rest[n]
        rig.pose.bones[n].matrix_basis=local_rest.inverted()@pose[parent].inverted()@pose[n]
    bpy.context.view_layer.update()
thumb_ids={v.index for v in arms.data.vertices if sum(g.weight for g in v.groups
           if arms.vertex_groups[g.group].name in names)>.25}
dg=bpy.context.evaluated_depsgraph_get()
obj=axe.evaluated_get(dg); mesh=obj.to_mesh()
tree=BVHTree.FromPolygons([obj.matrix_world@v.co for v in mesh.vertices],[tuple(p.vertices) for p in mesh.polygons])
obj.to_mesh_clear()
obj=arms.evaluated_get(dg); mesh=obj.to_mesh()
points=[obj.matrix_world@v.co for v in mesh.vertices]
thumb_faces=[tuple(p.vertices) for p in mesh.polygons if any(i in thumb_ids for i in p.vertices)]
thumb_tree=BVHTree.FromPolygons(points,thumb_faces)
distances=[]
samples=[]
for i in thumb_ids:
    nearest,normal,_,distance=tree.find_nearest(points[i])
    distances.append((distance if (points[i]-nearest).dot(normal)>=0 else -distance)*1000)
    weights={arms.vertex_groups[g.group].name:g.weight for g in arms.data.vertices[i].groups}
    samples.append({'id':i,'distance_mm':distances[-1], 'weights':weights,
                    'in_tool':list((rig.matrix_world@pose['WPN_root']).inverted()@points[i])})
obj.to_mesh_clear()
bones={}
for name in names:
    b=rig.pose.bones[name]
    parent=b.parent.name
    local_rest=rest[parent].inverted()@rest[name]
    basis=local_rest.inverted()@pose[parent].inverted()@pose[name]
    bones[name]={'parent':parent,'basis_quat':list(basis.to_quaternion()),
                 'basis_euler_deg':[math.degrees(x) for x in basis.to_euler()],
                 'basis_scale':list(basis.to_scale()),'basis_translation':list(basis.translation),
                 'position_in_tool':list(pose['WPN_root'].inverted()@pose[name].translation),
                 'local_rest':[list(row) for row in local_rest]}
report={'source':str(SOURCE),'bones':bones,'thumb_vertices':len(thumb_ids),
        'thumb_tool_triangle_pairs':len(thumb_tree.overlap(tree)),
        'thumb_inside_vertex_count':sum(d<-.1 for d in distances),
        'minimum_signed_surface_mm':min(distances),
        'worst_vertices':sorted(samples,key=lambda row:row['distance_mm'])[:10]}
(HERE/(prefix+'_source_diagnosis.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)

# Close source-model views restricted to this reported defect; no PIE or gameplay.
for obj in scene.objects:
    obj.hide_render=obj not in (arms,axe,rig)
def material(name,color):
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);return mat
arms.data.materials.clear()
arms.data.materials.append(material('DiagnosticHand',(.56,.61,.65)))
arms.data.materials.append(material('DiagnosticThumb',(.85,.43,.16)))
for p in arms.data.polygons:p.material_index=1 if any(i in thumb_ids for i in p.vertices) else 0
axe.data.materials.clear();axe.data.materials.append(material('DiagnosticAxe',(.19,.12,.065)))
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'
scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True
scene.display.shading.background_type='WORLD'
scene.world.color=(.07,.07,.07)
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
center=sum((rig.matrix_world@pose[n].translation for n in names),Vector())/3
camera_data=bpy.data.cameras.new('ThumbDiagnosticCamera');camera_data.type='ORTHO';camera_data.ortho_scale=.145
camera=bpy.data.objects.new('ThumbDiagnosticCamera',camera_data);scene.collection.objects.link(camera)
scene.camera=camera
for view,direction in [('player',(-center).normalized()),('side',Vector((1,-.3,.3)).normalized())]:
    camera.location=center+direction*.4
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(HERE/(prefix+'_'+view+'.png'))
    bpy.ops.render.render(write_still=True)
