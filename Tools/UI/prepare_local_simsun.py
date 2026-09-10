"""Local-only SimSun face 0 outline synthesis. Never package the resulting Windows font.

Godot TextServer uses strength = embolden * pixel_size / 16 (pixel_size is 26.6).
Thus embolden 0.5 is 1/32 em. Preserve advances; do not emulate bold with shadows.
Source: https://github.com/godotengine/godot/blob/master/modules/text_server_adv/text_server_adv.cpp
Dependencies: fonttools, freetype-py (installed in Saved/UIUpgrade/Dependencies).
"""
import array
import ctypes
import hashlib
import json
from pathlib import Path
import sys

project = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project / 'Saved/UIUpgrade/Dependencies'))
import freetype
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
from fontTools.ttLib.tables.ttProgram import Program

source = Path('C:/Windows/Fonts/simsun.ttc')
target = project / 'Saved/UIFonts/SimSun-ColdSteel-0p5.ttf'
target.parent.mkdir(parents=True, exist_ok=True)
font = TTFont(source, fontNumber=0)
face = freetype.Face(str(source), index=0)
strength = round(font['head'].unitsPerEm / 32)
count = 0
for index, name in enumerate(font.getGlyphOrder()):
    face.load_glyph(index, freetype.FT_LOAD_NO_SCALE | freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_NO_BITMAP)
    outline = face.glyph.outline
    if outline.n_points < 3:
        continue
    error = freetype.FT_Outline_Embolden(ctypes.byref(outline._FT_Outline), strength)
    if error:
        raise RuntimeError((name, error))
    if any(tag & 2 for tag in outline.tags):
        raise RuntimeError('Unexpected cubic outline: ' + name)
    glyph = Glyph()
    glyph.numberOfContours = outline.n_contours
    glyph.coordinates = GlyphCoordinates(outline.points)
    glyph.endPtsOfContours = outline.contours
    glyph.flags = array.array('B', [tag & 1 for tag in outline.tags])
    glyph.program = Program()
    glyph.program.fromBytecode([])
    font['glyf'][name] = glyph
    count += 1
for table in ('DSIG', 'hdmx', 'LTSH', 'VDMX', 'EBLC', 'EBDT', 'EBSC'):
    if table in font:
        del font[table]
font.save(target)
verified = TTFont(target)
assert len(verified.getBestCmap()) == len(font.getBestCmap())
metadata = {'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'face': 0, 'embolden': .5, 'strength_em': 1 / 32, 'glyphs': count,
            'output_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'use': 'Local preview only; Windows font rights are unchanged; do not redistribute.'}
target.with_suffix('.json').write_text(json.dumps(metadata, indent=2), encoding='utf8')
print(json.dumps(metadata))
