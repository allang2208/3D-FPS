// V3: visible flowing distortion with blue-violet caustics. XY = normal,
// Z = feathered coverage, W = luminous filaments. No solid/closed ring.
float along = saturate(UV.x);
float across = saturate(UV.y);
float clock = Time + Phase * 6.2831853;
float tips = smoothstep(0.0, .10, along) * (1.0 - smoothstep(.86, 1.0, along));
float sides = pow(saturate(sin(across * 3.14159265)), .95);
float traveling = .5 + .5 * sin(along * 18.0 - clock * 2.8 + sin(across * 7.0 + clock) * 1.7);
float opening = smoothstep(.05, .55, .5 + .5 * sin(along * 12.0 - clock * 1.7));
float mask = tips * sides * (.74 + .26 * traveling) * (.40 + .60 * opening);
float nx = .52 * sin(along * 23.0 - clock * 3.1 + cos(across * 8.0 + clock) * 2.0)
         + .13 * sin(along * 61.0 + clock * 4.7);
float ny = .58 * sin(across * 7.0 + along * 14.0 - clock * 2.7);
float warp = .10 * sin(along * 16.0 - clock * 2.6);
float filament = exp(-pow((across - .42 - warp) * 15.0, 2.0));
float counter = exp(-pow((across - .70 + warp * .65) * 20.0, 2.0));
float broken = .46 + .54 * smoothstep(.1, .8, .5 + .5 * sin(along * 41.0 + clock * 3.8));
float caustics = saturate(filament + counter * .58) * broken * (.65 + .35 * traveling);
return float4(nx, ny, mask, caustics);
