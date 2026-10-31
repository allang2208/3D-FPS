"""Production spacing policy for optional street furniture and parked vehicles."""
from pathlib import Path
import json,math,random,collections
R=Path(__file__).resolve().parent
p=R/'publish_manifest.json';m=json.loads(p.read_text())
if m.get('spacing_applied'):raise SystemExit('Street spacing already applied')
grids=collections.defaultdict(lambda:collections.defaultdict(list));counts=collections.Counter()
def free(category,p,r):
    cell=(math.floor(p[0]/r),math.floor(p[1]/r));grid=grids[category]
    for x in range(cell[0]-1,cell[0]+2):
        for y in range(cell[1]-1,cell[1]+2):
            if any((p[0]-q[0])**2+(p[1]-q[1])**2<r*r for q in grid[(x,y)]):return False
    grid[cell].append(p);return True
rng=random.Random(281028)
for row in m['rows']:
    stride=row.get('custom_stride',0)
    if stride and 'custom_data' in row:
        for i,tr in enumerate(row['transforms']):tr['custom']=row['custom_data'][i*stride:(i+1)*stride]
    mesh=row['mesh'];category=None;r=0;occupancy=1.0
    if '/Vehicle/' in mesh:category='parked_vehicles';r=850;occupancy=.45
    elif 'StreetLamp' in mesh:category='street_lamps';r=2300
    elif 'Parking_Meter' in mesh:category='parking_meters';r=1300;occupancy=.6
    elif 'Road_Sign' in mesh:category='road_signs';r=2000
    elif 'Mailbox' in mesh:category='mailboxes';r=4000
    elif 'Hydrant' in mesh:category='fire_hydrants';r=4000
    if not category:continue
    output=[]
    for tr in row['transforms']:
        if rng.random()<=occupancy and free(category,tr['p'],r):output.append(tr)
    counts[category]+=len(output);row['transforms']=output
m['rows']=[r for r in m['rows'] if r['transforms']]
m['spacing_applied']=True;m['street_detail_counts']=dict(counts)
m['counts']['instances']=sum(len(r['transforms']) for r in m['rows']);m['counts']['components']=len(m['rows'])
p.write_text(json.dumps(m,separators=(',',':')),encoding='utf8')
(R/'street_spacing.json').write_text(json.dumps(dict(stage='production_spacing_composed',counts=dict(counts),policy='Native grammar placements retained with deterministic spacing and partial parking occupancy',tests_run=False),indent=2),encoding='utf8')
print('STREET_SPACING_COMPOSED',dict(counts),m['counts'],flush=True)
