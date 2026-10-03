"""Export native rigs with only the factory black compensator in a new slot."""
import bpy,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'PitViper2011Integration20261002'
OUT=O/'Integration20261003';OUT.mkdir(exist_ok=True)
records={}
for key,relative in [('single','Single'),('r','Dual/r'),('l','Dual/l')]:
    folder=S/relative;auth=json.loads((folder/'authoring.json').read_text())
    source=folder/('PitViper2011_'+key+'_Editable.blend')
    bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.preferences.filepaths.save_version=0
    rig=bpy.data.objects[Path(auth['mesh']).stem]
    target=bpy.data.materials.get('M_PitViper2011_FactoryCompensator') or bpy.data.materials.new('M_PitViper2011_FactoryCompensator')
    split=0;objects=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH' or not (ob.parent==rig or any(m.type=='ARMATURE' and m.object==rig for m in ob.modifiers)):continue
        objects.append(ob)
        group=ob.vertex_groups.get('WPN_Barrel')
        if not group:continue
        weighted={v.index for v in ob.data.vertices if any(g.group==group.index and g.weight>.99 for g in v.groups)}
        old={i for i,m in enumerate(ob.data.materials) if m and m.name.split('.')[0]=='M_PitViper2011_h-190'}
        old|={i for i,m in enumerate(ob.data.materials) if m and m.name.split('.')[0]=='M_PitViper2011_h_190'}
        selected=[p for p in ob.data.polygons if p.material_index in old and all(i in weighted for i in p.vertices)]
        if not selected:continue
        index=len(ob.data.materials);ob.data.materials.append(target)
        for p in selected:p.material_index=index
        split+=sum(len(p.vertices)-2 for p in selected)
    if not split:raise RuntimeError('No original black compensator triangles found for '+key)
    # Export the same rest rig; animation actions, arm shape and all other
    # material/normal/UV/weight data remain in their existing authoring state.
    rig.animation_data_clear();rig.data.pose_position='REST'
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [rig]+objects:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=rig
    out=OUT/relative;out.mkdir(parents=True,exist_ok=True)
    fbx=out/auth['mesh']
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',
       add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=False)
    blend=out/('PitViper2011_'+key+'_CompensatorSections.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    # The normal reimport entry still reads the original FBX filename.
    previous=folder/auth['mesh'];backup=OUT/'Before'/relative/auth['mesh'];backup.parent.mkdir(parents=True,exist_ok=True)
    if previous.exists() and not backup.exists():shutil.copy2(previous,backup)
    shutil.copy2(fbx,previous)
    records[key]={'fbx':str(fbx),'blend':str(blend),'source':str(source),'name':Path(auth['mesh']).stem,
        'folder':'/Game/Weapons/PitViper2011/Integrated20261002/'+relative,
        'factory_compensator_triangles':split,'sha256':hashlib.sha256(fbx.read_bytes()).hexdigest()}
(OUT/'body_sections.json').write_text(json.dumps({'families':records,'status':'authored_and_exported','game_tested':False},indent=2),encoding='utf8')
print('PIT_VIPER_FACTORY_COMPENSATOR_SECTIONS_AUTHORED '+json.dumps({k:v['factory_compensator_triangles'] for k,v in records.items()}),flush=True)
