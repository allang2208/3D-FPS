"""Prepare a scoped, reproducible source revision; never overwrite the original blend."""
from pathlib import Path
import shutil
import hashlib
import json

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/CyberpunkApartmentPlayable20261021')
SOURCE = Path('D:/CyberpunkApartment')
BUILD = ROOT / 'build'
BUILD.mkdir(parents=True, exist_ok=True)
for path in (SOURCE / 'build').glob('*.py'):
    target = BUILD / path.name
    shutil.copy2(path, target)

def edit(name, old, new):
    path = BUILD / name
    data = path.read_text(encoding='utf-8-sig')
    if new in data:
        return
    if data.count(old) != 1:
        raise RuntimeError(f'{name}: expected one source anchor: {old[:90]}')
    path.write_text(data.replace(old, new), encoding='utf-8')

# Remove the duplicate east partition, retain both bedroom openings in one wall.
edit('s1_arch.py', '''    cy.wall_run(mb, "y", 0.0, 5.40, 11.34, 0.0, CL, T_INT, "plaster",
                openings=[(4.10, 5.00, 0.0, 2.08)])''',
     '    # East partition is emitted once below, with both bedroom doorways.')
edit('s1_arch.py', 'openings=[(7.58, 8.48, 0.0, 2.08)])',
     'openings=[(4.10, 5.00, 0.0, 2.08), (7.58, 8.48, 0.0, 2.08)])')
# The original north corridor wall sealed the foyer and both utility/bath approaches.
edit('s1_arch.py', 'openings=[(5.30, 7.90, 0.0, 2.42)])',
     'openings=[(1.10, 2.20, 0.0, 2.42), (3.48, 4.58, 0.0, 2.42), (5.30, 7.90, 0.0, 2.42), (9.40, 10.44, 0.0, 2.42)])')
edit('s1_arch.py', 'mull = [4.02, 5.82, 7.62, 9.42, 11.22]',
     'mull = [4.02, 5.82, 7.00, 8.10, 9.42, 11.22]  # clear balcony opening')
# No overlapping glass panes or immovable open slider in the new moving leaf's path.
edit('s1_arch.py', '(6.90, -0.055, 2.44), (6.90, -0.055, 0.16)',
     '(7.00, -0.055, 2.44), (7.00, -0.055, 0.16)')
edit('s1_arch.py', '(9.30, -0.055, 0.16), (9.30, -0.055, 2.44)',
     '(8.10, -0.055, 0.16), (8.10, -0.055, 2.44)')
p = BUILD / 's1_arch.py'
s = p.read_text(encoding='utf-8')
start = s.index('    mbg.quad((6.00,')
end = s.index('    # bedroom windows', start)
s = s[:start] + '    # Balcony moving glass is authored as an independent door asset.\n' + s[end:]
start = s.index('    # leaves\n')
end = s.index('    mb.build()', start)
s = s[:start] + '    # All leaves are runtime ColdSteelSlidingDoor components.\n' + s[end:]
# Remove the 16 cm solid spandrel only across the door opening (preserve surrounding facade).
s = s.replace('cy.wall_run(mb, "x", 0.0, 16.0, 0.0, 0.0, 0.16, T_EXT, "concrete_wall")',
              'cy.wall_run(mb, "x", 0.0, 16.0, 0.0, 0.0, 0.16, T_EXT, "concrete_wall", openings=[(7.00, 8.10, 0.0, 0.16)])')
p.write_text(s, encoding='utf-8')

edit('s2_living.py', '    # bookshelf on the south wall (right of the living opening)',
     '    mb.pop()  # close media-console frame before placing other furniture\n\n    # bookshelf on the south wall (right of the living opening)')
# Small bedroom is entered from foyer: move the shoe cabinet off its doorway.
edit('s5_bath_foyer.py', '(11.02, 8.55, 0)', '(11.02, 9.35, 0)')
edit('s5_bath_foyer.py', '(11.02, 8.55, 1.13)', '(11.02, 9.35, 1.13)')
edit('s5_bath_foyer.py', '(9.80, 6.50, 0)', '(10.70, 6.50, 0)')
# Keep the approach to foyer open (loose shoes were on its new opening).
edit('s5_bath_foyer.py', '(9.55, 7.05, 0)', '(9.00, 7.35, 0)')
edit('s5_bath_foyer.py', '(9.35, 7.05, 0)', '(9.00, 7.05, 0)')

p = BUILD / 's12_joinery.py'
s = p.read_text(encoding='utf-8')
s = s.replace('("y", 11.280, 0.160, 5.400, [], -1)', '("y", 11.280, 0.160, 5.400, [(4.10, 5.00)], -1)')
s = s.replace('("y", 11.280, 6.840, 10.880, [], -1)', '("y", 11.280, 6.840, 10.880, [(7.58, 8.48)], -1)')
s = s.replace('("x", 6.840, 8.760, 11.280, [], +1)', '("x", 6.840, 8.760, 11.280, [(9.40, 10.44)], +1)')
s = s.replace('("x", 6.720, 0.160, 11.280, [(5.30, 7.90)], -1)', '("x", 6.720, 0.160, 11.280, [(1.10, 2.20), (3.48, 4.58), (5.30, 7.90), (9.40, 10.44)], -1)')
s = s.replace('("x", 8.080, 0.160, 2.720, [], -1)', '("x", 8.080, 0.160, 2.720, [(1.14, 2.10)], -1)')
s = s.replace('("x", 8.080, 2.840, 4.680, [], -1)', '("x", 8.080, 2.840, 4.680, [(3.22, 4.18)], -1)')
start = s.index('    # ------------------------------------------------------- door sets')
end = s.index('    # ------------------------------------------------- window reveals', start)
s = s[:start] + '    # Moving hardware belongs to the independent runtime door meshes.\n\n' + s[end:]
p.write_text(s, encoding='utf-8')

p = BUILD / 's13_finish.py'
s = p.read_text(encoding='utf-8')
s = s.replace('("x", 8.080, +1, 0.120, 2.720, [])', '("x", 8.080, +1, 0.120, 2.720, [(1.14, 2.10)])')
s = s.replace('("x", 8.080, +1, 2.840, 4.680, [])', '("x", 8.080, +1, 2.840, 4.680, [(3.22, 4.18)])')
# Horizontal grout strips used to bridge every doorway at shin/waist height.
start = s.index('        for z in (Z0 + 0.30')
end = s.index('    # ------------------------------------------------- floor tile joints', start)
s = s[:start] + '''        for z in (Z0 + 0.30, Z0 + 0.60, Z0 + 0.90):
            for s0, s1 in segments(a0, a1, gaps):
                panel(mb, axis, fixed, side, s0, s1, z, z + 0.004, 0.014, "grout")

''' + s[end:]
s = s.replace('("y", 11.276, 0.20, 5.36, [])', '("y", 11.276, 0.20, 5.36, [(4.10, 5.00)])')
s = s.replace('("x", 6.712, 0.20, 11.26, [(5.32, 7.88)])', '("x", 6.712, 0.20, 11.26, [(1.10, 2.20), (3.48, 4.58), (5.30, 7.90), (9.40, 10.44)])')
p.write_text(s, encoding='utf-8')

# Wall props were authored directly inside bedroom/kitchen openings.
edit('s6_details.py', '(11.30, 5.02, 1.75, 0.55, 1.40, -math.pi / 2)', '(11.30, 3.55, 1.75, 0.55, 1.40, -math.pi / 2)')
edit('s6_details.py', '(6.85, 6.74, 1.90, 0.70, 0.50, 0)', '(8.40, 6.74, 1.90, 0.70, 0.50, 0)')
edit('s6_details.py', '(7.40, 6.68, 1.35)', '(8.15, 6.68, 1.35)')

# Clear the approach and the surface-mounted sliding pockets, not just the wall hole.
edit('s2_living.py', '(10.52, 3.05, 0)', '(10.52, 2.40, 0)')
edit('s4_bedrooms.py', '(1.05, 4.98, 0), math.pi', '(0.46, 4.65, 0), math.pi / 2')
edit('s4_bedrooms.py', '(13.55, 5.06, 0)', '(14.00, 5.06, 0)')
edit('s4_bedrooms.py', 'furn.wardrobe(mb, w=2.90, h=2.40', 'furn.wardrobe(mb, w=2.70, h=2.40')
edit('s4_bedrooms.py', '(11.55, 8.90, 0), -math.pi / 2', '(14.20, 10.64, 0), 0.0')
edit('s4_bedrooms.py', 'furn.shelves(mb, w=1.8, h=2.05', 'furn.shelves(mb, w=1.0, h=2.05')
edit('s3_kitchen.py', '[(6.10, 7.35, 0.05), (7.30, 7.35, -0.06)',
     '[(6.10, 7.80, 0.05), (7.30, 7.80, -0.06)')
edit('s5_bath_foyer.py', '(4.34, 8.62, 0)', '(4.34, 9.15, 0)')
p = BUILD / 's5_bath_foyer.py'
s = p.read_text(encoding='utf-8').replace('(3.14, 9.02,', '(3.14, 9.55,')
p.write_text(s, encoding='utf-8')
edit('s1_arch.py', '(7.60, -1.42, -0.09)', '(7.60, -1.42, -0.16)')
edit('s1_arch.py', 'mb.quad((x0, y0, F), (x0, y1, F), (x1, y1, F), (x1, y0, F), key)',
     'mb.quad((x0, y0, F), (x1, y0, F), (x1, y1, F), (x0, y1, F), key)')
edit('s4_bedrooms.py', '(11.60, 7.30, 0)', '(15.60, 10.40, 0)')
edit('s5_bath_foyer.py', '(10.62, 10.86, 1.45)', '(11.00, 10.86, 1.45)')
p = BUILD / 's4_bedrooms.py'
s = p.read_text(encoding='utf-8').replace('(0.70, 4.98, 0.86)', '(0.46, 4.65, 0.86)')
p.write_text(s, encoding='utf-8')
(ROOT / 'source_manifest.json').write_text(json.dumps({
    'original_blend': str(SOURCE / 'CyberpunkApartment.blend'),
    'original_sha256': hashlib.sha256((SOURCE / 'CyberpunkApartment.blend').read_bytes()).hexdigest(),
    'level_scale': 1.25, 'revision_build': str(BUILD),
    'map': '/Game/GameMaps/L_CyberpunkApartment'
}, indent=2), encoding='utf-8')
print(ROOT)
