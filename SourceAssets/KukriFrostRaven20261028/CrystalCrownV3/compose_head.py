"""Compose the unified sapphire eagle into the retained glass HUD without raster edits."""
import json
from pathlib import Path

from PIL import Image

P = Path(__file__).resolve().parent
PRODUCTION = P.parent / 'ProductionV1'


def crown_layout():
    image = Image.open(P / 'Art/FrostRavenCrystal.png').convert('RGBA')
    alpha = image.getchannel('A')
    shoulder_y, root_y = 1050, 1125
    shoulder = [x for x in range(image.width) if alpha.getpixel((x, shoulder_y)) > 192]
    root = [x for x in range(image.width) if alpha.getpixel((x, root_y)) > 192]
    if len(shoulder) < 2 or len(root) < 2:
        raise RuntimeError('The crystal shoulder/root source anchors are missing')
    scale = 182.04 / (shoulder[-1] - shoulder[0])
    root_center = (root[0] + root[-1]) * .5
    origin_y = 480.0 - shoulder_y * scale
    root_width = (root[-1] - root[0]) * scale
    return {
        'image': 'Art/FrostRavenCrystal.png', 'image_size': list(image.size),
        'shoulder_sample_y': shoulder_y, 'shoulder_span_x': [shoulder[0], shoulder[-1]],
        'root_sample_y': root_y, 'root_span_x': [root[0], root[-1]],
        'origin_px': [256.0 - root_center * scale, origin_y],
        'extent_px': [image.width * scale, image.height * scale],
        'uniform_scale': scale, 'join_y': 480.0,
        'root_width_before_px': root_width, 'root_width_target_px': 182.04,
        'root_width_scale': 182.04 / root_width,
        'root_width_blend_y': [origin_y + 1000.0 * scale, origin_y + root_y * scale],
        'root_fade_y': [520.0, 540.0],
        'method': 'Original head placement and RGBA retained; only the lower throat smoothly widens to the column width',
    }


def apply_crown_layout(code, layout=None):
    layout = layout or crown_layout()
    x, y = layout['origin_px']
    width, height = layout['extent_px']
    start = code.index('// Frost Raven:')
    end = code.index('col = saturate(col);', start)
    root_start, root_end = layout['root_width_blend_y']
    projection = (
        '// Fit only the lower crystal throat; the portrait above it keeps its original projection.\n'
        f'float rootWidthScale=lerp(1.0,{layout["root_width_scale"]:.8f},Fn.SS({root_start:.8f},{root_end:.8f},P.y));\n'
        'float2 crownP=float2(HudCenter+(P.x-HudCenter)/rootWidthScale,P.y);\n'
        f'float2 headUV=(crownP-float2({x:.8f},{y:.8f}))/float2({width:.8f},{height:.8f});\n'
    )
    block = (P / 'CrystalComposite.hlsl').read_text('utf-8').replace('// CROWN_PROJECTION', projection.rstrip())
    code = code[:start] + block.rstrip() + '\n' + code[end:]
    return code.replace('max(max(headOpacity,joinOpacity),helixParticleCoverage)', 'max(headOpacity,helixParticleCoverage)')


if __name__ == '__main__':
    layout = crown_layout()
    target = PRODUCTION / 'FrostRavenEnergyHud.hlsl'
    code = apply_crown_layout(target.read_text('utf-8'), layout)
    target.write_text(code, encoding='utf-8')
    (P / 'FrostRavenCrystalHud.hlsl').write_text(code, encoding='utf-8')
    (P / 'crown-layout.json').write_text(json.dumps(layout, indent=2), encoding='utf-8')
    print(json.dumps(layout, indent=2))
