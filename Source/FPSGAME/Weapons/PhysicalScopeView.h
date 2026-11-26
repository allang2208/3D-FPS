#pragma once
#include "CoreMinimal.h"

class UMeshComponent;
class UMaterialInterface;

namespace PhysicalScopeMaterials
{
    // Returns the installed surface beneath a local ADS override, including a custom finish.
    UMaterialInterface* ForWorldEquipment(const UMeshComponent* Mesh,int32 Slot,UMaterialInterface* Current);
}
// IDs are also the ReticleStyle parameter of M_PhysicalScopeLens.
enum class EPhysicalScopeStyle : uint8 { M24, LPVO, Prism, KV, PSO, Handgun, Thermal, Peakwatch, SVChKV, SVDFactory };
struct FPhysicalScopeView
{
    UMeshComponent* Mesh=nullptr;
    int32 Glass=INDEX_NONE, OriginalReticle=INDEX_NONE;
    EPhysicalScopeStyle Style=EPhysicalScopeStyle::M24;
    FVector Center=FVector::ZeroVector,Forward=FVector::ForwardVector;
    FVector Right=FVector::RightVector,Up=FVector::UpVector;
    FVector2D Radius=FVector2D(1,1);
    float CaptureRadiusScale=1.f;
    float RearDepth=1.f;
    FLinearColor BowDrawState=FLinearColor::Transparent;
    float BowRelease=0.f;
};
