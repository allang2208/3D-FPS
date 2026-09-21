import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector

O=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O/'A762_Rigged_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
report=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
for key in report['animations']:
    name='A_A762_'+key
    with bpy.data.libraries.load(str(O/(name+'.blend')),link=False) as (src,dst):
        dst.actions=[name]
    dst.actions[0].use_fake_user=True
for label,hinge in report['hinges_ue_root'].items():
    ob=bpy.data.objects['SM_A762_'+label]
    # Exported static sights are hinge-local. Reassemble them in the editable rig.
    xf=r.data.bones['WPN_root'].matrix_local@Matrix.Translation(Vector((hinge[0],-hinge[1],hinge[2])))
    normals=[(xf.to_3x3().inverted().transposed()@n.vector).normalized() for n in ob.data.corner_normals]
    ob.data.transform(xf);ob.data.normals_split_custom_set(normals)
    ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
    ob.vertex_groups.new(name='WPN_root').add(list(range(len(ob.data.vertices))),1,'REPLACE')
    mod=ob.modifiers.new('EditableSightMount','ARMATURE');mod.object=r
    ob.hide_set(False);ob.hide_render=False
r.animation_data.action=bpy.data.actions['A_A762_idle']
r.animation_data.action_slot=r.animation_data.action.slots[0]
s.render.fps=round(report['animations']['idle']['fps']);s.render.fps_base=1
s.frame_start=0;s.frame_end=report['animations']['idle']['frames'];s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'A762_Rigged_Editable.blend'))
print('A762 editable rig assembled with all owned actions.',flush=True)
