"""Cut the user-selected current recording into six reusable, uneven segments."""
from pathlib import Path
import hashlib, json, shutil
import numpy as np
import soundfile as sf

P = Path(__file__).resolve().parent
source = Path('D:/FPS3D/资产/音效/疾雷重击蓄力.mp3')
(P/'Original').mkdir(exist_ok=True)
(P/'Waves').mkdir(exist_ok=True)
shutil.copy2(source, P/'Original/JiLei_Charge_User.mp3')
audio, rate = sf.read(source, dtype='float64', always_2d=True)
# Keep the active recording, removing only its very short empty lead/tail.
start = round(.04 * rate)
end = min(len(audio), round(10.07 * rate))
rng = np.random.default_rng(202611012221)
weights = rng.uniform(.80, 1.20, 6)
boundaries = np.rint(start + np.r_[0, np.cumsum(weights / weights.sum())] * (end-start)).astype(int)
gain = 10 ** (-3.5 / 20) / np.max(np.abs(audio[start:end]))
manifest = dict(revision='JiLeiRecordedCurrentV2', source=str(source),
    original_copy='Original/JiLei_Charge_User.mp3',
    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    decoded_seconds=len(audio)/rate, sample_rate=rate, channels=audio.shape[1],
    encoding='PCM_16', gain_db=float(20*np.log10(gain)), edge_fade_ms=2,
    provenance='User-provided recording; not claimed as original synthesis or public-domain material',
    selection='Six uneven contiguous source cuts; runtime random choice avoids previous two segments',
    playback='MetaSound Wave Player, On Nearly Finished through delayed trigger variable; native pitch',
    gameplay_tested=False, clips=[])
for i, (a,b) in enumerate(zip(boundaries[:-1],boundaries[1:]), 1):
    clip = audio[a:b].copy() * gain
    fade = round(rate * .002)
    clip[:fade] *= np.sin(np.linspace(0,np.pi/2,fade))[:,None] ** 2
    clip[-fade:] *= np.cos(np.linspace(0,np.pi/2,fade))[:,None] ** 2
    filename = f'S_JiLei_Current_{i:02d}.wav'
    sf.write(P/'Waves'/filename, clip, rate, subtype='PCM_16')
    manifest['clips'].append(dict(file='Waves/'+filename, name=Path(filename).stem,
        start_sample=int(a), end_sample=int(b), start_seconds=a/rate,
        end_seconds=b/rate, seconds=(b-a)/rate,
        sha256=hashlib.sha256((P/'Waves'/filename).read_bytes()).hexdigest()))
(P/'audio_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('JI_LEI_USER_RECORDING_CUT', [(r['name'],round(r['seconds'],3)) for r in manifest['clips']])
