from pathlib import Path
P=Path(__file__).resolve().parent
old=(P.parent/'FrostSpiritBurst20260922/spirit_burst.hlsl').read_text(encoding='utf-8')
prefix=old.split('// Three amethyst nodes:')[0]
(P/'spirit_blend.hlsl').write_text(prefix+(P/'spirit_blend_tail.hlsl').read_text(encoding='utf-8'),encoding='utf-8')
print('FROST_SPIRIT_BLEND_SOURCE_READY')
