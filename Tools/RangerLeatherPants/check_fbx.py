"""Refresh relative texture references, then inspect actual FBX round trips."""
import json,math,sys
from pathlib import Path
import bpy,numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerLeatherPants20261021';OUT=R/'Review'
profiles=('Jason','Jason_ShortBootsFit','Jason_HighBootsFit');rows=[]
sys.path.insert(0,str(P/'Tools/RangerLeatherPants'));import export as exporter
bpy.ops.wm.open_mainfile(filepath=str(R/'RangerLeatherPants_Editable.blend'))
for profile in profiles:
    ob=bpy.data.objects['SK_'+profile+'_RangerLeatherPants'];rig=ob.parent;ob.hide_set(False);rig.hide_set(False)
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=ob
    exporter.export_fbx(ob,rig,R/'Exports'/(profile+'_RangerLeatherPants.fbx'))
for profile in profiles:
    bpy.ops.wm.read_factory_settings(use_empty=True);file=R/'Exports'/(profile+'_RangerLeatherPants.fbx');bpy.ops.import_scene.fbx(filepath=str(file),use_custom_normals=True,automatic_bone_orientation=False)
    meshes=[o for o in bpy.data.objects if o.type=='MESH'];rigs=[o for o in bpy.data.objects if o.type=='ARMATURE'];ob=meshes[0];mesh=ob.data;mesh.calc_loop_triangles()
    ps=np.array([ob.matrix_world@v.co for v in mesh.vertices]);d=json.loads((R/'Authored/ue_leather_pants'/(profile+'.json')).read_bytes());src=np.array(d['positions'])*[.01,-.01,.01]
    image_files={}
    for img in bpy.data.images:
        if img.source=='FILE':image_files[img.name]=dict(path=bpy.path.abspath(img.filepath),exists=Path(bpy.path.abspath(img.filepath)).exists())
    sums=[sum(g.weight for g in v.groups) for v in mesh.vertices];row=dict(profile=profile,meshes=len(meshes),armatures=len(rigs),vertices=len(mesh.vertices),triangles=len(mesh.loop_triangles),materials=len(mesh.materials),uv_layers=len(mesh.uv_layers),bones=len(rigs[0].data.bones),bounds_error_m=float(max(abs(ps.min(0)-src.min(0)).max(),abs(ps.max(0)-src.max(0)).max())),max_weight_sum_error=float(max(abs(s-1) for s in sums)),missing_images=[n for n,v in image_files.items() if not v['exists']],images=image_files)
    expected={f+'_'+c+'.png' for f in ('WalnutLeather','ReinforcedLeather','OliveTwill') for c in ('BaseColor','Normal','Roughness')};row['unexported_image_channels']=sorted(expected-set(image_files))
    rows.append(row);print('FBX_ROUNDTRIP',profile,row['triangles'],row['bounds_error_m'],row['missing_images'],row['unexported_image_channels'],flush=True)
(OUT/'fbx_report.json').write_text(json.dumps(dict(scope='Actual FBX import in isolated Blender scene; no UE import',models=rows),indent=2),encoding='utf-8')
