"""Manufactured roof service base for the reused Soul City ventilation pieces."""
import bpy,json,math
from pathlib import Path
R=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
materials={}
for name in ['Machined','Rubber','Copper']:
    materials[name]=bpy.data.materials.new(name)
def box(name,p,size,role,bevel=.018):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.name=name;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(materials[role])
    b=o.modifiers.new('Manufactured edge radii','BEVEL');b.width=bevel;b.segments=3;bpy.ops.object.modifier_apply(modifier=b.name)
    # Non-overlapping projected UVs retain the source material's fine-scale normals.
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1519,island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
    return o
for x in (-1.35,1.35):
    for y in (-.85,.85):
        box('BoltedFoot',(x,y,.025),(.32,.32,.05),'Machined',.012)
        box('VibrationPad',(x,y,.065),(.24,.24,.03),'Rubber',.008)
        box('SupportRiser',(x,y,.13),(.16,.16,.10),'Machined',.009)
for y in (-.85,.85):box('Crossmember',(0,y,.145),(3.,.16,.07),'Machined',.01)
box('ServiceDeck',(0,0,.20),(3.2,2.2,.04),'Machined',.012)
for x in (-1.56,1.56):box('DeckEdge',(x,0,.235),(.05,2.16,.07),'Copper',.008)
for x in (-1.35,1.35):
    for y in (-.85,.85):
        for dx in (-.105,.105):
            bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.023,depth=.018,location=(x+dx,y,.06));o=bpy.context.object;o.name='AnchorBolt';o.data.materials.append(materials['Machined'])
bpy.ops.object.select_all(action='SELECT');bpy.context.view_layer.objects.active=next(o for o in bpy.context.scene.objects if o.type=='MESH');bpy.ops.object.join();o=bpy.context.object;o.name='SM_Exterior_ServicePlatform';bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
tri=o.modifiers.new('Production triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'ServicePlatform_Source.blend'))
out=R/'Meshes'/f'{o.name}.fbx';bpy.ops.export_scene.fbx(filepath=str(out),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
(R/'service_platform.json').write_text(json.dumps(dict(name=o.name,fbx=str(out),materials=list(materials),deck_top_cm=22,footprint_cm=[320,220]),indent=2))
print('EXTERIOR_SERVICE_PLATFORM_AUTHORED',flush=True)
