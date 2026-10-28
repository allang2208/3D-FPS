// Temporary whole-assembly overlay. Geometry normals keep the blade, grip and
// attachments legible while the crimson body and hotter edges emit red light.
float3 n=normalize(Normal);
float facing=saturate(abs(dot(n,normalize(ToEye))));
float rim=pow(1.0-facing,2.4);
float facet=.48+.52*saturate(dot(n,normalize(float3(-.3,-.45,.84)))*.5+.5);
float breath=.94+.06*sin(Age*2.3);
float intensity=(.65+facet*.90+rim*2.30+EntryBurst*.90)*breath;
return float4(float3(1.0,.008,.022)*intensity,saturate(Strength)*.96);
