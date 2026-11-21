#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "VillageDefenseFocusVisual.generated.h"

class AController;
class APawn;
class AVillageDefenseSection;
class UCameraComponent;
class UMaterialInstanceDynamic;
class UStaticMeshComponent;
struct FStreamableHandle;

/** Local presentation of the aimed barrier and the nearest repairable breach. */
UCLASS()
class FPSGAME_API UVillageDefenseFocusVisual : public UActorComponent
{
    GENERATED_BODY()

public:
    void SetFocus(AVillageDefenseSection* Aimed, AVillageDefenseSection* NearbyDestroyed);

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    TWeakObjectPtr<AVillageDefenseSection> FocusedSection;
    TWeakObjectPtr<AVillageDefenseSection> PreviewSection;
    TWeakObjectPtr<UCameraComponent> BoundCamera;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Outline;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Ghost;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> DepthParts;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> GhostParts;
    TSharedPtr<FStreamableHandle> Load;
    bool bFocusedClosed = false;

    void MaterialsReady();
    void BuildParts(AVillageDefenseSection* Section, bool bGhost, bool bClosed);
    UFUNCTION() void PossessionChanged(APawn* Pawn, AController* Previous, AController* Next);
};
