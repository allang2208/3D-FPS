#pragma once
#include "CoreMinimal.h"

class AFPSGAMECharacter;
class USceneComponent;
namespace HammerFireSurfaces { struct FProfile; }

/** Cosmetic samples from the rendered weapon, never combat traces or aim rays. */
struct FFlameArmorAttachment
{
    TWeakObjectPtr<USceneComponent> Source;
    TWeakObjectPtr<UObject> Geometry;
    FName Section;
    // Skeletal weapon/hand anchor; static parts use their component frame.
    FName Socket;
    uint32 EquipmentIdentity=0;
    FVector Base=FVector::ZeroVector,Tip=FVector::ZeroVector;
    FVector Side=FVector::RightVector,Normal=FVector::UpVector;
    // Cross-section centre (XY) and surface half extents (ZW), in world cm
    // along Side/Normal. Eight measured stations follow curved/widening heads.
    FVector4 Surface[8];
    float Size=.5f,Opacity=1.f;
    bool bSword=false;
    const HammerFireSurfaces::FProfile* HammerSurface=nullptr;
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
    FVector FlameFlow=FVector::ZeroVector;
    FVector SurfaceScale=FVector::OneVector;
    FVector SwordBaseFlow=FVector::ZeroVector,SwordTipFlow=FVector::ZeroVector;
    bool bValid=false;
};

namespace FlameArmorAttachments
{
    constexpr int32 MaxLayers=4;
    void Gather(AFPSGAMECharacter* Player,FFlameArmorAttachments& Out);
}
