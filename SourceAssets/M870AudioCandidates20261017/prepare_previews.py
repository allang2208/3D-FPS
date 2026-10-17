"""Collect vendor-provided public listening previews for the user's selection.

These are evaluation previews, not purchased production WAV files. Nothing is
imported into Unreal. Preserve the preview content, pitch and level unchanged.
"""
from pathlib import Path
import hashlib
import html
import json
import re
import subprocess
import urllib.request
import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
DEST = HERE/'Preview'
DEST.mkdir(exist_ok=True)
CANDIDATES = [
    dict(id='A', name='M870_Dry', title='Remington 870 Single Shot Dry 05',
         creator='SoundMorph, Charles Maynes', library='Intervention',
         url='https://www.prosoundeffects.com/sound-effects/PSE_SMPH-INTR/T63GP/Remington-870-Single-Shot-Dry-05'),
    dict(id='B', name='M870_Exterior', title='Remington 870 Single Shot Exterior Open 02',
         creator='SoundMorph, Charles Maynes', library='Intervention',
         url='https://www.prosoundeffects.com/sound-effects/PSE_SMPH-INTR/Syi45/Remington-870-Single-Shot-Exterior-Open-02'),
    dict(id='C', name='M870_Close', title='Gunshot Shotgun - Remington 870, single shot, near perspective, exterior, bird shot',
         creator='Blastwave FX', library='Blastdrive 3.0',
         url='https://www.prosoundeffects.com/sound-effects/PSE_BW-BD3/8CjDE/Gunshot-Shotgun'),
]


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read()


records = []
for candidate in CANDIDATES:
    page = get(candidate['url']).decode('utf-8')
    # Use only the public compressed stream exposed by the vendor's player;
    # do not construct full-quality asset URLs or use a purchase endpoint.
    matches = re.findall(r'https://prosoundeffects\.blob\.core\.windows\.net/library/ogg/[^\s<>"\\]+\.ogg[^\s<>"\\]*', page)
    streams = sorted(set(html.unescape(url) for url in matches))
    if len(streams) != 1:
        raise RuntimeError('Expected one public preview on '+candidate['url'])
    data = get(streams[0])
    if not data.startswith(b'OggS'):
        raise RuntimeError('Preview response is not Ogg audio')
    base = candidate['id']+'_'+candidate['name']+'_Preview'
    original = DEST/(base+'.ogg')
    playable = DEST/(base+'.mp3')
    original.write_bytes(data)
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v','error','-y',
        '-i',str(original),'-vn','-c:a','libmp3lame','-b:a','320k',str(playable)],check=True)
    records.append(dict(**candidate,
        public_preview_path=streams[0].split('?',1)[0],
        original_preview=str(original),mp3_preview=str(playable),
        source_sha256=hashlib.sha256(data).hexdigest(),
        mp3_sha256=hashlib.sha256(playable.read_bytes()).hexdigest(),
        rights='Vendor public listening preview only. Production license not acquired; not a free or CC0 asset.',
        processing='OGG preview converted to MP3 for the requested listening files. No EQ, gain, trim, pitch or speed processing.',
        installed_in_game=False))

(HERE/'provenance.json').write_text(json.dumps(dict(date='2026-10-17',
    purpose='User-requested M870 firing sound candidates for listening and selection.',
    candidates=records),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([dict(id=r['id'],file=r['mp3_preview']) for r in records],indent=2))
