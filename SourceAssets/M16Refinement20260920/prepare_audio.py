"""Decode the user-designated original one-shot without pitch, trimming or EQ."""
from pathlib import Path
import soundfile as sf,shutil,json,hashlib
O=Path(__file__).parent/'Audio';O.mkdir(exist_ok=True)
source=Path('D:/FPS3D/资产/音效/M16-fire.mp3');shutil.copy2(source,O/source.name)
samples,rate=sf.read(source,dtype='float32',always_2d=True);sf.write(O/'S_M16_OriginalFire.wav',samples,rate,subtype='PCM_16')
(O/'source.json').write_text(json.dumps({'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'sample_rate':rate,'channels':samples.shape[1],'duration':len(samples)/rate,'processing':'MP3 to PCM16 WAV only; original pitch, complete attack and tail','provenance':'Original Godot firing sound designated by the user on 2026-09-20. Local reuse; source authorship/license not supplied.'},indent=2),encoding='utf-8')
