from pathlib import Path
from PIL import Image
import numpy as np,wave,json,hashlib
root=Path('D:/FPS3D/FPSGAME/SourceAssets/PoisonMaggot20260911');out=root/'delivery'
im=np.array(Image.open(out/'T_Maggot_Normal.png'));im[:,:,1]=255-im[:,:,1];Image.fromarray(im).save(out/'T_Maggot_Normal_DirectX.png')
rng=np.random.default_rng(2414);rate=44100;t=np.arange(int(rate*.17))/rate;env=np.sin(np.pi*t/.17)**2*np.exp(-t*12);noise=rng.normal(0,1,len(t));wet=np.convolve(noise,np.ones(7)/7,'same')*.65+np.sin(2*np.pi*(170*t-180*t*t))*.2;v=np.int16(np.clip(wet*env*.6,-1,1)*32767)
with wave.open(str(out/'S_Maggot_Spit.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(v.tobytes())
manifest=json.loads(Path('D:/FPS3D/FPSGAME/Saved/Hunyuan3D/Candidates/poison_maggot_v01/manifest.json').read_text())
record={k:manifest[k] for k in ('provider','model','job_id','pbr','outputs')};record['reference']='reference/realistic_identity_v01.png';record['reference_tool']='built-in image_gen';record['source_identity']='reference/identity.png';record['usage']='User-provided project reference; generated and locally edited model; local use; original source redistribution not audited';record['audio']='Locally synthesized wet filtered-noise spit, reproducible seed 2414, no external sample';record['reference_prompt_summary']='One photorealistic same ivory 9-segment larva, black mouth, six paired short prolegs, neutral pose, uniform light, gray background, no poison mesh';(root/'provenance.json').write_text(json.dumps(record,indent=2))
