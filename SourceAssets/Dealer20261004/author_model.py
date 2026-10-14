"""Thin rounded cards in UE centimetres; no camera, lights or preview rendering."""
import bpy
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'Export'
OUT.mkdir(parents=True,exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
# Author UE centimetres as Blender units. FBX_SCALE_ALL retains raw vertex coordinates.
bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=.01


def outline(w,h,r):
    points=[]
    for cy,cz,angle in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
        for i in range(9):
            t=math.radians(angle+i*90/8)
            points.append((cy+r*math.cos(t),cz+r*math.sin(t)))
    return points


def card():
    rings=[(-.035,6.27,8.77,.285),(-.023,6.3,8.8,.3),(.023,6.3,8.8,.3),(.035,6.27,8.77,.285)]
    verts=[]
    for depth,w,h,r in rings:verts += [(depth,y,z) for y,z in outline(w,h,r)]
    n=len(verts)//4
    faces=[tuple(reversed(range(n))),tuple(range(n*3,n*4))]
    slots=[0,1]
    for k in range(3):
        for i in range(n):
            j=(i+1)%n
            faces.append((k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i));slots.append(2)
    mesh=bpy.data.meshes.new('DealerCardGeometry');mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new('SM_DealerCard',mesh);bpy.context.collection.objects.link(obj)
    for name in ['DealerFace','DealerBack','DealerEdge']:mesh.materials.append(bpy.data.materials.new(name))
    uv=mesh.uv_layers.new(name='UVMap')
    for poly,slot in zip(mesh.polygons,slots):
        poly.material_index=slot
        poly.use_smooth=slot==2
        for li in poly.loop_indices:
            x,y,z=mesh.vertices[mesh.loops[li].vertex_index].co
            # Unreal FBX flips source Y and V. This puts the face's top-left UV at (0,0).
            uv.data[li].uv=(.5-y/6.3,.5+z/8.8)
    obj['author_units']='UE centimetres';obj['dimensions_cm']='6.3 x 8.8 x 0.07'
    return obj


def badge():
    mesh=bpy.data.meshes.new('DealerResultGeometry')
    mesh.from_pydata([(-.045,-10,-1.75),(-.045,-10,1.75),(-.045,10,1.75),(-.045,10,-1.75)],[],[(0,1,2,3)])
    mesh.materials.append(bpy.data.materials.new('DealerResult'))
    uv=mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            x,y,z=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=(.5-y/20,.5+z/3.5)
    obj=bpy.data.objects.new('SM_DealerResult',mesh);bpy.context.collection.objects.link(obj)
    return obj


objects=[card(),badge()]
manifest=[]
for obj in objects:
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    export=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(export),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,apply_scale_options='FBX_SCALE_ALL',embed_textures=False)
    manifest.append({'name':obj.name,'fbx':str(export),'slots':[m.name for m in obj.data.materials],
        'triangles':sum(len(p.vertices)-2 for p in obj.data.polygons)})
# Keep the original images alongside the editable geometry, packed in the .blend.
for name in ['T_DealerFaces','T_DealerBack','T_DealerResults']:
    image=bpy.data.images.load(str(OUT/'Textures'/(name+'.png')),check_existing=True);image.pack()

def source_material(material,image_name,index=None,columns=13,rows=4):
    material.use_nodes=True
    nodes=material.node_tree.nodes;links=material.node_tree.links
    nodes.clear()
    bsdf=nodes.new('ShaderNodeBsdfPrincipled');bsdf.inputs['Roughness'].default_value=.32
    output=nodes.new('ShaderNodeOutputMaterial');links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.get(image_name+'.png')
    links.new(tex.outputs['Color'],bsdf.inputs['Base Color']);links.new(tex.outputs['Alpha'],bsdf.inputs['Alpha'])
    if index is not None:
        uv=nodes.new('ShaderNodeTexCoord')
        scale=nodes.new('ShaderNodeVectorMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=(1/columns,1/rows,1)
        offset=nodes.new('ShaderNodeVectorMath');offset.operation='ADD'
        offset.inputs[1].default_value=(index%columns/columns,(rows-1-index//columns)/rows,0)
        links.new(uv.outputs['UV'],scale.inputs[0]);links.new(scale.outputs['Vector'],offset.inputs[0]);links.new(offset.outputs['Vector'],tex.inputs['Vector'])

source_material(bpy.data.materials['DealerFace'],'T_DealerFaces',0)
source_material(bpy.data.materials['DealerBack'],'T_DealerBack')
source_material(bpy.data.materials['DealerResult'],'T_DealerResults',0,3,3)
# The author file exposes all 52 front designs as linked geometry, while UE uses one reusable mesh.
collection=bpy.data.collections.new('Deck52Variants');bpy.context.scene.collection.children.link(collection)
for index in range(52):
    obj=objects[0].copy();collection.objects.link(obj)
    obj.name=f'DealerCard_{index:02d}';obj.location=(0,(index%13-6)*7.2,(index//13+1)*10)
    obj['card_id']=index
    mat=bpy.data.materials['DealerFace'].copy();mat.name=f'DealerFace_{index:02d}'
    source_material(mat,'T_DealerFaces',index)
    obj.material_slots[0].link='OBJECT';obj.material_slots[0].material=mat
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'DealerDeck.blend'))
(OUT/'meshes.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(ROOT/'model-receipt.json').write_text(json.dumps({'complete':True,'meshes':manifest,'blend':str(ROOT/'DealerDeck.blend'),
    'card_dimensions_cm':[6.3,8.8,.07],'corner_radius_cm':.3,'runtime_tested':False,'rendered':False},indent=2),encoding='utf-8')
print('DEALER_MODELS_SAVED meshes=2 rendered=false')
