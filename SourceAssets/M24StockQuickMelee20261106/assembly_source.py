"""Attach the real independent stock/chassis/grips to the editable native rig."""
import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).resolve().parent
def attach_current_assembly(rig):
    for name in ('M24_base',):
        ob=bpy.data.objects.get(name)
        if ob:ob.hide_set(True);ob.hide_render=True
    d=json.loads((O.parent/'M24AcceptedGrip20261103/Review/weapon_geometry.json').read_text())
    mesh=bpy.data.meshes.new('M24 retained native receiver barrel and trigger')
    mesh.from_pydata([(p[0]*.01,-p[1]*.01,p[2]*.01) for p in d['positions']],[],[list(reversed(f['vertices'])) for f in d['faces'] if f['material']==2]);mesh.update()
    ob=bpy.data.objects.new('M24_Advanced_RetainedNativeBody',mesh);bpy.context.collection.objects.link(ob)
    for index,weights in d['weights'].items():
        for name,weight in weights.items():
            vg=ob.vertex_groups.get(name) or ob.vertex_groups.new(name=name);vg.add([int(index)],weight,'REPLACE')
    mod=ob.modifiers.new('Native_M24_Armature','ARMATURE');mod.object=rig
    for kind,spec in json.loads((O/'assembly.json').read_text()).items():
        before=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=spec['fbx'],use_custom_normals=True)
        imported=list(set(bpy.data.objects)-before)
        for part in imported:
            if part.type!='MESH':continue
            matrix=part.matrix_world.copy();part.parent=None;part.data.transform(matrix);part.matrix_world=Matrix.Identity(4)
            part.name='M24_Advanced_'+kind;part['assembly_role']=kind
            vg=part.vertex_groups.new(name='WPN_root');vg.add(list(range(len(part.data.vertices))),1.,'REPLACE')
            mod=part.modifiers.new('Native_M24_Armature','ARMATURE');mod.object=rig
            if (kind.startswith('grip_') and kind!='grip_Default') or kind in ('carbon','stock_native','carbon_native'):part.hide_set(True);part.hide_render=True
        for part in imported:
            if part.type!='MESH':bpy.data.objects.remove(part,do_unlink=True)
if __name__=='__main__':
    file=O/'M24_QuickMelee_CurrentGrip_Editable.blend'
    bpy.ops.wm.open_mainfile(filepath=str(file),use_scripts=False)
    attach_current_assembly(bpy.data.objects['M24_V9_Rig'])
    bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(file))
    print('M24_CURRENT_ASSEMBLY_SOURCE_SAVED',flush=True)
