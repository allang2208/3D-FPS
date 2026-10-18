from pathlib import Path
path=Path(__file__).with_name('author_thumb.py')
exec(compile(path.read_text().split('report, authored = {}, {}')[0],str(path),'exec'))
motion=json.loads((ROOT/'Content/ColdSteelData/potion_use_motion.json').read_text())['roasted_large_lamb']
geometry=json.loads((ROOT/'SourceAssets/LargeLamb20261014/large-lamb-geometry.json').read_text())
grasp=Grasp(motion,geometry,'r')
print('SHARED_THUMB',json.dumps(grasp.metrics(motion['digits']['thumb'])),flush=True)
