"""Inspect authored decoration colors only where exported blade UVs use them."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
uvs = json.loads((P / 'blade-uvs.json').read_text(encoding='utf-8'))
textures = {
    'M_Zhanmadao_Surface_V1': 'Zhanmadao20261018/Textures/Zhanmadao_BaseColor.jpg',
    'M_TangDaoSurface': 'TangDaoMeshy20261002/SurfaceV2/Textures/TangDao_BaseColor.png',
    'M_TangDaoYanlingSteel': 'TangDaoMeshy20261002/YanlingBlade20261002/Textures/TangDao_Yanling_BaseColor.png',
    'M_TangDaoTengyunSteel': 'TangDaoMeshy20261002/TengyunBlade20261002/Textures/TangDao_Tengyun_BaseColor.png',
    'M_Chixiao_BladeSurface': 'Zhanmadao20261018/ChixiaoBladeV1/Textures/Chixiao_BaseColor.png',
    'M_Zhufeng_BladeSurface': 'Zhanmadao20261018/ZhufengBladeV1/Textures/Zhufeng_BaseColor.png',
}
result = {}
for choice, row in uvs.items():
    result[choice] = []
    for slot, triangles in row['slots'].items():
        path = textures.get(slot)
        if not path:
            result[choice].append({'slot': slot, 'separate_decoration_slot': True})
            continue
        image = Image.open(ROOT / 'SourceAssets' / path).convert('RGB')
        w, h = image.size
        coverage = Image.new('L', (w, h))
        draw = ImageDraw.Draw(coverage)
        for triangle in triangles:
            draw.polygon([(round(u * (w - 1)), round((1 - v) * (h - 1))) for u, v in triangle], fill=255)
        used = np.asarray(coverage) > 0
        encoded = np.asarray(image, dtype=np.float32) / 255
        linear = np.where(encoded <= .04045, encoded / 12.92, ((encoded + .055) / 1.055) ** 2.4)
        chroma = linear[:, :, 0] - np.maximum(linear[:, :, 1], linear[:, :, 2])
        warm = used & (chroma > .020)
        entry = {'slot': slot, 'texture': path, 'used_texels': int(used.sum()),
                 'warm_decoration_texels': int(warm.sum()),
                 'warm_fraction': float(warm.sum() / used.sum()),
                 'max_warm_chroma': float(chroma[used].max())}
        if choice == 'zhufeng':
            orm = np.asarray(Image.open(ROOT / 'SourceAssets/Zhanmadao20261018/ZhufengBladeV1/Textures/Zhufeng_ORM.png').convert('RGB'))
            inlay = used & (orm[:, :, 2] / 255 < .93)
            entry['cyan_inlay_texels'] = int(inlay.sum())
        result[choice].append(entry)
(P / 'color-coverage.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
for key, rows in result.items():
    print(key, [{k: v for k, v in row.items() if k not in ('texture', 'used_texels')} for row in rows])
