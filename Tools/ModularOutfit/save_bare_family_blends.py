"""Save editable per-rig authoring meshes. UE retains the actual native skeleton."""
import json
from pathlib import Path
import bpy
from mathutils import Matrix,Vector

ROOT=Path(globals().get('AUTHOR_ROOT','D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260925/BareArmsFamilyV6'))
SOURCES=Path(globals().get('NATIVE_SOURCE_ROOT',ROOT/'Sources'))
VERSION=globals().get('FAMILY_VERSION','V6')
OUT=ROOT/'Editable';OUT.mkdir(parents=True,exist_ok=True)
reflection=Matrix.Diagonal((1,-1,1))
for row in json.loads((ROOT/'manifest.json').read_text()):
    name=row['profile'];data=json.loads(Path(row['authored']).read_text())
    native=json.loads((SOURCES/f'{name}.json').read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm=bpy.data.armatures.new(name+'_NativeReference')
    rig=bpy.data.objects.new(name+'_NativeReference',arm);bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    bone_names={b['index']:n for n,b in native['bones'].items()}
    for n,b in native['bones'].items():
        bone=arm.edit_bones.new(n);axes=Matrix(b['axes']).transposed()
        for col in range(3):axes.col[col]=axes.col[col].normalized()
        rotation=reflection@axes@reflection
        matrix=rotation.to_4x4();matrix.translation=reflection@Vector(b['position'])*.01
        bone.matrix=matrix;bone.length=.025
    for n,b in native['bones'].items():
        parent=bone_names.get(b['parent'])
        if parent:arm.edit_bones[n].parent=arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh=bpy.data.meshes.new(name+'_BareArmsV6')
    mesh.from_pydata([(p[0]*.01,-p[1]*.01,p[2]*.01) for p in data['positions']],[],data['triangles']);mesh.update()
    obj=bpy.data.objects.new(name+'_BareArmsV6',mesh);bpy.context.collection.objects.link(obj)
    obj.parent=rig;mod=obj.modifiers.new('NativeBinding','ARMATURE');mod.object=rig
    for n in sorted({n for w in data['weights'] for n in w}):obj.vertex_groups.new(name=n)
    for vi,w in enumerate(data['weights']):
        for n,v in w.items():obj.vertex_groups[n].add([vi],v,'REPLACE')
    for label in ('UpperArm','Forearm','Hand'):
        material=bpy.data.materials.new('Skin_'+label);material.diffuse_color=(.372,.232,.182,1)
        material.use_nodes=True;bsdf=material.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value=(.372,.232,.182,1);bsdf.inputs['Roughness'].default_value=.49
        mesh.materials.append(material)
    layer=mesh.uv_layers.new(name='Anatomy');ns=[]
    for p,uv,normals,mat in zip(mesh.polygons,data['uv'],data['normals'],data['triangle_materials']):
        p.material_index=mat;p.use_smooth=True
        for loop,(u,v),n in zip(p.loop_indices,uv,normals):layer.data[loop].uv=(u,1-v);ns.append((n[0],-n[1],n[2]))
    mesh.normals_split_custom_set(ns)
    for channel in range(3):
        layer=mesh.uv_layers.new(name=('CanonicalXY','CanonicalZNormalX','CanonicalNormalYZ')[channel])
        for p in mesh.polygons:
            for corner,loop in enumerate(p.loop_indices):
                vi=mesh.loops[loop].vertex_index;c=data['canonical_positions'][vi];n=data['canonical_normals'][p.index][corner]
                layer.data[loop].uv=(c[:2],(c[2],n[0]),n[1:])[channel]
    obj['UE_source']=data['source'];obj['Contract']=data['contract']
    obj['Material']='Authoring preview only. UE shared V5 physical skin remains authoritative.'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'{name}_BareArms{VERSION}.blend'))
    print('BARE_FAMILY_BLEND_SAVED',name,flush=True)
