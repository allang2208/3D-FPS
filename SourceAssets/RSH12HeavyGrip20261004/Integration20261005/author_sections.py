"""Add a replaceable factory grip material section, without changing geometry or rig."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent.parent;O.mkdir(exist_ok=True)
raw=json.loads((S/'RSH12Integration20261003/canonical_parts.json').read_text())
grip=next(p for p in raw if p['name']=='9_l');records={}
for side in ('single','r','l'):
    source=S/'RSH12Speedloader20261003'/('Single' if side=='single' else 'Dual/'+side)
    bpy.ops.wm.open_mainfile(filepath=str(source/('RSH12_'+side+'_Editable.blend')))
    bpy.context.preferences.filepaths.save_version=0
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    rig.data.pose_position='REST'
    meta=json.loads((source/'authoring.json').read_text())
    frame=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local@Matrix(meta['alignment'])
    slot=bpy.data.materials.new('M_RSH12_FactoryGrip')
    selected=[];faces=0
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH' or not any(m.type=='ARMATURE' and m.object==rig for m in ob.modifiers):continue
        local=ob.matrix_world.inverted()@frame
        points={tuple(round(float(c),5) for c in local@Vector(v)) for v in grip['verts']}
        indices={v.index for v in ob.data.vertices if tuple(round(float(c),5) for c in v.co) in points}
        affected=[p for p in ob.data.polygons if all(i in indices for i in p.vertices)]
        if affected:
            ob.data.materials.append(slot);index=len(ob.data.materials)-1
            for p in affected:p.material_index=index
            faces+=len(affected)
        selected.append(ob)
    if not faces:raise RuntimeError('Factory grip section could not be authored: '+side)
    folder=O/'Host'/side;folder.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for ob in selected:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=rig
    file=folder/meta['mesh']
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE','MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/('RSH12_'+side+'_GripSections.blend')))
    records[side]={'fbx':str(file),'name':file.stem,'skeleton':meta['skeleton'],'factory_grip_faces':faces}
    print('RSH_FACTORY_GRIP_SECTION_AUTHORED',side,faces,flush=True)
(O/'host_sections.json').write_text(json.dumps(records,indent=2))
