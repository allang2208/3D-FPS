#pragma once
#include "CoreMinimal.h"

class UNiagaraComponent;

namespace HammerFireSurfaces
{
constexpr int32 PatchCount=32;
struct FPatch
{
    FVector3f A,B,C,Normal;
};
struct FProfile
{
    const TCHAR* Mesh;
    FVector3f Center,Extent;
    int32 Axis;
    FPatch Patches[PatchCount];
};

const FProfile* Find(UObject* Geometry);
// Upload once on equipment/geometry/scale changes, in the head-centred FX frame.
void Configure(UNiagaraComponent* FX,const FProfile& Profile,const FVector& Scale);
}
