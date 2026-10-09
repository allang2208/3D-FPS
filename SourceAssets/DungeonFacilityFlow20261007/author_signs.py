import bpy,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Authored';BASE='/Game/Dungeons/FacilityFlow20261007'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
material=bpy.data.materials.new('FF_Pairs');records=[]
for row in json.loads((ROOT/'pair-signs.json').read_text('utf8')):
    name='SM_FacilityPair_'+row['key'];mesh=bpy.data.meshes.new(name)
    # Fixed 4:1 proportions, with space above the existing canopy and name card.
    mesh.from_pydata([(-1.25,-.24,4.6875),(1.25,-.24,4.6875),(1.25,-.24,5.3125),(-1.25,-.24,5.3125)],[],[(0,1,2,3)])
    mesh.materials.append(material);uv=mesh.uv_layers.new(name='UVMap');x,y,xx,yy=row['rect']
    for i,p in enumerate([(x/4096,1-yy/2048),(xx/4096,1-yy/2048),(xx/4096,1-y/2048),(x/4096,1-y/2048)]):uv.data[i].uv=p
    mesh.update();obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    fbx=OUT/(name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',path_mode='STRIP')
    records.append(dict(name=name,key=row['key'],kind='PairSign',mesh=BASE+'/Meshes/'+name,fbx=str(fbx),sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),materials={'FF_Pairs':BASE+'/Materials/M_FacilityRoutePairs'},collision=False,nanite=False,cast_shadow=False))
(ROOT/'sign-geometry.json').write_text(json.dumps(dict(meshes=records),indent=2),encoding='utf8')
