// Retain the original breathing rhythm with a lower blue peak so fine cuts stay readable.
return Mask*float3(.055,.30,.68)*(.85+.15*sin(Time*1.5));
