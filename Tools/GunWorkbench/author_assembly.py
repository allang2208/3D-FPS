"""Export real M4 components in one shared assembly frame; no previews or tests."""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector

PROJECT=Path('D:/FPS3D/FPSGAME')
OUT=PROJECT/'SourceAssets/GunWorkbench20260927/Assembly'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(PROJECT/'SourceAssets/M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend'))
rig=bpy.data.objects['SK_M4_Infima']
root=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted()
specs=[('body','枪身',['M4_M4 Body_Export','M4_Trigger Straight Unreal_Export']),
 ('handguard','护木',['M4_Handguard Kmode Unreal_Export']),
 ('stock','枪托',['M4_Stock Classic Unreal_Export']),
 ('grip','握把',['M4_Grip Default Unreal_Export']),
 ('magazine','弹匣',['M4_Magazine Light.003_Export']),
 ('muzzle','枪口件',['M4_Flash Hider Unreal_Export'])]
source={name:bpy.data.objects[name] for _,_,names in specs for name in names}
points=[root@o.matrix_world@v.co for o in source.values() for v in o.data.vertices]
low=Vector([min(v[a] for v in points) for a in range(3)])
high=Vector([max(v[a] for v in points) for a in range(3)])
axes=sorted(range(3),key=lambda a:high[a]-low[a])
# Thin axis becomes height, long axis runs along the mat. One rigid frame for all parts.
rot=Matrix([[float(i==axes[1]) for i in range(3)],
            [float(i==axes[2]) for i in range(3)],
            [float(i==axes[0]) for i in range(3)]])
if rot.determinant()<0:
    rot[0]=-rot[0]
rot=rot.to_4x4()
points=[rot@p for p in points]
low=Vector([min(v[a] for v in points) for a in range(3)])
high=Vector([max(v[a] for v in points) for a in range(3)])
shift=Vector((.82-(low.x+high.x)/2,-(low.y+high.y)/2,.97-low.z))
frame=Matrix.Translation(shift)@rot@root
mirror=Matrix.Diagonal((1,-1,1,1)) # UE static FBX conversion reflects Y.
manifest={'meshes':[],'source':str(PROJECT/'SourceAssets/M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend')}
recipe={'id':'assemble_m4','output':'ue_m4a1','inputs':[{'item':'ironIngot','count':12},{'item':'copperIngot','count':4},{'item':'wood','count':2}],
        'camera':[24,0,181],'look_at':[82,0,96],
        'position_tolerance_cm':5,'angle_tolerance_deg':18,'calibration_seconds':5,'parts':[]}
created=[]
parking=[(59,-35),(106,33),(59,29),(106,-29),(59,51)]
for index,(key,label,names) in enumerate(specs):
    pieces=[]
    for name in names:
        orig=source[name];obj=bpy.data.objects.new(key+'_'+name,orig.data.copy());bpy.context.scene.collection.objects.link(obj)
        source_frame=frame@orig.matrix_world
        obj.data.transform(source_frame)
        if source_frame.determinant()<0:obj.data.flip_normals()
        pieces.append(obj)
    verts=[v.co for o in pieces for v in o.data.vertices]
    lo=Vector([min(v[a] for v in verts) for a in range(3)]);hi=Vector([max(v[a] for v in verts) for a in range(3)])
    center=(lo+hi)*.5;extent=(hi-lo)*50
    for obj in pieces:
        obj.data.transform(mirror@Matrix.Translation(-center))
        obj.data.flip_normals() # A baked handedness change must reverse face winding too.
    bpy.ops.object.select_all(action='DESELECT')
    for obj in pieces:obj.select_set(True)
    bpy.context.view_layer.objects.active=pieces[0]
    if len(pieces)>1:bpy.ops.object.join()
    obj=pieces[0];obj.name='SM_GA_'+key;obj.data.name=obj.name
    tri=obj.modifiers.new('Assembly export triangles','TRIANGULATE');tri.keep_custom_normals=True
    bpy.ops.object.modifier_apply(modifier=tri.name)
    path='/Game/Building/GunWorkbench20260927/Assembly/'+obj.name
    mats=[m.name for m in obj.data.materials]
    bpy.ops.export_scene.fbx(filepath=str(OUT/(obj.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
    manifest['meshes'].append({'name':obj.name,'path':path,'materials':mats,'fbx':str(OUT/(obj.name+'.fbx'))})
    if key=='body':recipe['body_mesh']=path;recipe['body_position']=list(center*100)
    else:
        x,y=parking[index-1]
        recipe['parts'].append({'id':key,'name':label,'mesh':path,'target':list(center*100),
            'extent':list(extent),'loose':[x,y,95.3+extent.z],
            'angle':[25,-35,55,-45,70][index-1],'radius':max(3.5,min(extent.x,extent.y)+1.5)})
    created.append(obj)
for obj in list(bpy.data.objects):
    if obj not in created:bpy.data.objects.remove(obj,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M4_AssemblyParts.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
catalog_path=PROJECT/'Content/ColdSteelData/gun-assembly.json'
previous=json.loads(catalog_path.read_text(encoding='utf-8-sig')) if catalog_path.exists() else {'recipes':[]}
recipes=previous.get('recipes',[previous] if 'id' in previous else [])
recipes=[r for r in recipes if r['id']!=recipe['id']]
recipes.insert(0,recipe)
catalog_path.write_text(json.dumps({'recipes':recipes},ensure_ascii=False,indent=2),encoding='utf-8')
print('ASSEMBLY_PARTS_EXPORTED '+json.dumps({'parts':len(created),'gun_size_cm':list((high-low)*100)}))
