// Dynamic body/stab ribbon: UV.x is sample age, UV.y spans the swept section.
float age = saturate(UV.x);
float v = saturate(UV.y);
float fade = 1.-smoothstep(.08,1.,age);
float taper = smoothstep(0.,.12,v)*(1.-smoothstep(.91,1.,v));
float rim = exp2(-180.*(v-.74)*(v-.74));
float inner = exp2(-300.*(v-.36)*(v-.36));
float3 color = float3(1.65,.57,.055) + float3(3.35,1.96,.39)*rim + float3(1.13,.55,.10)*inner;
return float4(color, fade*taper*(.27+.60*rim+.32*inner));
