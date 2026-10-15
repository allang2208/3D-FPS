// Fixed surface fissures; flowing heat and breathing intensity do not move the rock.
float heat = saturate(Heat.r);
float phase = Heat.g * 6.2831853;
float breathing = 0.84 + 0.16 * sin(Time * PulseSpeed + phase);
float flow = 0.68 + 0.32 * smoothstep(-0.4, 0.8, sin(Time * FlowSpeed - UV.y * 18.0 + phase));
float3 color = lerp(EmberColor, HotColor, pow(heat, 2.0));
return color * heat * EmissionStrength * breathing * flow;
