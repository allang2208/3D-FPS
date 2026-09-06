"""Package actual Blender-rendered frames and inspect exported GLB structure."""
from pathlib import Path
import json, struct
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parent
for name,ms in [('idle',200),('attack',None),('walk',None),('death',None)]:
    paths=sorted((ROOT/('frames-'+name)).glob('*.png'))
    frames=[Image.open(p).convert('RGB') for p in paths]
    durations=[ms]*len(frames) if ms else [40,40,40,40,40,50]*(len(frames)//6)
    if name=='death':durations[-1]+=1000
    frames[0].save(ROOT/(name+'-preview.gif'),save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=2)
    with Image.open(ROOT/(name+'-preview.gif')) as gif:
        total=0
        for i in range(gif.n_frames):gif.seek(i);total+=gif.info['duration']
        print(name,'frames',gif.n_frames,'duration_ms',total)
        # GIF coalesces identical anticipation poses and adds their hold durations.
        assert gif.n_frames<=len(paths)
        assert total=={'idle':4800,'attack':1000,'walk':2250,'death':3000}[name]
blob=(ROOT/'zombie-preview.glb').read_bytes()
length=struct.unpack_from('<I',blob,12)[0]
doc=json.loads(blob[20:20+length])
clips=[]
for a in doc.get('animations',[]):
    times=[doc['accessors'][s['input']] for s in a['samplers']]
    clips.append({'name':a.get('name'),'start':min(x['min'][0] for x in times),'end':max(x['max'][0] for x in times),'channels':len(a['channels'])})
primitives=[p for m in doc.get('meshes',[]) for p in m['primitives']]
report={'clips':clips,'skins':len(doc.get('skins',[])),'joint_counts':[len(s['joints']) for s in doc.get('skins',[])],'all_primitives_skinned':all('JOINTS_0' in p['attributes'] and 'WEIGHTS_0' in p['attributes'] for p in primitives),'embedded_images':all('bufferView' in i for i in doc.get('images',[])),'external_buffers':[b.get('uri') for b in doc.get('buffers',[]) if b.get('uri')]}
assert {a['name'] for a in clips}>={'Idle','Attack','Walk','Death'},clips
for a in clips:
    assert abs(a['start'])<1e-6,a
    assert abs(a['end']-{'Idle':4.8,'Attack':1.0,'Walk':2.25,'Death':2}[a['name']])<1e-5,a
assert report['all_primitives_skinned'] and report['skins']==1
(ROOT/'export-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
