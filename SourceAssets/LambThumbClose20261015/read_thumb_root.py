from pathlib import Path
path = Path(__file__).with_name('author_thumb.py')
exec(compile(path.read_text().split('report, authored = {}, {}')[0], str(path), 'exec'))
item='roasted_large_lamb'
geometry=json.loads((ROOT/'SourceAssets/LargeLamb20261014/large-lamb-geometry.json').read_text())
for side in ('l','r'):
    for offset in (0., .4, .8, 1.2):
        motion=copy.deepcopy(data[item])
        field='right_grip_in_palm' if side=='r' else 'grip_in_palm'
        motion[field][2]+=offset
        grasp=Grasp(motion,geometry,side)
        thumb={'spread':[-70,-65,-60], 'flex':[5,22,35]}
        print(side,offset,json.dumps(grasp.metrics(thumb)),flush=True)
