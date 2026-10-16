"""Adapt the existing local asset-production entry points to this new variant."""
from pathlib import Path
O=Path(__file__).parent
S=O.parent/'Super90Choke20261015'
replacements=[('Super90Choke20261015','Super90Birdcage20261015'),
              ('ShotgunChoke_Box01','ShotgunBirdcage01'),
              ('ShotgunChoke_Icon','ShotgunBirdcage_Icon'),
              ('ShotgunChoke_LODGroup','ShotgunBirdcage_LODGroup'),
              ('/CommonShotgun/Choke20261015','/CommonShotgun/Birdcage20261015'),
              ('T_Choke_FlatNormal','T_Birdcage_FlatNormal'),
              ('T_ShotgunChoke_Icon','T_ShotgunBirdcage_Icon'),
              ('muzzle_shotgun_choke','muzzle_shotgun_birdcage_flash_hider'),
              ('ShotgunChokeSource','ShotgunBirdcageSource'),
              ('24.8','7.4'),('25.8','8.4')]
for name in ('author_icon.py','package_runtime.py','install_assets.py','install.ps1','build_game.ps1','build_editor.ps1'):
    text=(S/name).read_text(encoding='utf-8-sig')
    for old,new in replacements:text=text.replace(old,new)
    text=text.replace('CHOKE','BIRDCAGE').replace('shared choke','shared birdcage')
    (O/name).write_text(text,encoding='utf-8-sig' if name.endswith('.ps1') else 'utf-8',newline='\n')
# Keep this new variant on its own path, reusing the accepted neutral normal.
install=O/'install_assets.py'
text=install.read_text(encoding='utf-8').replace(
    '/Game/Weapons/A762/ADSSurface20261015/Textures/T_A762_FlatNormal',
    '/Game/Weapons/CommonShotgun/Choke20261015/Textures/T_Choke_FlatNormal')
install.write_text(text,encoding='utf-8',newline='\n')
print('BIRDCAGE_PIPELINE_PREPARED')
