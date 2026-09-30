if(Data.a<.0001)return Base;
return normalize(float3(Base.xy*(1.-Data.b*.35)+Data.xy,Base.z));
