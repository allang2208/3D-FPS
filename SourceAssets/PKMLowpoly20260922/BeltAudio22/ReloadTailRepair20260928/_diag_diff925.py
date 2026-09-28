import numpy as np, soundfile as sf
from pathlib import Path
P = Path(r"D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\BeltAudio22")
for name in ["CoverOpen", "CoverClose"]:
    orig = sf.read(P/f"S_PKM_{name}.wav")[0]
    new  = sf.read(P/"rebuild"/f"S_PKM_{name}_rebuilt_delivered.wav")[0]
    print(f"=== {name}: orig {len(orig)}  new {len(new)}  equal_len={len(orig)==len(new)}")
    n = min(len(orig), len(new))
    d = np.abs(orig[:n]-new[:n])
    # first sample where they differ beyond int16 quantisation
    idx = np.flatnonzero(d > 1.5/32768)
    first = int(idx[0]) if len(idx) else None
    if first is not None:
        print(f"   first differing sample: {first}  ({first/48000*1000:.1f} ms)")
        print(f"   identical prefix len: {first} samples = {first/48000*1000:.1f} ms")
        print(f"   differing region: {first}..{n} = {(n-first)/48000*1000:.1f} ms")
    print(f"   peak orig {np.max(np.abs(orig)):.4f} @ {int(np.argmax(np.abs(orig)))}  new {np.max(np.abs(new)):.4f} @ {int(np.argmax(np.abs(new)))}")
    print(f"   RMS  orig {20*np.log10(np.sqrt(np.mean(orig**2))):.2f} dBFS  new {20*np.log10(np.sqrt(np.mean(new**2))):.2f} dBFS")
    print(f"   RMS of last 100 ms: orig {20*np.log10(np.sqrt(np.mean(orig[-4800:]**2))):.2f}  new {20*np.log10(np.sqrt(np.mean(new[-4800:]**2))):.2f}")
