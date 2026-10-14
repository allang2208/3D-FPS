"""Acquire the CC0 public preview and author a short, onset-aligned Dealer cue; no playback."""
from array import array
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import subprocess
import sys
import urllib.request
import wave

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
SOURCE_PAGE = 'https://freesound.org/people/scorpion67890/sounds/169317/'
SOURCE_AUDIO = 'https://cdn.freesound.org/previews/169/169317_2389125-hq.mp3'
LICENSE_PAGE = 'https://creativecommons.org/publicdomain/zero/1.0/'
FFMPEG = PROJECT / 'SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
RATE = 48000


def acquire(url, destination):
    if not destination.exists():
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': SOURCE_PAGE})
        with urllib.request.urlopen(request, timeout=45) as response:
            destination.write_bytes(response.read())
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def main():
    originals = ROOT / 'Original'
    masters = ROOT / 'Masters'
    originals.mkdir(parents=True, exist_ok=True)
    masters.mkdir(parents=True, exist_ok=True)
    page_hash = acquire(SOURCE_PAGE, originals / 'freesound-169317.html')
    license_hash = acquire(LICENSE_PAGE, originals / 'CC0-1.0.html')
    source = originals / '169317_2389125-hq.mp3'
    source_hash = acquire(SOURCE_AUDIO, source)
    pcm = subprocess.run([
        str(FFMPEG), '-v', 'error', '-i', str(source), '-vn', '-ac', '1', '-ar', str(RATE),
        '-af', 'highpass=f=40,lowpass=f=9000', '-f', 'f32le', 'pipe:1',
    ], check=True, capture_output=True).stdout
    samples = array('f')
    samples.frombytes(pcm)
    if sys.byteorder != 'little':
        samples.byteswap()
    peak = max(abs(value) for value in samples)
    # Align the laugh's onset with the burst; retain 3 ms before the first audible sample.
    threshold = max(.002, peak * .01)
    onset = next(index for index, value in enumerate(samples) if abs(value) >= threshold)
    start = max(0, onset - int(RATE * .003))
    samples = samples[start:]
    gain = math.pow(10, -3 / 20) / peak
    fade_in, fade_out = int(RATE * .003), int(RATE * .060)
    encoded = array('h')
    for index, value in enumerate(samples):
        edge = min(1.0, index / fade_in, (len(samples) - 1 - index) / fade_out)
        encoded.append(round(value * gain * max(0.0, edge) * 32767))
    if sys.byteorder != 'little':
        encoded.byteswap()
    output = masters / 'S_Dealer_DemonLaugh.wav'
    with wave.open(str(output), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(RATE)
        stream.writeframes(encoded.tobytes())
    recipe = {
        'complete': True, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'source_title': 'Demonic Laugh', 'author': 'scorpion67890', 'sound_id': 169317,
        'source_page': SOURCE_PAGE, 'source_audio': SOURCE_AUDIO,
        'license': 'CC0-1.0', 'license_url': LICENSE_PAGE,
        'acquisition': 'Public HQ MP3 preview; the original WAV download requires a Freesound login.',
        'source_description': 'Author recorded their own laugh and lowered its pitch.',
        'source_page_sha256': page_hash, 'license_page_sha256': license_hash,
        'source_sha256': source_hash, 'source_file': str(source.relative_to(ROOT)),
        'output': str(output.relative_to(ROOT)), 'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'output_rate_hz': RATE, 'output_channels': 1, 'output_bits': 16,
        'duration_seconds': len(samples) / RATE, 'trim_lead_seconds': start / RATE,
        'processing': {'highpass_hz': 40, 'lowpass_hz': 9000, 'peak_target_dbfs': -3,
                       'gain': gain, 'fade_in_seconds': .003, 'fade_out_seconds': .060},
        'runtime_tiers': {'4': {'volume': .65, 'pitch': 1.0}, '5': {'volume': .75, 'pitch': .96},
                          '7': {'volume': .85, 'pitch': .90}},
        'listened': False, 'gameplay_tested': False,
    }
    (ROOT / 'provenance.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'DEALER_LAUGH_AUTHORED {len(samples) / RATE:.3f}s CC0 preview-derived played=false')


if __name__ == '__main__':
    main()
