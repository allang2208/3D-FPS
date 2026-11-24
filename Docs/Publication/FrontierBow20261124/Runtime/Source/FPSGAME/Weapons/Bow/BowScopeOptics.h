#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "Rendering/DrawElements.h"
#include "BowScopeReticle.h"
#include "BowScopeOptics.generated.h"

class UBowWeaponComponent;
class UPrimitiveComponent;
class UCameraComponent;

struct FBowScopePrimitiveState
{
    TWeakObjectPtr<UPrimitiveComponent> Component;
    uint8 Type=0;
    bool bOwnerNoSee=false;
};

/** Owner-local Peakwatch framing and feedback; the shared capture owns its lens. */
UCLASS()
class UBowScopeOptics : public UObject
{
    GENERATED_BODY()
public:
    static bool Enabled();
    void UpdateCamera(UBowWeaponComponent& Bow);
    void Update(UBowWeaponComponent& Bow,float Delta,bool Present);
    void InvalidateAssembly(UBowWeaponComponent& Bow);
    void Release(UBowWeaponComponent& Bow);
    bool OwnsPrimitive(const UPrimitiveComponent* Primitive) const;
    bool HidesPrimitive(const UPrimitiveComponent* Primitive) const;
    float PresentationAlpha() const { return Alpha; }
    const FBowScopeReticleState& ReticleState() const { return Reticle; }
    FVector2D CueOffset(const FGeometry& Geometry,float PixelToLocal) const;
    int32 Paint(const FGeometry& Geometry,FSlateWindowElementList& Elements,int32 Layer,const FLinearColor& Tint) const;

private:
    TWeakObjectPtr<UCameraComponent> OwnedCamera;
    TArray<FBowScopePrimitiveState> Primitives;
    bool bSavedCamera=false,bWasFirstPersonFOV=false;
    float SavedFirstPersonFOV=90.f,Alpha=0.f;
    FBowScopeReticleState Reticle;
    void RestoreCamera();
    void RestoreAssembly(UBowWeaponComponent& Bow);
    void UpdateReticle(const UBowWeaponComponent& Bow,float Delta);
};
