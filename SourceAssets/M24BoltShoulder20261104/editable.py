"""Editable full-pose examples for the factory and advanced bolt branches."""
from pathlib import Path
import ast
import copy
exec(compile((Path(__file__).parent/'shoulder.py').read_text().split("if __name__=='__main__'")[0],'M24 source FK','exec'))
patch=json.load(gzip.open(O/'shoulder_tracks.json.gz','rt'))
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(S/'M24QuickMeleeRightHandR3_20261104/M24_QuickMelee_RightHandR3_Editable.blend'),link=False) as (library,data):
    data.objects=['M24_V9_Rig','M24_CurrentV9_Arms']
s=bpy.context.scene
for ob in data.objects:s.collection.objects.link(ob)
r,skin=data.objects
r.animation_data_clear();skin.data.shape_keys.animation_data_clear()
author=ast.parse((S/'M24Hold20261027/author_hold.py').read_text())
bake_node=next(n for n in author.body if isinstance(n,ast.FunctionDef) and n.name=='bake')
# The shared baker normally adds its own twist pass; use our complete poses.
bake_node.body=bake_node.body[1:]
code=ast.unparse(bake_node).replace('s.render.fps = 30','s.render.fps = 60').replace('(len(rows) - 1) / 30','(len(rows) - 1) / 60')
exec(compile(code,'native editable bake','exec'))
report={'clips':{}}
for family in ('base','skeleton_mag10_stable'):
    for role,tracks in patch[family].items():
        clip=copy.deepcopy(entry(family,role));replacement={tr['bone']:tr for tr in tracks}
        clip['tracks']=[replacement.get(tr['bone'],tr) for tr in clip['tracks']]
        rows=[compose(clip,i/60)[0] for i in range(round(clip['duration']*60)+1)]
        bake(f'BoltShoulder_{family}_{role}',rows)
        action=r.animation_data.action
        shapes=bpy.data.actions.new(action.name+'_Skin');shapes.use_fake_user=True
        keys=skin.data.shape_keys;keys.animation_data_create();keys.animation_data.action=shapes
        action['corrective_action']=shapes.name
        for i,row in enumerate(rows):
            values,_=corrective_weights(row,morph.files)
            for name in morph.files:
                key=keys.key_blocks[name];key.value=values.get(name,0.);key.keyframe_insert('value',frame=i)
first=bpy.data.actions['A_M24_BoltShoulder_base_fire']
r.animation_data.action=first;r.animation_data.action_slot=first.slots[0]
skin.data.shape_keys.animation_data.action=bpy.data.actions[first['corrective_action']]
s.render.fps=60;s.frame_end=110;s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_BoltShoulder_Editable.blend'),compress=True)
