"""Place both default-grip revisions on one editable V9 timeline."""
from pathlib import Path
exec(compile((Path(__file__).parent/'common_pose.py').read_text(), 'V9 motion', 'exec'))
with gzip.open(WORK/'skeleton_base.json.gz','rt') as file:
    revised=json.load(file)
bpy.ops.wm.open_mainfile(filepath=str(PREVIOUS/'M24_TwoStock_QuickMelee_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig']
keys=bpy.data.objects['M24_CurrentV9_Arms'].data.shape_keys
r.animation_data_clear();keys.animation_data_clear()
for action in list(bpy.data.actions):
    if action.name.startswith('A_M24_QuickMeleeGrip_'):bpy.data.actions.remove(action)
node=next(n for n in ast.parse((S/'M24Hold20261027/author_hold.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='bake')
node.body=[n for n in node.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and getattr(n.value.func,'id','')=='twists')]
report={'clips':{}}
exec(compile(ast.unparse(node),'existing native action baker','exec'))
stock=[compose(revised['stock'],i/240)[0] for i in range(217)]
carbon=[compose(revised['carbon'],i/240)[0] for i in range(217)]
rows=stock+[stock[-1]]*23+carbon
bake('StockHandContinuity',rows)
s.render.fps=240
available=[k.name for k in keys.key_blocks if k.name!='Basis']
for i,row in enumerate(rows):
    weights,_=corrective_weights(row,available)
    for n in available:
        key=keys.key_blocks[n]
        key.value=weights.get(n,0.);key.keyframe_insert('value',frame=i)
for label,visible in (('stock',True),('carbon',False)):
    ob=bpy.data.objects['M24_Advanced_'+label]
    ob.hide_set(False)
    for fr,show in ((0,visible),(240,not visible)):
        ob.hide_viewport=not show;ob.hide_render=not show
        ob.keyframe_insert('hide_viewport',frame=fr);ob.keyframe_insert('hide_render',frame=fr)
s.timeline_markers.clear()
s.timeline_markers.new('Skeleton',frame=0);s.timeline_markers.new('Carbon',frame=240)
s.frame_start=0;s.frame_end=len(rows)-1;s.frame_set(0)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(WORK/'M24_HandContinuity.blend'),compress=True)
