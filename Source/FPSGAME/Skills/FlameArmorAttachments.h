#pragma once
#include "CoreMinimal.h"

class AFPSGAMECharacter;
class USceneComponent;

/** Cosmetic samples from the rendered weapon, never combat traces or aim rays. */
struct FFlameArmorAttachment
{
    TWeakObjectPtr<USceneComponent> Source;
    TWeakObjectPtr<UObject> Geometry;
    FName Section;
    uint32 EquipmentIdentity=0;
    FVector Base=FVector::ZeroVector,Tip=FVector::ZeroVector;
    float Size=.5f,Opacity=1.f;
};
struct FFlameArmorAttachmentBuffer : TArray<FFlameArmorAttachment,TInlineAllocator<4>> {};
using FFlameArmorAttachments=FFlameArmorAttachmentBuffer;

struct FFlameArmorHistory
{
    TWeakObjectPtr<USceneComponent> Source;
    TWeakObjectPtr<UObject> Geometry;
    FName Section;
    uint32 EquipmentIdentity=0;
    FVector Base=FVector::ZeroVector,Tip=FVector::ZeroVector;
    bool bValid=false;
};

namespace FlameArmorAttachments
{
    constexpr int32 MaxLayers=4;
    void Gather(AFPSGAMECharacter* Player,FFlameArmorAttachments& Out);
}
