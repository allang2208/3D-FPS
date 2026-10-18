"""Read the authored skin contacts without changing the motion or assets."""
from pathlib import Path
path = Path(__file__).with_name('author_thumb.py')
exec(compile(path.read_text().split('report, authored = {}, {}')[0], str(path), 'exec'))
current = json.loads((ROOT/'Content/ColdSteelData/potion_use_motion.json').read_text())
rows = {}
for item, folder, file in [('roasted_large_lamb','LargeLamb20261014','large-lamb-geometry.json'),
                           ('roasted_lamb_ribs','LambRibs20261014','lamb-geometry.json')]:
    geometry = json.loads((ROOT/'SourceAssets'/folder/file).read_text())
    for side in (('l','r') if current[item].get('two_handed') else ('l',)):
        grasp = Grasp(current[item], geometry, side)
        thumb = current[item].get('right_thumb') if side=='r' else current[item]['digits']['thumb']
        row = {'thumb': grasp.metrics(thumb), 'finger_tip_nearest_food_cm': {}}
        for digit in ('index','middle','ring','pinky'):
            ids = np.array([i for i,w in enumerate(skin['weights']) if w.get(digit+'_03_'+side,0)>.7])
            points = grasp.deform(thumb, ids, grasp.forearms[0])
            nearest = min(grasp.food.find_nearest(Vector(p))[3] for p in points)
            row['finger_tip_nearest_food_cm'][digit] = round(nearest,4)
        rows[item+'_'+side] = row
        print(item,side,json.dumps(row),flush=True)
(OUT/'saved-contacts.json').write_text(json.dumps(rows,indent=2)+'\n')
