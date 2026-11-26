"""Refine the first authored idle after side-view inspection."""
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
src=(P/'Tools/ChapelNun/author_idle_hands_front.py').read_text(encoding='utf-8')
src=src.replace("OUT = NUN / 'IdleHandsFrontR1'", "OUT = NUN / 'IdleHandsFrontR2'")
src=src.replace("rig = read(OUT / 'native_rig.json')", "rig = read(NUN / 'IdleHandsFrontR1/native_rig.json')")
src=src.replace("zip(DIGITS, (1., 2., 3., 4.))", "zip(DIGITS, (9., 12., 15., 18.))")
src=src.replace("'r': np.array([-6.2, 27.0, 99.2])", "'r': np.array([-2.6, 27.0, 96.8])")
src=src.replace("'l': unit([-.47, .02, -.88]), 'r': unit([.64, -.015, -.77])", "'l': unit([-.47, .02, -.88]), 'r': unit([.48, -.015, -.87])")
src=src.replace("# Left hand is the lower support", """# Flatten the upper thumb's deep default opposition before fitting the palms.
# Its native tip otherwise becomes the only contact and holds both palms apart.
for joint in (1, 2):
    name = f'thumb_{joint:02d}_r'
    child = f'thumb_{joint+1:02d}_r'
    w = fk(base)
    direction = unit(w[ix[child], :3, 3]-w[ix[name], :3, 3])
    normal = palm_normal['r']
    desired = unit(direction-normal*np.dot(direction, normal)*.90)
    orient(base, name, between(direction, desired) @ w[ix[name], :3, :3])

# Left hand is the lower support""")
exec(compile(src,str(P/'Tools/ChapelNun/author_idle_hands_front.py'),'exec'))
