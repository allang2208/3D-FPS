from pathlib import Path
import struct,json
R=Path(__file__).resolve().parent
with (R/'delivery/HandBrain_SingleFace.glb').open('rb') as f:
 magic,version,length=struct.unpack('<III',f.read(12));assert magic==0x46546c67 and version==2
 size,kind=struct.unpack('<II',f.read(8));assert kind==0x4e4f534a
 doc=json.loads(f.read(size))
clips={}
for a in doc['animations']:
 times=[doc['accessors'][s['input']] for s in a['samplers']]
 clips[a['name']]=max(t['max'][0] for t in times)-min(t['min'][0] for t in times)
assert set(clips)=={'Idle','Move','Attack_Slam','Attack_Howl'},clips
for name,d in [('Idle',2),('Move',1),('Attack_Slam',2),('Attack_Howl',3)]:assert abs(clips[name]-d)<.001
assert len(doc['skins'])==1 and len(doc['skins'][0]['joints'])==37
(R/'delivery/glb_validation.json').write_text(json.dumps({'clips':clips,'skins':1,'joints':37,'meshes':len(doc['meshes'])},indent=2))
print('SINGLE_FACE_GLB_VALIDATED',clips)
