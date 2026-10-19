"""Editable representative rigs; production shader asset references are retained."""
import json
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentSleeveRepair20261018'
rows=json.loads((R/'inventory.json').read_text())['rows']
for item,profile in [('ue_field_sweater','M16'),('ue_field_sweater_charcoal','SVD'),('ue_chainmail_shirt','RuneSword')]:
    row=next(r for r in rows if r['item']==item and r['profile']==profile)
    old=json.loads(Path(row['file']).read_text());d=json.loads((R/'Authored'/item/(profile+'.json')).read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True);materials=[]
    for i,path in enumerate(old['materials']):
        material=bpy.data.materials.new(path.rsplit('.',1)[1]);material['UE_Material']=path
        material.diffuse_color=(.13,.15,.07,1.) if item=='ue_field_sweater' else (.055,.052,.047,1.) if item=='ue_field_sweater_charcoal' else (.31,.32,.30,1.)
        materials.append(material)
    bones=d['bones'];ordered=sorted(bones,key=lambda n:bones[n]['index']);byid={b['index']:n for n,b in bones.items()};reflection=Matrix.Diagonal((1,-1,1));arm=bpy.data.armatures.new(profile+'_NativeRig');rig=bpy.data.objects.new(arm.name,arm);bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for name in ordered:
        b=bones[name];eb=arm.edit_bones.new(name);axes=Matrix(b['axes']).transposed()
        for i in range(3):axes.col[i]=axes.col[i].normalized()
        matrix=(reflection@axes@reflection).to_4x4();matrix.translation=reflection@Vector(b['position'])*.01;eb.matrix=matrix;eb.length=.025
    for name in ordered:
        parent=bones[name]['parent']
        if parent>=0:arm.edit_bones[name].parent=arm.edit_bones[byid[parent]]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    mesh=bpy.data.meshes.new(item+'_'+profile);mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in d['positions']],[],d['triangles']);mesh.update();ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob)
    for m in materials:mesh.materials.append(m)
    uv=mesh.uv_layers.new(name='Physical25cm')
    for fi,poly in enumerate(mesh.polygons):
        poly.material_index=d['triangle_materials'][fi];poly.use_smooth=True
        for ci,li in enumerate(poly.loop_indices):u,v=d['uv'][fi][ci];uv.data[li].uv=(u,1-v)
    mesh.normals_split_custom_set([(x,-y,z) for face in d['normals'] for x,y,z in face]);groups={n:ob.vertex_groups.new(name=n) for n in {n for ws in d['weights'] for n in ws}}
    for vi,ws in enumerate(d['weights']):
        for n,w in ws.items():groups[n].add([vi],w,'REPLACE')
    if d.get('colors'):
        colors=mesh.color_attributes.new(name='SharedSway',type='FLOAT_COLOR',domain='POINT')
        for i,color in enumerate(d['colors']):colors.data[i].color=color
    ob.parent=rig;ob.modifiers.new('Native binding','ARMATURE').object=rig;ob['Contract']=d['contract']
    bpy.context.scene['ProductionMaterials']='Existing UE shader assets; see material UE_Material properties'
    bpy.context.scene['RemainingNativeVariants']='Authored/<item>/<profile>.json'
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);ob.select_set(True);bpy.context.view_layer.objects.active=ob
    folder=R/'Editable';folder.mkdir(exist_ok=True);name=item+'_'+profile
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/(name+'.blend')))
    bpy.ops.export_scene.fbx(filepath=str(folder/(name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE')
    print('GARMENT_EDITABLE_SAVED',item,profile,flush=True)
