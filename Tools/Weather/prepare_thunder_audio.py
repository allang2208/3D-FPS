"""Prepare local, licensed Thunder Sounds exports for the weather mixer.

Input: thunder-source-{0,1,2}.wav exported from the original three no-rain waves.
Requires numpy, soundfile and ffmpeg (PATH or imageio_ffmpeg). Never redistributes
the originals: the WAVs and resulting uassets remain local licensed content.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf


def prepare(source, destination):
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for index, variant in enumerate(('I', 'II', 'III')):
        original = source / f'thunder-source-{index}.wav'
        samples, rate = sf.read(original, always_2d=True)
        # Require a sustained 200 ms onset so a small isolated pre-rumble does
        # not retain seconds of near-silence. Keep 80 ms of natural attack.
        width = int(rate * .05)
        windows = samples[:len(samples)//width*width].reshape(-1, width, samples.shape[1])
        rms = np.sqrt(np.mean(windows ** 2, axis=(1, 2)))
        audible = np.flatnonzero(np.convolve((rms >= 10 ** (-38 / 20)).astype(int),
                                            np.ones(4), 'valid') == 4)
        if not len(audible):
            raise ValueError(f'No thunder onset in {original}')
        start = max(0., float(audible[0]) * .05 - .08)
        length = len(samples) / rate - start
        base = (f'atrim=start={start:.6f},asetpts=PTS-STARTPTS,'
                f'afade=t=in:d=0.025,afade=t=out:st={max(0., length-.2):.6f}:d=0.2')
        target = 'loudnorm=I=-20:TP=-3:LRA=11'
        measured = subprocess.run([ffmpeg, '-hide_banner', '-nostats', '-i', str(original),
            '-af', base + ',' + target + ':print_format=json', '-f', 'null', '-'],
            capture_output=True, text=True, check=True).stderr
        values = json.loads(measured[measured.rfind('{'):measured.rfind('}')+1])
        norm = (target + f":measured_I={values['input_i']}:measured_TP={values['input_tp']}"
                f":measured_LRA={values['input_lra']}:measured_thresh={values['input_thresh']}"
                f":offset={values['target_offset']}:linear=true:print_format=json")
        output = destination / f'S_Thunder_{variant}.wav'
        rendered = subprocess.run([ffmpeg, '-hide_banner', '-nostats', '-y', '-i', str(original),
            '-af', base + ',' + norm, '-ar', '48000', '-c:a', 'pcm_s16le', str(output)],
            capture_output=True, text=True, check=True).stderr
        final = json.loads(rendered[rendered.rfind('{'):rendered.rfind('}')+1])
        records.append(dict(variant=variant,
            source_asset=f'/Game/Thunder_Sounds/WAV/WAV_Thunder_Lightning_{variant}_Without_rain_wind_background_noise',
            source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
            output=output.name, output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
            trimmed_lead_seconds=round(start, 4), duration_seconds=round(length, 4),
            processing=final))
    (destination/'provenance.json').write_text(json.dumps(dict(
        source='Existing project Thunder Sounds pack; derivative for local game use only.',
        redistribution='No additional redistribution rights granted; do not publish source audio or uassets.',
        target_lufs=-20, true_peak_db=-3, assets=records), indent=2), encoding='utf-8')
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[2]/'SourceAssets/Weather/Thunder')
    args = parser.parse_args()
    prepare(args.source, args.output)
