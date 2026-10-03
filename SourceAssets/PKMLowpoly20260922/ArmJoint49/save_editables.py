"""Update PKM's existing editable outfits without changing their geometry/materials."""
import hashlib,json,shutil
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
ROOT=PROJECT/'SourceAssets/ModularOutfit20260925'
OUT=HERE/'Editable';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report={}
native=json.loads((HERE/'Inputs/BarePalmV7.json').read_text())['bones']
reflection=Matrix.Diagonal((1,-1,1));indices={v['index']:n for n,v in native.items()}
for family in ['HuntFieldGlovesV1','FittedFieldGlovesV1','FittedSleevesV1']:
    source=ROOT/family/'Editable'/f'PKM_{family}.blend';before=sha(source)
    data=json.loads((HERE/'Authored'/f'{family}.json').read_text())
    # The previous editable uses an older surface snapshot. Rebuild from the
    # now-published native authoring data, retaining that older file as backup.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm=bpy.data.armatures.new('PKM_NativeReference');rig=bpy.data.objects.new(arm.name,arm)
    bpy.context.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for name,bone in native.items():
        edit=arm.edit_bones.new(name);q=bone['q'];rot=Quaternion((q[3],q[0],q[1],q[2])).to_matrix()
        matrix=(reflection@rot@reflection).to_4x4();matrix.translation=reflection@Vector(bone['p'])*.01
        edit.matrix=matrix;edit.length=.025
    for name,bone in native.items():
        if bone['parent'] in indices:arm.edit_bones[name].parent=arm.edit_bones[indices[bone['parent']]]
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh=bpy.data.meshes.new('PKM_'+family)
    mesh.from_pydata([(p[0]*.01,-p[1]*.01,p[2]*.01) for p in data['positions']],[],data['triangles']);mesh.update()
    obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(obj);obj.parent=rig
    obj.modifiers.new('NativeBinding','ARMATURE').object=rig
    colors={'HuntFieldGlovesV1':(.18,.085,.035,1),'FittedFieldGlovesV1':(.025,.03,.035,1),'FittedSleevesV1':(.15,.18,.10,1)}
    mat=bpy.data.materials.new(family+'_Authoring');mat.diffuse_color=colors[family];mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=mat.diffuse_color
    shader.inputs['Roughness'].default_value=.72;mesh.materials.append(mat)
    layer=mesh.uv_layers.new(name='NativeUV');normals=[]
    for face,uv,ns in zip(mesh.polygons,data['uv'],data['normals']):
        face.use_smooth=True
        for li,(uu,vv),n in zip(face.loop_indices,uv,ns):
            layer.data[li].uv=(uu,1-vv);normals.append((n[0],-n[1],n[2]))
    mesh.normals_split_custom_set(normals)
    for name in sorted({n for w in data['weights'] for n in w}):obj.vertex_groups.new(name=name)
    for vi,weights in enumerate(data['weights']):
        for name,weight in weights.items():obj.vertex_groups[name].add([vi],weight,'REPLACE')
    obj['Contract']=data['contract'];obj['PKMArmJointRevision']='ArmJoint49'
    obj['BareAuthoredSHA256']=data['bare_authored_sha256']
    output=OUT/source.name;bpy.ops.wm.save_as_mainfile(filepath=str(output))
    if sha(source)!=before:raise RuntimeError('Overlapping editable edit: '+family)
    backup=HERE/'Before/Editables'/source.name;backup.parent.mkdir(exist_ok=True,parents=True)
    if not backup.exists():shutil.copy2(source,backup)
    shutil.copy2(output,source)
    report[family]={'file':str(source),'before_sha256':before,'after_sha256':sha(source),'saved':True}
    print('PKM_JOINT49_EDITABLE_SAVED',family,flush=True)
(HERE/'editables_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
