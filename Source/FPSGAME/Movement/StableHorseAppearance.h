#pragma once
#include "CoreMinimal.h"

// The phenotype is derived from the permanent horse ID. Keep the R30 seed, draw order
// and category order stable so a saved mare or gelding keeps its markings on recall.
struct FStableHorseAppearance
{
    enum class EMane : uint8 { Crop, Sweep, Parted };
    enum class ETail : uint8 { Bob, Fan, Side };
    int32 Coat=0,Patch=1,Pattern=0;
    EMane Mane=EMane::Crop;
    ETail Tail=ETail::Bob;
    FLinearColor CoatColour,PatchColour,HairColour;
    FVector4f Projection=FVector4f(0,0,.01f,1.2f);
    float ManeCoverage=1.f,TailCoverage=1.f,ManeLength=1.f,Feather=.03f;
    float TailLength=1.f,TailWidth=1.f,TailSweepCm=0.f;
    static FStableHorseAppearance FromId(const FGuid& Id);
    FString CoatDescription() const;
    FString HairDescription() const;
    FString Describe() const;
    void ApplyPigment(class UPrimitiveComponent& Body,class UPrimitiveComponent& Fibres) const;
};
