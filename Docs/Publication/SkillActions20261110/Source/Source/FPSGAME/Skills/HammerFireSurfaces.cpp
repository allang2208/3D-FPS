#include "HammerFireSurfaces.h"
#include "NiagaraComponent.h"

namespace HammerFireSurfaces
{
#include "HammerFireSurfaceData.inl"

const FProfile* Find(UObject* Geometry)
{
    if(!Geometry)return nullptr;
    static TMap<TWeakObjectPtr<UObject>,const FProfile*> Cache;
    const TWeakObjectPtr<UObject> Key=Geometry;
    if(const auto* Found=Cache.Find(Key))return *Found;
    if(Cache.Num()>=64)Cache.Reset();
    const FString Path=Geometry->GetPathName();
    const FProfile* Result=nullptr;
    for(const auto& Profile:Profiles)if(Path==Profile.Mesh){Result=&Profile;break;}
    Cache.Add(Key,Result);
    return Result;
}

void Configure(UNiagaraComponent* FX,const FProfile& Profile,const FVector& Scale)
{
    struct FParameterNames
    {
        FName Names[PatchCount][4];
        FParameterNames()
        {
            const TCHAR* Prefix[]={TEXT("A"),TEXT("B"),TEXT("C"),TEXT("N")};
            for(int32 I=0;I<PatchCount;++I)for(int32 J=0;J<4;++J)
                Names[I][J]=FName(*FString::Printf(TEXT("User.Hammer%s%d"),Prefix[J],I));
        }
    };
    static const FParameterNames Parameters;
    const FVector InverseScale=FTransform::GetSafeScaleReciprocal(Scale);
    for(int32 I=0;I<PatchCount;++I)
    {
        const auto& P=Profile.Patches[I];
        FX->SetVariableVec3(Parameters.Names[I][0],FVector(P.A-Profile.Center)*Scale);
        FX->SetVariableVec3(Parameters.Names[I][1],FVector(P.B-Profile.Center)*Scale);
        FX->SetVariableVec3(Parameters.Names[I][2],FVector(P.C-Profile.Center)*Scale);
        FX->SetVariableVec3(Parameters.Names[I][3],(FVector(P.Normal)*InverseScale).GetSafeNormal());
    }
}
}
