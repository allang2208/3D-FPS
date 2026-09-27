"""Acquire the CC0 weapon-texture archive, then extract only bow source WAVs.

The GitHub repository is an index, not the full sound library. OGA mirrors the
original Still North Media recordings. Ranged transfers keep this large solid
archive resumable on the slow mirror. No audio playback or gameplay is run.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import subprocess
import requests

HERE = Path(__file__).resolve().parent
URL = 'https://opengameart.org/sites/default/files/medieval_sfx_textures_1_of_2.7z'
TOTAL = 89924031
CHUNK = 4 * 1024 * 1024
DOWNLOADS = HERE / 'Downloads'
PARTS = DOWNLOADS / 'Parts'
PARTS.mkdir(parents=True, exist_ok=True)


def fetch(index):
    begin = index * CHUNK
    end = min(TOTAL, begin + CHUNK) - 1
    path = PARTS / f'{index:03d}.part'
    if path.exists() and path.stat().st_size == end - begin + 1:
        return path
    for attempt in range(3):
        try:
            result = requests.get(URL, headers={'Range': f'bytes={begin}-{end}'}, timeout=(30, 60))
            result.raise_for_status()
            if result.status_code != 206 or len(result.content) != end - begin + 1:
                raise RuntimeError('Mirror did not supply the requested byte range')
            path.write_bytes(result.content)
            print(f'Acquired range {index + 1}/{(TOTAL + CHUNK - 1) // CHUNK}', flush=True)
            return path
        except requests.RequestException:
            if attempt == 2:
                raise


with ThreadPoolExecutor(max_workers=6) as pool:
    paths = list(pool.map(fetch, range((TOTAL + CHUNK - 1) // CHUNK)))
archive = DOWNLOADS / 'medieval_sfx_textures_1_of_2.7z'
with archive.open('wb') as out:
    for path in paths:
        out.write(path.read_bytes())
sources = HERE / 'Original'
sources.mkdir(exist_ok=True)
subprocess.run([r'C:\Program Files\7-Zip\7z.exe', 'x', '-y', str(archive),
                f'-o{sources}', 'English Longbow*.wav', 'Arrow Fletching.wav'], check=True)

license_url = 'https://raw.githubusercontent.com/PanderMusubi/sound-effects-library-weapons/master/LICENSE'
license_response = requests.get(license_url, timeout=40)
license_response.raise_for_status()
(HERE / 'LICENSE-CC0.txt').write_text(license_response.text, encoding='utf-8')

manifest = {
    'author': 'Ben Jaszczak and Brian Nelson / Still North Media',
    'license': 'CC0-1.0',
    'github_index': 'https://github.com/PanderMusubi/sound-effects-library-weapons',
    'mirror_page': 'https://opengameart.org/content/medieval-sound-effects-weapon-textures',
    'original_permission_page': 'https://web.archive.org/web/20220331020630/https://www.stillnorthmedia.com/libraries',
    'archive_url': URL,
    'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
    'files': [dict(file=p.name, bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
              for p in sorted(sources.glob('*.wav'))],
}
(HERE / 'sources.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print('BOW_AUDIO_ACQUIRED ' + str(len(manifest['files'])) + ' source recordings', flush=True)
