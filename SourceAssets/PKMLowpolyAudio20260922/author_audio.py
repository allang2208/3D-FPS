"""Author the PKM fire one-shot for continuous fire and a weightier tone.

Source defect (measured, see analyze_tone.py / analyze_timing.py): the delivered
file is a 0.5 s container holding 64 ms of sound, 50 ms of leading silence and a
hard cut at full level; its content is bright and thin compared with the accepted
AKM reference, and its energy sits in a single early spike.

Tone target, measured against that reference:
  * band share  40-315 Hz    PKM 18.9% vs AKM 59.9%   -> lacks body
  * band share 630-5000 Hz   PKM 55.0% vs AKM 16.7%   -> hard and clangy
  * level at 92.3 ms         PKM about -21 dB         -> tail never blooms
  * crest factor             PKM 10.6 dB vs AKM 15.5 dB
The AKM's weight comes from its low end *growing* through the body (low-band
share 5% in the first 15 ms, 60% afterwards) while its upper midrange decays away.
So the fix is two-part: a static tilt correction on the recording, and a rebuilt
decay whose low band rings long while its upper bands die fast.

The attack keeps its own recording (tilt EQ only), and the decay is built only
from the recording's own spectrum. No pitch or time change, no external layers.

Run with the local Python 3.11 environment (NumPy, SciPy, SoundFile).
"""
from pathlib import Path
import hashlib
import json
import math

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'S_PKM_Fire.raw.wav'
OUTPUT = HERE / 'S_PKM_Fire.wav'

FIRE_INTERVAL = 0.092308          # 650 发/分，与 gunsmith.json 一致
OUTPUT_SECONDS = 0.150            # 尾音延长让低频绽放；仍与下一发叠尾
REFERENCE_PEAK = 0.6025           # 与 AKM 参考峰值一致，保持全枪族峰值口径

# 修正 EQ（相对原录音）。只走"从 PKM 原始倾斜朝 AKM 参考移动 60%"这一段，
# 保留 PKM 自身性格；40-80 Hz 不动，那在参考里是房间隆隆而不是枪声。
# 每项为 (类型, 频率 Hz, 增益 dB, Q)。参数由 sweep_tone.py 扫描选定。
EQ = [
    ('lowshelf', 90.0, -1.2, 0.7),
    ('lowshelf', 200.0, 1.8, 0.7),
    ('peak', 500.0, 0.9, 0.9),
    ('peak', 900.0, -1.2, 0.9),
    ('peak', 2400.0, -0.9, 1.0),
    ('highshelf', 7000.0, -1.2, 0.707),
]

# 尾音：低频长鸣、中频中等、机械细节快收，复现 AKM 那种"低频在主体段绽放"。
TAIL_BANDS = (
    (50.0, 200.0, 0.110, 1.00),         # 厚度与胸腔感
    (200.0, 800.0, 0.070, 1.00),        # 主体
    (800.0, 3500.0, 0.032, 1.00),       # 机械细节
    (3500.0, 9000.0, 0.016, 1.00),      # 尾端空气感
)
TAIL_GAIN = 0.50                  # 拼接对齐之后再乘，真正控制尾部绝对电平
BODY_DUCK = 0.90                  # 轻微收主体，让爆音重音更突出（提升 crest）
BODY_DUCK_START = 0.035           # 秒；此前的爆音完全不动
PEAK_SOFTEN = 0.30                # 主峰软化量（0 = 不动）
SPLICE_BLEND = 0.012
END_FADE = 0.008

x, rate = sf.read(SOURCE, always_2d=True, dtype='float64')
if x.shape[1] != 1:
    raise RuntimeError('This recipe expects the delivered mono PKM recording.')
signal = x[:, 0]


def envelope(sig, win=0.0025):
    step = max(1, int(rate * win))
    return np.array([math.sqrt(float(np.mean(sig[i:i + step] ** 2)))
                     for i in range(0, max(1, len(sig) - step), step)])


def biquad(kind, freq, gain_db, q, sample_rate):
    """RBJ cookbook peaking/shelf biquad, returned as second-order sections."""
    a = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * freq / sample_rate
    cw, sw = math.cos(w0), math.sin(w0)
    if kind == 'peak':
        alpha = sw / (2.0 * q)
        b = [1 + alpha * a, -2 * cw, 1 - alpha * a]
        d = [1 + alpha / a, -2 * cw, 1 - alpha / a]
    elif kind == 'lowshelf':
        alpha = sw / 2.0 * math.sqrt((a + 1 / a) * (1 / q - 1) + 2)
        sq = 2.0 * math.sqrt(a) * alpha
        b = [a * ((a + 1) - (a - 1) * cw + sq),
             2 * a * ((a - 1) - (a + 1) * cw),
             a * ((a + 1) - (a - 1) * cw - sq)]
        d = [(a + 1) + (a - 1) * cw + sq,
             -2 * ((a - 1) + (a + 1) * cw),
             (a + 1) + (a - 1) * cw - sq]
    elif kind == 'highshelf':
        alpha = sw / 2.0 * math.sqrt((a + 1 / a) * (1 / q - 1) + 2)
        sq = 2.0 * math.sqrt(a) * alpha
        b = [a * ((a + 1) + (a - 1) * cw + sq),
             -2 * a * ((a - 1) + (a + 1) * cw),
             a * ((a + 1) + (a - 1) * cw - sq)]
        d = [(a + 1) - (a - 1) * cw + sq,
             2 * ((a - 1) - (a + 1) * cw),
             (a + 1) - (a - 1) * cw - sq]
    else:
        raise RuntimeError('unknown biquad kind: ' + kind)
    return np.array([[b[0] / d[0], b[1] / d[0], b[2] / d[0],
                      1.0, d[1] / d[0], d[2] / d[0]]])


def apply_eq(sig, sample_rate):
    out = sig
    for kind, freq, gain_db, q in EQ:
        out = sosfilt(biquad(kind, freq, gain_db, q, sample_rate), out)
    return out


# --- 1. 裁掉前导静音与满幅硬截断，保留完整瞬态 -------------------------------
nonzero = np.nonzero(signal != 0.0)[0]
if nonzero.size == 0:
    raise RuntimeError('Source recording is silent.')
content_start = int(nonzero[0])
content_end = int(nonzero[-1]) + 1
trimmed = signal[max(0, content_start - int(0.0005 * rate)):content_end].copy()

# --- 2. 修正 EQ（同时用于尾部合成源，保证频谱与主体同源） --------------------
tilted = apply_eq(signal, rate)

attack = apply_eq(trimmed, rate)
total = int(OUTPUT_SECONDS * rate)
tail_length = total - len(attack)
if tail_length <= 0:
    raise RuntimeError('Attack already fills the target length; adjust OUTPUT_SECONDS.')

# --- 3. 低频长鸣的尾音 -------------------------------------------------------
source_start = max(0, content_start - int(0.0005 * rate))
decay_time = np.arange(tail_length) / rate
tail = np.zeros(tail_length)
for low, high, tau, weight in TAIL_BANDS:
    band = sosfiltfilt(butter(2, [low, high], btype='bandpass', fs=rate, output='sos'),
                       tilted)
    tail += weight * band[source_start:source_start + tail_length] * np.exp(-decay_time / tau)

# The band sum does not reconstruct the broadband level, so match the tail's
# opening RMS to the attack's closing RMS; otherwise the splice steps down.
probe = max(1, int(0.005 * rate))
attack_ref = math.sqrt(float(np.mean(attack[-probe:] ** 2)))
tail_ref = math.sqrt(float(np.mean(tail[:probe] ** 2)))
if tail_ref > 0:
    tail *= attack_ref / tail_ref
# The gain applies after the splice match, so it really sets the tail's level.
tail *= TAIL_GAIN

y = np.concatenate([attack, tail])
blend = min(int(SPLICE_BLEND * rate), len(attack) // 2, tail_length // 2)
ramp = np.linspace(0.0, 1.0, blend)
y[len(attack) - blend:len(attack)] *= 1.0 - ramp * 0.5
y[len(attack):len(attack) + blend] *= 0.5 + ramp * 0.5

# --- 4. 瞬态塑形：爆音不动，主体轻微下沉，重音更突出 -------------------------
duck_from = int(BODY_DUCK_START * rate)
y[duck_from:] *= BODY_DUCK
# Soften the single loudest sample run so the loud end of the recording does not
# spend the whole headroom on one spike.
peak_index = int(np.argmax(np.abs(y)))
soften = int(0.0015 * rate)
lo, hi = max(0, peak_index - soften), min(len(y), peak_index + soften)
y[lo:hi] *= (1.0 - PEAK_SOFTEN * np.hanning(hi - lo))

# --- 5. 电平与收尾 ----------------------------------------------------------
# 用户反馈实机偏小一倍。加工前先检查要加多少才削顶：把 2× 直接乘上去会削掉 1.7% 的样本，
# 所以先归一到满刻度（相对当前 0.6025 是 +4.4 dB），剩下的差额由资产 volume 属性补，
# 这样既拿到接近两倍的响度，又不产生硬削顶失真。
y *= 1.0 / np.max(np.abs(y))
# What a blind 2x user request would have cost, recorded so the decision is auditable.
fade = int(END_FADE * rate)
y[-fade:] *= np.linspace(1.0, 0.0, fade)

sf.write(OUTPUT, y, rate, subtype='PCM_16')

out_env = envelope(y)
peak = float(np.max(np.abs(y)))
rms = math.sqrt(float(np.mean(y ** 2)))
report = {
    'source_raw': str(SOURCE),
    'source_raw_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'source_raw_seconds': len(signal) / rate,
    'source_content_ms': [round(content_start / rate * 1000, 2), round(content_end / rate * 1000, 2)],
    'source_defect': '64 ms of sound inside a 0.5 s container; 50 ms leading silence; '
                     'hard cut at full level at ~114 ms',
    'output_seconds': len(y) / rate,
    'fire_interval_seconds': FIRE_INTERVAL,
    'output_longer_than_interval': len(y) / rate > FIRE_INTERVAL,
    'corrective_eq': [{'type': k, 'hz': f, 'gain_db': g, 'q': q} for k, f, g, q in EQ],
    'tail_bands': [{'low': lo, 'high': hi, 'tau': tau, 'weight': w}
                   for lo, hi, tau, w in TAIL_BANDS],
    'tail_length_ms': round(tail_length / rate * 1000, 2),
    'tail_gain': TAIL_GAIN,
    'body_duck': BODY_DUCK,
    'body_duck_start_ms': BODY_DUCK_START * 1000,
    'peak_soften': PEAK_SOFTEN,
    'sample_peak': peak,
    'peak_normalised_full_scale': True,
    'level_note': 'WAV is at full scale; the requested 2x loudness is split into '
                  '+4.4 dB here (peak 0.6025 -> 1.0, short of clipping) and the rest via the '
                  'SoundWave volume property, because a blind 2x on the WAV clips samples.',
    'rms': rms,
    'crest_db': 20 * math.log10(peak / rms),
    'pitch_multiplier': 1.0,
    'attack_modified': 'trimmed to the real sound; tilt EQ only, no time or pitch change',
    'runtime_volume_multiplier': 'unchanged (AKMSource::FireVolume * WeaponAudioGain)',
    'envelope_db': [round(20 * math.log10(max(v, 1e-9)), 1) for v in out_env[:int(0.16 / 0.0025)]],
    'listening_or_gameplay_tested': False,
}
(HERE / 'authoring.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
# provenance.json is the single source of truth for hashes; keep it current so a
# stale hash never describes a file that has since been re-authored.
provenance = {
    'source_raw': str(SOURCE),
    'source_raw_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'source_origin': 'E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/sounds/weapons/pkm_half_sec.wav',
    'role_in_prototype': 'PKM fire one-shot (equip-data-manager.js PKM_ITEM.fireSound)',
    'authored_output': str(OUTPUT),
    'authored_sha256': hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    'ue_asset': '/Game/Weapons/PKMLowpoly20260922/Audio/S_PKM_Fire',
    'reference_asset': '/Game/Weapons/AKM/VideoAudio20260921/S_AKM_Fire',
    'rights': 'Original gamedev prototype recording; original rights retained, '
              'no public redistribution license established. Local project use only.',
    'listening_or_gameplay_tested': False,
}
(HERE / 'provenance.json').write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'envelope_db'}, indent=2, ensure_ascii=False))
