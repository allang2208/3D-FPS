#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSRiftBladeComponent.generated.h"

class URuneSwordComponent;
class UColdSteelStatusModel;
class UFPSCombatHealthComponent;
class USceneComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;
struct FStreamableHandle;

/** Local held-sword refraction, owned by the equipped Rift Slash instance. */
UCLASS(ClassGroup=(Weapons))
class FPSGAME_API UFPSRiftBladeComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSRiftBladeComponent();
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
    UPROPERTY(EditDefaultsOnly,Category="Enchantment") TSoftObjectPtr<UStaticMesh> RibbonAsset;
    UPROPERTY(EditDefaultsOnly,Category="Enchantment") TSoftObjectPtr<UMaterialInterface> DistortionAsset;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> RibbonMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> DistortionMaterial;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> BladeAnchor;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Ribbons;
    TWeakObjectPtr<URuneSwordComponent> Sword;
    TWeakObjectPtr<UFPSCombatHealthComponent> Health;
    TWeakObjectPtr<UColdSteelStatusModel> Profile;
    TSharedPtr<FStreamableHandle> LoadHandle;
    FDelegateHandle ProfileChanged;
    FString VisualItem;
    uint32 VisualDataHash=0;
    float Age=0.f;
    bool bEnabled=false;
    void RefreshEquipment();
    void ClearBlade();
};
