#include "../FPSGAMECharacter.h"
#include "ThermalScopeAssets.h"
#include "CommonHK416Parts.h"
#include "RSH12OpticAssets.h"
#include "Super90OpticAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

void AFPSGAMECharacter::SetThermalOptic()
{
    if(!bInventoryWeaponReady){SetGunsmithOpticVariant(TEXT("false"));return;}
    if(HasThermalScope()&&HolographicOptic&&HolographicOptic->GetStaticMesh())
    {
        HolographicOptic->SetVisibility(true);if(LPVORing)LPVORing->SetVisibility(true);
        return; // A profile refresh is not a new installation or a zoom reset.
    }
    // The shared attachment resource list preloads these for previews/pickups.
    // Resolve only at an actual part change, just like the host's native optics.
    auto* Body=LoadObject<UStaticMesh>(nullptr,*ThermalScopeAssets::MeshPath(ActiveInventoryWeaponDefinition));
    auto* Selector=LoadObject<UStaticMesh>(nullptr,*ThermalScopeAssets::SelectorPath(ActiveInventoryWeaponDefinition));
    if(!Body||!Selector){UE_LOG(LogTemp,Error,TEXT("Thermal optic assets unavailable for %s"),*ActiveInventoryWeaponDefinition);return;}
    SetGunsmithOpticVariant(CommonHK416Parts::OpticInterface(ActiveInventoryWeaponDefinition));
    if(!bHolographicOptic||!HolographicOptic)return;
    if(LPVORing){LPVORing->DestroyComponent();LPVORing=nullptr;}
    HolographicOptic->EmptyOverrideMaterials();HolographicOptic->SetStaticMesh(Body);
    // These two measured rails have optic-specific offsets; use their neutral
    // rail seat for this 99 mm thermal housing. Super90 seats directly on its
    // receiver rail; RSH12 retains its own adapter.
    if(IsRSH12Weapon())HolographicMount=RSH12OpticAssets::OpticMount(ThermalScopeAssets::Id);
    if(IsSuper90Weapon())HolographicMount=Super90OpticAssets::OpticMount(AKMViewmodel,ThermalScopeAssets::Id);
    HolographicOptic->SetRelativeTransform(HolographicMount);
    LPVORing=NewObject<UStaticMeshComponent>(this);
    LPVORing->SetStaticMesh(Selector);LPVORing->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    LPVORing->SetCastShadow(false);LPVORing->bReceivesDecals=false;
    LPVORing->SetOnlyOwnerSee(AKMViewmodel->bOnlyOwnerSee);
    LPVORing->SetFirstPersonPrimitiveType(AKMViewmodel->FirstPersonPrimitiveType);
    LPVORing->SetupAttachment(HolographicOptic,TEXT("ZoomPivot"));LPVORing->RegisterComponent();
    OpticVariant=ThermalScopeAssets::Id;ThermalZoomIndex=0;bSightCalibrated=false;
}
