#pragma once
#include "CoreMinimal.h"
#include "GunsmithSystem.h"
#include "SwordGripClearance.h"
class UStaticMeshComponent;
class UStaticMesh;
class FJsonObject;

// Shared assembly contract for held, workbench, inventory and dropped swords.
namespace ColdSteelModularSword
{
    struct FModuleGeometry
    {
        FString Slot,Mesh;
        TArray<FString> Materials;
        FTransform RelativeTransform=FTransform::Identity;
        bool bRoot=false;
    };
    // Inventory-backed geometry for remote holders that have no first-person components.
    TArray<FModuleGeometry> DescribeGeometry(const FColdSteelItem& Item);
    // Shared local/remote cosmetic settings, resolved only when creating a part.
    TSharedPtr<FJsonObject> HangingDynamics(const UStaticMesh* Mesh);
    void ResetCatalogCache();
    bool Supports(const FColdSteelItem& Item);
    FString ArmsMesh(const FColdSteelItem& Item);
    FString AnimationFolder(const FColdSteelItem& Item);
    FSwordGripFit GripClearance(const FColdSteelItem& Item);
    bool UsesOverheadFinisher(const FColdSteelItem& Item,const FGunsmithParts* Draft=nullptr);
    bool UsesRisingDragonFinisher(const FColdSteelItem& Item,const FGunsmithParts* Draft=nullptr);
    bool UsesChixiaoDoubleHeavy(const FColdSteelItem& Item);
    bool UsesZhufengWhirlwind(const FColdSteelItem& Item);
    void GatherVisualResources(const FColdSteelItem& Item,TArray<FSoftObjectPath>& Out,const FGunsmithParts* Draft=nullptr);
    FString Key(const FColdSteelItem& Item,const FGunsmithParts* Draft=nullptr,bool IncludeRune=true);
    uint8 BladeFinishMode(const FColdSteelItem& Item,const FGunsmithParts* Draft=nullptr);
    bool IsBladeFinishCarrier(const UStaticMeshComponent* Mesh,const FColdSteelItem& Item);
    uint32 BladeFinishSeed(const FColdSteelItem& Item,const FGunsmithParts* Draft=nullptr);
    void ApplyBladeFinish(UStaticMeshComponent* Mesh,uint8 Mode,bool GuardRoot,uint32 FinishSeed=0);
    // Colored glass transmission needs an alpha-coverage adapter in UI captures.
    bool ApplyGlassPreview(UStaticMeshComponent* Blade);
    bool Apply(UStaticMeshComponent* Blade,const FColdSteelItem& Item,const FGunsmithParts* Draft=nullptr,bool IncludeRune=true);
    void Clear(UStaticMeshComponent* Blade);
    TArray<UStaticMeshComponent*> Components(UStaticMeshComponent* Blade);
    FBox LocalBounds(UStaticMeshComponent* Blade);
    FTransform BoneMount(const FColdSteelItem& Item);
    FString Appearance(const FColdSteelItem& Item,const FString& Slot,const FString& Option);
    FVector BladePoint(const FColdSteelItem& Item,bool Tip);
}
