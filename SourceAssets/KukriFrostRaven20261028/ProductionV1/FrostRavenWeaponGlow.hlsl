// A translucent thin frost layer preserves the blade's metal and rune silhouette.
float3 n=normalize(Normal);
float facing=saturate(abs(dot(n,normalize(ToEye))));
float rim=pow(1.0-facing,2.2);
float facet=saturate(dot(n,normalize(float3(-.3,-.45,.84)))*.5+.5);
float breath=.94+.06*sin(Age*1.8);
float intensity=(.22+facet*.30+rim*1.30+EntryBurst*.45)*breath;
return float4(float3(.18,.65,1.0)*intensity,saturate(Strength)*(.22+rim*.40));
