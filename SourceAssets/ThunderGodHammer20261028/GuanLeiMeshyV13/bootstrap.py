"""Reuse the saved JiLei integration recipe in an isolated GuanLei revision."""
from pathlib import Path
P=Path(__file__).resolve().parent
source=P.parent/'JiLeiMeshyV15'
replacements=[
 ('Meshy_AI_Nordic_Aegis_Shield_1101101638_texture.glb','Meshy_AI_Valkyrie_Forge_Chestp_1101102421_texture.glb'),
 ('JiLeiInlaidLightningV14','GuanLeiClosedCrownV12'),
 ('JiLei_V14','GuanLei_V12'),('JiLei14','GuanLei12'),
 ('JiLeiMeshyV15','GuanLeiMeshyV13'),('JiLei_V15','GuanLei_V13'),
 ('JiLei15','GuanLei13'),('ji_lei_seat_V15','guan_lei_seat_V13'),
 ('ji_lei','guan_lei'),('jilei-v15','guanlei-v13'),
 ('JILEI_V15','GUANLEI_V13'),('JILEI','GUANLEI'),('JiLei','GuanLei'),
 ('MeshyV15','MeshyV13'),('疾雷','贯雷')]
for relative in ['intake.py','read_geometry.py','author.py','render_icon.py','Integration/import_assets.py','Integration/install.ps1','Integration/publish.py']:
    target=P/relative
    if target.exists():continue
    text=(source/relative).read_text(encoding='utf-8-sig')
    for a,b in replacements:text=text.replace(a,b)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding='utf-8')
print('GUANLEI_RECIPE_PREPARED')
