"""Produce the visibility revision from the actual saved material, not an old draft."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
state=json.loads((P/'state_before.json').read_text(encoding='utf-8'))
code=next(n['code'] for n in state['nodes'] if n['class']=='MaterialExpressionCustom' and 'RuneTexture' in n.get('code',''))
changes={
    '// Keep the existing spirit composition and blade-space placement.':'// Frost Spirit visibility: preserve composition, blade projection and soft timing.',
    'lightBands += outline * life * .10;':'lightBands += outline * (.03 + life * .14);',
    'float fracture = (core * .18 + halo * .82) * (.07 + .15 * breath + .12 * saturate(wake));':'float fracture = (core * .28 + halo * .72) * (.15 + .15 * breath + .12 * saturate(wake));',
    'float coverage = (1 - exp2(-1.8 * (body + aura * .22))) * SpiritOpacity * (.72 + .28 * breath);':'float coverage = (1 - exp2(-2.2 * (body + aura * .22))) * SpiritOpacity * (.86 + .14 * breath);\n// Keep the actual fracture glyph readable while the two echoes fade out.\nfloat restingCoverage = saturate(core * .72 + halo * .28) * SpiritRestOpacity;\ncoverage = max(coverage, restingCoverage);',
    'float brightness = SpiritBrightness * (.62 + .38 * saturate(body)) * (.82 + .18 * breath);':'float brightness = SpiritBrightness * (.76 + .24 * saturate(body)) * (.90 + .10 * breath);',
    'emission *= min(1, 1.15 / max(peak, .0001));':'emission *= min(1, EmissionPeak / max(peak, .0001));',
}
for old,new in changes.items():
    if code.count(old)!=1:raise RuntimeError('Saved material differs from the diagnosed source: '+old)
    code=code.replace(old,new)
(P/'spirit_visible.hlsl').write_text(code,encoding='utf-8')
(P/'parameters.json').write_text(json.dumps({'SpiritOpacity':.78,'SpiritRestOpacity':.14,'SpiritBrightness':2.65,'EmissionPeak':2.4},indent=2)+'\n',encoding='utf-8')
