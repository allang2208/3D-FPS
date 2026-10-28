"""B4 audition: TannerSound's energy strike with a layered pressure burst."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import soundfile as sf

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
SR = 48000
helper = BASE/'BowSemanticV2/author_bow_impact.py'
spec = importlib.util.spec_from_file_location('mountain_echo_audio_dsp', helper)
dsp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dsp)
RNG = np.random.default_rng(2026102804)


def pair(mono):
    return np.repeat(mono[:, None], 2, axis=1)


def main():
    # Retain the original first energy event and its internal tail, at original
    # pitch/speed. Previous revisions shortened it to .30 s and lowered its pitch.
    source = BASE/'Sources/LaserMagicImpacts.mp3'
    primary = dsp.read(source, 0, .72)
    primary = dsp.filt(primary, 48, 'highpass', 2)
    primary = dsp.bell(primary, 3300, -4.5, .85)
    primary = dsp.bell(primary, 5900, -8, .8)
    primary = dsp.filt(primary, 6500, 'lowpass', 3)
    low = dsp.filt(primary, 2300, 'lowpass', 2)
    age = np.arange(len(primary))/SR
    # Keep the initial edge; progressively soften the high-frequency ring.
    presence = .28+.42*np.exp(-age/.085)
    primary = low+(primary-low)*presence[:, None]
    primary = dsp.peak(dsp.edge(primary, .001, .055))

    t = np.arange(round(.68*SR))/SR
    centre = RNG.normal(0, 1, len(t))
    width_noise = RNG.normal(0, 1, (len(t), 2))
    noise = pair(centre)*.70+width_noise*.30

    # Pressure front and harmonics provide a solid impact on ordinary speakers.
    phase = 2*np.pi*(78*t+70*.038*(1-np.exp(-t/.038)))
    pressure = np.sin(phase)+.32*np.sin(2*phase)+.13*np.sin(3*phase)
    pressure *= (1-np.exp(-t/.002))*np.exp(-t/.105)
    pressure = dsp.peak(pair(pressure))
    body = dsp.filt(noise, [90, 1150], 'bandpass', 2)
    body *= ((1-np.exp(-t/.0018))*np.exp(-t/.090))[:, None]
    body = dsp.peak(np.tanh(body*1.6))

    # Broad, non-tonal energy expansion: dense just after impact, rapidly thinning.
    wave = dsp.filt(noise, [220, 3100], 'bandpass', 2)
    wave_env = (1-np.exp(-t/.014))*np.exp(-t/.180)
    wave *= wave_env[:, None]
    wave = dsp.peak(wave)
    grains = dsp.filt(width_noise, [1000, 4200], 'bandpass', 2)
    grain_env = (1-np.exp(-t/.006))*np.exp(-t/.145)
    grains *= grain_env[:, None]
    grains = dsp.peak(grains)

    # A low, short resonant residue connects the pressure wave to the golden VFX.
    resonance = (np.sin(2*np.pi*210*t)*np.exp(-t/.19)
                 +.44*np.sin(2*np.pi*347*t)*np.exp(-t/.15)
                 +.22*np.sin(2*np.pi*563*t)*np.exp(-t/.10))
    resonance *= 1-np.exp(-t/.012)
    resonance = dsp.peak(pair(resonance))
    air = dsp.read(dsp.ARROWS/'swish_2.wav', .04, .18, 1.14)
    air = dsp.peak(dsp.edge(dsp.filt(air, [450, 2600], 'bandpass', 2), .006, .025))

    audio = np.zeros((round(1.02*SR), 2))
    dsp.mix_at(audio, air, 0, .095)
    dsp.mix_at(audio, primary, .025, 1.0)
    dsp.mix_at(audio, pressure, .027, .48)
    dsp.mix_at(audio, body, .026, .40)
    dsp.mix_at(audio, wave, .046, .27)
    dsp.mix_at(audio, grains, .042, .075)
    dsp.mix_at(audio, resonance, .062, .075)
    # Diffuse, quiet reflections only; do not copy a loud delayed impact.
    reflections = dsp.edge(dsp.filt(wave, [320, 1600], 'bandpass', 2), .018, .10)
    dsp.mix_at(audio, reflections, .13, .035)
    dsp.mix_at(audio, reflections[:, ::-1], .21, .018)
    audio = dsp.edge(dsp.filt(audio, 42, 'highpass', 2), .002, .08)
    # Gentle body saturation and the same peak target as B2/B3; impact comes
    # from the envelope/layers rather than a higher audition peak.
    audio = np.tanh(audio*1.05)
    audio *= 10**(-3.5/20)/max(1e-8, float(np.abs(audio).max()))
    single = OUT/'B4_GoldenArrow_EnergyImpact.wav'
    audition = OUT/'B4_GoldenArrow_EnergyImpact_2x.wav'
    sf.write(single, audio, SR, subtype='PCM_24')
    sf.write(audition, np.concatenate([audio, np.zeros((round(.8*SR), 2)), audio]), SR, subtype='PCM_16')

    sources = [
        {'title': 'Laser/Magic Spell Impacts', 'author': 'TannerSound',
         'file': str(source), 'page': 'https://freesound.org/people/TannerSound/sounds/842627/',
         'license': 'CC-BY-4.0', 'license_url': 'https://creativecommons.org/licenses/by/4.0/',
         'cut_seconds': [0, .72], 'speed_pitch_ratio': 1.0},
        {'title': 'Battle Sound Effects / swish_2.wav', 'author': 'artisticdude',
         'file': str(dsp.ARROWS/'swish_2.wav'), 'page': 'https://opengameart.org/content/battle-sound-effects',
         'license': 'CC0-1.0', 'license_url': 'https://creativecommons.org/publicdomain/zero/1.0/',
         'cut_seconds': [.04, .18], 'speed_pitch_ratio': 1.14}]
    for item in sources:
        item['sha256'] = hashlib.sha256(Path(item['file']).read_bytes()).hexdigest()
    receipt = {'date': '2026-10-28', 'revision': 'B4 Energy Fusion',
        'user_direction': 'Use TannerSound Laser/Magic Spell Impacts combined with energy impact',
        'single_file': str(single), 'audition_file': str(audition), 'single_seconds': 1.02,
        'audition_repeats': 2, 'gap_seconds': .8, 'sample_rate': SR, 'channels': 2,
        'target_sample_peak_dbfs': -3.5, 'source_pitch_preserved': True,
        'sources': sources, 'original_layers': ['pressure impulse', 'dense impact body',
            'non-tonal energy expansion', 'diffuse grains', 'short low resonance'],
        'processing': 'Keep original event/tail; restrained high-frequency EQ and age-shaped presence; layered energy pressure burst; short diffuse reflections; gentle saturation and peak matching.',
        'helper_script': str(helper), 'helper_sha256': hashlib.sha256(helper.read_bytes()).hexdigest(),
        'runtime_modified': False, 'imported_to_ue': False, 'user_listening_approved': False}
    (OUT/'manifest.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    (OUT/'CREDITS.txt').write_text('\n'.join([
        'B4 Golden Arrow Energy Impact. Modified audition, 2026-10-28.',
        'Based on "Laser/Magic Spell Impacts" by TannerSound, CC BY 4.0.',
        'https://freesound.org/people/TannerSound/sounds/842627/',
        'https://creativecommons.org/licenses/by/4.0/',
        'Changes: first .72 s excerpt, EQ/high-frequency envelope, original synthesized energy/pressure layers, saturation and gain adjustment. Original pitch and speed retained.',
        'Short air layer: swish_2.wav, artisticdude / Battle Sound Effects, CC0.',
        'https://opengameart.org/content/battle-sound-effects',
        'https://creativecommons.org/publicdomain/zero/1.0/',
        'No UE or runtime audio changed.']), encoding='utf-8')
    print(json.dumps({'single': str(single), 'audition': str(audition), 'seconds': 1.02, 'runtime_modified': False}))


if __name__ == '__main__':
    main()
