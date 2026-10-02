"""Author a localized left-thumb shader from the existing V5 skin shader.

This produces HLSL/parameters only. It does not edit raster images, meshes,
pose data, imported materials, texture packages, or the shared V5 author source.
The consumer must use canonical UV1-3 rest coordinates from BarePalmV7.
"""
import hashlib
import json
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
HERE = Path(__file__).resolve().parent
BASE_SHADER = PROJECT / 'Tools/ModularOutfit/skin_surface_v5.hlsl'
ANATOMY = PROJECT / 'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/WristContourV4/M4_bare_shape.json'


def hlsl_vector(values):
    return 'float3(' + ','.join(f'{value:.10f}' for value in values) + ')'


def author():
    code = BASE_SHADER.read_text(encoding='utf-8')
    frame = json.loads(ANATOMY.read_text(encoding='utf-8'))['anatomy']['l']
    rows = [row for row in frame['digits'] if row['digit'] == 'thumb']

    # Finite capsules avoid the neighboring index finger, the wrist/thenar
    # surface, and all right-hand materials. No UV0 atlas coordinate guesses.
    capsule_method = '''    float thumbCapsule(float3 p,float3 head,float3 axis,float extent,float radius)
    {
        float3 v=p-head;
        float t=dot(v,axis);
        float3 radial=v-axis*clamp(t,0,extent);
        return (1-smoothstep(radius*.96,radius*1.32,length(radial)))
             * smoothstep(-.30,.12,t)
             * (1-smoothstep(extent+.04,extent+.32,t));
    }
'''
    code = code.replace('    float3 rnm(float3 base,float3 detail)', capsule_method + '    float3 rnm(float3 base,float3 detail)')
    mask_lines = ['// V9 local thumb surface; canonical M4 anatomy survives native M16 binding.', 'float thumbRegion=0;']
    for row in rows:
        # Keep the broad thenar/wrist transition untouched; use only the
        # terminal half of the metacarpal capsule for the proximal boundary.
        head = row['head']
        length = row['length']
        if row['segment'] == 1:
            offset = length * .62
            head = [head[i] + row['axis'][i] * offset for i in range(3)]
            length -= offset
        mask_lines.append('thumbRegion=max(thumbRegion,f.thumbCapsule(RestPosition,' + hlsl_vector(head) + ',' + hlsl_vector(row['axis']) + f',{length:.10f},{row["radius"]:.10f}));')
    mask_lines += ['thumbRegion*=1-ForearmMode;', 'float thumbSkin=thumbRegion*(1-nail);']
    code = code.replace('float skinDetail=(1-nail)*(1-.60*palmDetail);', '\n'.join(mask_lines) + '\nfloat skinDetail=(1-nail)*(1-lerp(.60,.38,thumbRegion)*palmDetail);')

    # Preserve V7's accepted soft-palm base normal outside this finite thumb
    # region. The low-pore thumb surface uses shallow relief, not sharpened
    # baked folds or displacement.
    code = code.replace('float3 skinNormal=f.rnm(AnatomicalNormal,detail);', '''float baseNormalScale=(1-ForearmMode)*lerp(1,.58,palmar*(1-nail));
baseNormalScale*=lerp(1,.82,thumbSkin);
float3 skinNormal=f.rnm(normalize(float3(AnatomicalNormal.xy*baseNormalScale,AnatomicalNormal.z)),detail);''')
    code = code.replace('colour*=lerp(float3(1,1,1),tone,ColourDetailStrength*skinDetail*fade);', '''// The atlas' dark painted fold is distinct from its normal relief. Locally
// reduce the painted term while retaining the fold normal and skin microfield.
colour*=lerp(1,(1-.035*Surface.b)/max(1-.10*Surface.b,.90),thumbSkin);
float localColourDetail=ColourDetailStrength*lerp(1,.58,thumbRegion);
colour*=lerp(float3(1,1,1),tone,localColourDetail*skinDetail*fade);''')

    tip = rows[-1]
    nail_body = '''// Separate a translucent nail plate, a narrow free edge, and the adjacent
// living skin instead of the atlas' nearly uniform opaque pink/cream patch.
float3 thumbTip=RestPosition-THUMB_HEAD;
float thumbAlong=dot(thumbTip,THUMB_AXIS)/THUMB_EXTENT;
float thumbAcross=dot(thumbTip,THUMB_ACROSS)/THUMB_RADIUS;
float thumbNail=thumbRegion*saturate(nail);
float localFine=.5*sin(RestPosition.x*19+RestPosition.y*13)*sin(RestPosition.z*23-RestPosition.x*11);
float3 underNail=float3(.36,.235,.185)*(1+broad*.04+localFine*.012);
float rootPink=(1-smoothstep(.24,.52,thumbAlong))*.020;
float3 nailPlate=lerp(underNail,float3(.50,.345,.315),.30)+float3(rootPink,-rootPink*.18,-rootPink*.12);
float freeEdge=smoothstep(.80,.87,thumbAlong)*.13;
nailPlate=lerp(nailPlate,float3(.63,.56,.48),freeEdge);
// Subtle longitudinal plate variation changes highlight width, not skin hue.
float nailVariation=sin(thumbAcross*15)*.005;
colour=lerp(colour,nailPlate,thumbNail);
rough=lerp(rough,.385+nailVariation,thumbNail);
'''
    nail_body = nail_body.replace('THUMB_HEAD', hlsl_vector(tip['head'])).replace('THUMB_AXIS', hlsl_vector(tip['axis'])).replace('THUMB_EXTENT', f'{tip["length"]:.10f}').replace('THUMB_ACROSS', hlsl_vector(tip['across'])).replace('THUMB_RADIUS', f'{tip["radius"]:.10f}')
    code = code.replace('rough=clamp(rough+RoughnessOffset,.30,.64);', nail_body + 'rough=clamp(rough+RoughnessOffset,.30,.64);')
    code = '// V9: finite left-thumb appearance correction; all existing custom inputs/outputs retained.\n' + code
    output = HERE / 'skin_surface_thumb_v9.hlsl'
    output.write_text(code, encoding='utf-8')

    receipt = {
        'schema': 'm16_left_thumb_local_skin_surface_v9_authoring_v1',
        'base_shader': str(BASE_SHADER),
        'base_shader_sha256': hashlib.sha256(BASE_SHADER.read_bytes()).hexdigest(),
        'anatomy_source': str(ANATOMY),
        'anatomy_sha256': hashlib.sha256(ANATOMY.read_bytes()).hexdigest(),
        'output_shader': str(output),
        'output_shader_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'inputs_outputs': 'Same as skin_surface_v5.hlsl; do not add CustomInputs',
        'coordinate_contract': 'BarePalmV7 canonical UV1.xy + UV2.r position; UV2.g + UV3.xy rest normal, full precision; not native M16 PreSkinnedPosition',
        'localization': 'Only left thumb finite rest-space capsules; hand section ForearmMode=0; preserve the shared V7 source material',
        'source_findings': [
            'Anatomical skin/nail atlas is authored procedurally, with uniform opaque nail colour [0.50,0.335,0.285], a 48 percent white edge blend, and 10 percent painted crease darkness.',
            'V5 reuses the generic photographed micro colour across the thumb at strength 0.55 while suppressing palmar micro normals by 60 percent; colored mottling can dominate the shallow natural relief.',
            'Base colour imports use TC_DEFAULT and masks use TC_MASKS; no source evidence of a UV replacement or wrong sRGB flag. Do not report compression as proven root cause.',
        ],
        'changes': {
            'painted_thumb_fold_darkness': '10 percent to 3.5 percent, normal relief retained',
            'thumb_generic_colour_detail_multiplier': .58,
            'thumb_palmar_micro_attenuation': '.60 to .38, preserves physical scale',
            'thumb_macro_normal_multiplier': .82,
            'nail_plate_colour': '70 percent underlying authored skin + 30 percent muted nail tint; narrow 13 percent free-edge blend',
            'nail_roughness': '.385 plus .005 longitudinal variation',
            'right_hand_and_other_digits': 'unchanged',
        },
        'geometry_poses_and_weights_edited': False,
        'raster_images_edited': False,
        'new_texture_samples': 0,
        'new_cpu_tick': False,
        'pom_loop': False,
        'ue_imported': False,
        'compiled': False,
        'runtime_tested': False,
        'rendered': False,
        'consumer_note': 'Duplicate the existing canonical-coordinate M16 hand material/instance into this candidate family, replace only its MP_NORMAL Custom code, retain all existing input wires and additional output connections; assign only the current M16 bare hand slots. Do not run shared family publishers.',
    }
    (HERE / 'authoring.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('THUMB_SURFACE_V9_AUTHOR_SOURCE_WRITTEN', str(output), flush=True)


if __name__ == '__main__':
    author()
