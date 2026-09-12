// Preserve a readable, antialiased core at gameplay distances (UE units: cm).
float2 p = (UV - .5) * 2;
float width = lerp(3.0, 7.0, Random);
float len = lerp(.68, .98, frac(Random * 13.7));
float a = exp(-p.x * p.x * width) * pow(saturate(1 - abs(p.y) / len), .85);
return a * smoothstep(0, .06, Age) * (1 - smoothstep(.85, 1, Age))
    * smoothstep(65, 160, Depth) * (1 - smoothstep(2000, 3000, Depth)) * .58;
