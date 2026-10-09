from pathlib import Path
O=Path(__file__).parent
review=O.parents[1]/'Saved/Super90R7Review20261008/render_saved.py'
ns={'__file__':str(review)}
exec(compile(review.read_text().split('items=[]')[0],str(review),'exec'),ns)
bpy=ns['bpy'];scene=ns['scene'];s=ns['s'];apply=ns['apply'];frames=O/'Diagnostics/Frames';frames.mkdir(exist_ok=True)
for empty,frame in ((False,f) for f in (0,42,87,104,114,120,124,128,129,134,146)):
    apply(s['pose'](frame,7,empty)[0])
    for ob in ns['groups']['props']:ob.hide_render=not(74<=frame<127)
    scene.render.filepath=str(frames/f'normal_{frame:03d}.png');bpy.ops.render.render(write_still=True)
for frame in (128,139,146,158,165,174,182):
    apply(s['pose'](frame,7,True)[0])
    for ob in ns['groups']['props']:ob.hide_render=not(74<=frame<127)
    scene.render.filepath=str(frames/f'empty_{frame:03d}.png');bpy.ops.render.render(write_still=True)
print('CANDIDATE_RENDERED',flush=True)
