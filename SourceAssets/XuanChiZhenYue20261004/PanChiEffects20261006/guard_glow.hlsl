float left = max(step(0.5, Stacks),ReleaseFlash) * (1-smoothstep(-7,-5,LP.x));
float right = max(step(1.5, Stacks),ReleaseFlash) * smoothstep(5,7,LP.x);
float relief = smoothstep(.79,.97,Texture2DSample(Relief,ReliefSampler,UV).r);
// Facing already contains a cubic Fresnel. Raising it again erased the
// front-facing light (0.06 ^ 2.2 ~= 0.002), especially on the central jade.
float edge = pow(saturate(Facing),.55);
float body = (left+right) * (.10+relief*.68+edge*.22);
float jadeR = length(float2(LP.x,LP.z-1.3));
float jadeRing = smoothstep(1.4,1.9,jadeR) * (1-smoothstep(2.7,3.2,jadeR));
float jade = max(step(2.5,Stacks),ReleaseFlash*.65) * jadeRing * (.65+.35*edge);
float breath = .90+.10*sin(Time*3.7);
float alpha = saturate((body+jade*.88)*breath);
float3 copper = lerp(float3(.90,.28,.035),float3(1,.65,.12),saturate(relief*.6+edge*.2));
// EyeAdaptationInverse keeps this exposure-independent. Remain above the
// bloom threshold on raised carving rather than merely tinting the copper.
return float4(copper*(3.6+Ready*2.4+ReleaseFlash*1.8),alpha);
