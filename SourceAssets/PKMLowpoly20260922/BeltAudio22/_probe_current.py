import numpy as np, soundfile as sf
from pathlib import Path
HERE = Path(r"D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\BeltAudio22")
CONTENT = Path(r"D:\FPS3D\FPSGAME\Content\Weapons\PKMLowpoly20260922\ReloadAudio22")
for name in ["CoverOpen", "CoverClose"]:
    fixed = sf.read(HERE / "rebuild" / f"S_PKM_{name}_rebuilt_delivered.wav")[0]
    orig  = sf.read(HERE / f"S_PKM_{name}.wav")[0]
    raw   = (CONTENT / f"S_PKM_{name}.uasset").read_bytes()
    print(f"=== {name}: fixed {len(fixed)} samples, orig {len(orig)} samples, uasset {len(raw)} B")
    for label, arr in (("FIXED", fixed), ("ORIGINAL", orig)):
        pcm = np.clip(np.round(arr * 32767.0), -32768, 32767).astype("<i2").tobytes()
        idx = raw.find(pcm)
        print(f"   verbatim PCM16 of {label:9s} found at offset: {idx}")
    # also try float32
    for label, arr in (("FIXED", fixed), ("ORIGINAL", orig)):
        pcm = arr.astype("<f4").tobytes()
        idx = raw.find(pcm)
        print(f"   verbatim F32   of {label:9s} found at offset: {idx}")
