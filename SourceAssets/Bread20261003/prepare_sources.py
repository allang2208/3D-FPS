"""Extract the user's Bread archive and retain a reproducible production recipe."""
from pathlib import Path
import zipfile

CASE = Path(__file__).resolve().parent
SOURCE = CASE / 'Source'
ARCHIVE = Path('D:/FPS3D/资产/bread_ukjkbef_high.zip')
SOURCE.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(ARCHIVE) as archive:
    for entry in archive.infolist():
        if not (SOURCE / entry.filename).resolve().is_relative_to(SOURCE.resolve()):
            raise RuntimeError('Archive member leaves its source folder: ' + entry.filename)
    archive.extractall(SOURCE)

BASE = CASE.parent / 'Baguette20261003'
author = (BASE / 'author_baguette.py').read_text(encoding='utf-8-sig')
author = author.replace("Path('D:/FPS3D/VaultCache/FabLibrary/Baguette_Bread-e555b990/fbx/high/baguette_bread_ujqhebs_h_extracted')", "OUT / 'Source'")
author = author.replace('Baguette_Bread_ujqhebs', 'Bread_ukjkbef')
author = author.replace('baguette_bread.png', 'bread.png').replace('Baguette', 'Bread')
author = author.replace('LENGTH_CM = 30.0', 'LENGTH_CM = 12.0')
author = author.replace('scene.render.resolution_y = 960', 'scene.render.resolution_y = 320')
author = author.replace("camera.location = (.7, -.18, HALF_LENGTH_M)", "camera.location = (.30, -.70, HALF_LENGTH_M + .18)")
author = author.replace('width * 3 / .86', 'width / .90')
author = author.replace('1x3 canvas', '1x1 canvas').replace('[320, 960]', '[320, 320]')
author = author.replace('e555b990-d7ca-49db-bdde-653ce637854e', 'fa23606e-e514-47b8-9d62-2833886ae518')
author = author.replace("'source': str(SOURCE)", "'source_archive': 'D:/FPS3D/资产/bread_ukjkbef_high.zip', 'source': str(SOURCE)")
(CASE / 'author_bread.py').write_text(author, encoding='utf-8')

importer = (BASE / 'import_baguette.py').read_text(encoding='utf-8-sig')
importer = importer.replace('Baguette', 'Bread').replace('baguette_bread', 'bread').replace('baguette', 'bread')
importer = importer.replace('BAGUETTE_ASSETS_SAVED', 'BREAD_ASSETS_SAVED')
(CASE / 'import_bread.py').write_text(importer, encoding='utf-8')
driver = (BASE / 'build_and_save.ps1').read_text(encoding='utf-8-sig')
driver = driver.replace('Baguette', 'Bread').replace('baguette', 'bread')
(CASE / 'build_and_save.ps1').write_text(driver, encoding='utf-8-sig')
print('BREAD_PRODUCTION_SOURCES_SAVED')
