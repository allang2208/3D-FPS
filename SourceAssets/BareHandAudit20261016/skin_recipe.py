"""Shared bare-skin shader upgrade: Super90 SkinClean (10-11) + JointSurface (10-12) generic parts.

Pure text transform of the Custom-node HLSL; used by material_upgrade.py and
checked offline against the 10-10 sources. Hard-coded Super90 wrist coordinates
and its Surface.a palmar substitute are NOT carried over; the shared materials
keep their WristOrigin/WristForward/WristDorsal parameters and normal-based palmar.
"""
MARK = '// Shared bare skin V8 20261016: Super90 clean-up and wrist transition, shared parameters.'

STEPS = [
    # Softer, wider hand/forearm colour transition across the material seam.
    ('float handAnatomy=smoothstep(-.8,1.5,longitudinal)*(1-ForearmMode);',
     'float handAnatomy=smoothstep(-1.5,2.8,longitudinal)*(1-ForearmMode);'),
    ('float skinDetail=(1-nail)*(1-.60*palmDetail);',
     'float skinDetail=(1-nail)*(1-.60*palmDetail);\n'
     'float cleanPalm=saturate(Surface.a)*(1-ForearmMode);\n'
     '// Filter the micro field only, leaving anatomical atlas UVs intact.\n'
     'float3 cleanDx=dx*2.0,cleanDy=dy*2.0;'),
    ('float4 fieldX=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.yz,dx.yz,dy.yz);',
     'float4 fieldX=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.yz,cleanDx.yz,cleanDy.yz);'),
    ('float4 fieldY=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.xz,dx.xz,dy.xz);',
     'float4 fieldY=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.xz,cleanDx.xz,cleanDy.xz);'),
    ('float4 fieldZ=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.xy,dx.xy,dy.xy);',
     'float4 fieldZ=Texture2DSampleGrad(MicroTexture,MicroTextureSampler,q.xy,cleanDx.xy,cleanDy.xy);'),
    ('restGradient*=MicroNormalStrength*.22*fade*skinDetail*(8/tile);',
     'restGradient*=MicroNormalStrength*lerp(.12,.065,cleanPalm)*fade*skinDetail*(8/tile);'),
    ('microSlope*=min(1,.10/max(length(microSlope),.000001));',
     'microSlope*=min(1,.055/max(length(microSlope),.000001));'),
    ('AnatomicalNormal=normalize(float3(AnatomicalNormal.xy*lerp(.65,1,nail),AnatomicalNormal.z));',
     '// Keep the palm creases readable while softening dorsal and wrist relief.\n'
     'float cleanAnatomy=lerp(.42,.62,cleanPalm)*lerp(.75,1,handAnatomy);\n'
     'AnatomicalNormal=normalize(float3(AnatomicalNormal.xy*lerp(cleanAnatomy,1,nail),AnatomicalNormal.z));'),
    ('float3 toneX=Texture2DSampleGrad(ColourDetail,ColourDetailSampler,q.yz,dx.yz,dy.yz).rgb;',
     'float3 toneX=Texture2DSampleGrad(ColourDetail,ColourDetailSampler,q.yz,cleanDx.yz,cleanDy.yz).rgb;'),
    ('float3 toneY=Texture2DSampleGrad(ColourDetail,ColourDetailSampler,q.xz,dx.xz,dy.xz).rgb;',
     'float3 toneY=Texture2DSampleGrad(ColourDetail,ColourDetailSampler,q.xz,cleanDx.xz,cleanDy.xz).rgb;'),
    ('float3 toneZ=Texture2DSampleGrad(ColourDetail,ColourDetailSampler,q.xy,dx.xy,dy.xy).rgb;',
     'float3 toneZ=Texture2DSampleGrad(ColourDetail,ColourDetailSampler,q.xy,cleanDx.xy,cleanDy.xy).rgb;'),
    ('float broad=f.noise(RestPosition.xy*.12+RestPosition.z*.07)-.5;',
     'float broad=f.noise(RestPosition.xy*.12+RestPosition.z*.07)-.5;\n'
     'float warm=f.noise(RestPosition.xz*.21+float2(13.2,5.4))-.5;'),
    ('float3 sharedColour=WristTint*float3(1.015,1,.99)*(1+broad*.018*forearmVariation);',
     'float3 sharedColour=WristTint*float3(1.015,1,.99)*(1+broad*.030)*float3(1+warm*.025,1+warm*.008,1-warm*.018);'),
    ('float3 colour=lerp(sharedColour,BaseColour,handAnatomy);',
     '// The atlas author multiplies skin by 1-.10*crease. Retain a 3.5%\n'
     '// painted crease instead; never lift the nail colour with this term.\n'
     'float cleanCrease=saturate(Surface.b);\n'
     'float cleanDarkLine=(1-.035*cleanCrease)/max(1-.10*cleanCrease,.90);\n'
     'float3 cleanBaseColour=BaseColour*lerp(1,cleanDarkLine,1-nail);\n'
     'float3 colour=lerp(sharedColour,cleanBaseColour,handAnatomy);'),
    ('colour*=lerp(float3(1,1,1),tone,ColourDetailStrength*.20*skinDetail*fade);',
     'colour*=lerp(float3(1,1,1),tone,ColourDetailStrength*.025*skinDetail*fade);'),
    ('float sharedRough=.50-.02*palmar+.004*broad;',
     'float sharedRough=.50-.018*palmar+.024*broad;'),
    ('float rough=lerp(sharedRough,lerp(sharedRough,Surface.g,.65),handAnatomy);',
     'float rough=lerp(sharedRough,lerp(sharedRough,Surface.g,lerp(.38,.65,nail)),handAnatomy);'),
    ('rough+=(dot(float3(fieldX.a,fieldY.a,fieldZ.a),blend)-.48)*skinDetail*.12*fade;',
     'rough+=(dot(float3(fieldX.a,fieldY.a,fieldZ.a),blend)-.48)*skinDetail*.055*fade;'),
]


# M16 thumb shaders keep their thumb-region weighting; same changes, their own lines.
ALTERNATIVES = {
    'float skinDetail=(1-nail)*(1-.60*palmDetail);':
        ('float skinDetail=(1-nail)*(1-lerp(.60,.38,thumbRegion)*palmDetail);',
         'float skinDetail=(1-nail)*(1-lerp(.60,.38,thumbRegion)*palmDetail);\n'
         'float cleanPalm=saturate(Surface.a)*(1-ForearmMode);\n'
         '// Filter the micro field only, leaving anatomical atlas UVs intact.\n'
         'float3 cleanDx=dx*2.0,cleanDy=dy*2.0;'),
    'colour*=lerp(float3(1,1,1),tone,ColourDetailStrength*.20*skinDetail*fade);':
        ('colour*=lerp(float3(1,1,1),tone,localColourDetail*.20*skinDetail*fade);',
         'colour*=lerp(float3(1,1,1),tone,localColourDetail*.025*skinDetail*fade);'),
}


def upgrade(code):
    """Return (new_code, applied, missing). Already-upgraded code is returned unchanged."""
    if code.startswith(MARK):
        return code, [], []
    applied, missing = [], []
    for old, new in STEPS:
        if code.count(old) != 1 and old in ALTERNATIVES:
            old, new = ALTERNATIVES[old]
        c = code.count(old)
        if c == 1:
            code = code.replace(old, new); applied.append(old[:48])
        else:
            missing.append((old[:60], c))
    return MARK + '\n' + code, applied, missing


if __name__ == '__main__':
    from pathlib import Path
    src = Path(__file__).parent.parent / 'BareSkinSurfaceRework20261010'
    for f in sorted(src.glob('*.hlsl')):
        new, applied, missing = upgrade(f.read_text())
        print(f.name, 'applied', len(applied), 'missing', missing)
