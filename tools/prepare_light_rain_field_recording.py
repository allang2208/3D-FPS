"""Prepare the licensed Freesound leaf/ground rain field recording for Godot."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
import wave

import av
import numpy as np
from av.audio.resampler import AudioResampler


URL = "https://cdn.freesound.org/previews/497/497044_8021791-hq.mp3"
SOURCE_SHA256 = "46257de2128608e2233c3ef10e823732bd94dfde3cd70bf85716909050c9b653"
RATE = 22050
START_SECONDS = 25
SOURCE_SECONDS = 26
CROSSFADE_SECONDS = 2
TARGET_RMS = 0.065
OUTPUT = Path(__file__).resolve().parents[1] / "assets/sfx/weather/rain_leaves_ground_ccby_v4.wav"


def decode_source(data: bytes) -> np.ndarray:
    container = av.open(BytesIO(data), format="mp3")
    resampler = AudioResampler(format="s16p", layout="stereo", rate=RATE)
    chunks = []
    for frame in container.decode(audio=0):
        converted = resampler.resample(frame)
        if converted is None:
            continue
        if not isinstance(converted, list):
            converted = [converted]
        chunks.extend(item.to_ndarray().T.astype(np.float64) / 32768.0 for item in converted)
    return np.concatenate(chunks)


def main() -> None:
    source = urlopen(URL, timeout=60).read()
    assert sha256(source).hexdigest() == SOURCE_SHA256, "public source changed; review before rebuilding"
    decoded = decode_source(source)
    start = START_SECONDS * RATE
    source_frames = SOURCE_SECONDS * RATE
    clip = decoded[start:start + source_frames].copy()
    assert len(clip) == source_frames

    fade_frames = CROSSFADE_SECONDS * RATE
    middle = clip[fade_frames:-fade_frames]
    weight = np.linspace(0.0, 1.0, fade_frames, endpoint=False)[:, None]
    seam = clip[-fade_frames:] * (1.0 - weight) + clip[:fade_frames] * weight
    loop = np.concatenate([middle, seam])
    loop -= np.mean(loop, axis=0, keepdims=True)
    loop *= TARGET_RMS / np.sqrt(np.mean(loop ** 2))
    loop *= min(1.0, 0.92 / np.max(np.abs(loop)))

    pcm = np.round(loop * 32767).astype("<i2")
    with wave.open(str(OUTPUT), "wb") as stream:
        stream.setparams((2, 2, RATE, 0, "NONE", "not compressed"))
        stream.writeframes(pcm.tobytes())
    seam_step = np.max(np.abs(loop[0] - loop[-1]))
    typical_step = np.sqrt(np.mean(np.diff(loop, axis=0) ** 2))
    assert seam_step < typical_step * 6
    print(
        OUTPUT.name,
        "seconds=", len(loop) / RATE,
        "peak=", round(float(np.max(np.abs(loop))), 4),
        "rms=", round(float(np.sqrt(np.mean(loop ** 2))), 4),
        "seam_step/rms_step=", round(float(seam_step / typical_step), 3),
    )


if __name__ == "__main__":
    main()
