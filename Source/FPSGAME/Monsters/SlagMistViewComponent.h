#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SlagMistViewComponent.generated.h"

class UCameraComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;

/** Screen contamination while the player's eye is inside dense world-space smoke. */
UCLASS(ClassGroup=(Combat))
class FPSGAME_API USlagMistViewComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    USlagMistViewComponent();
    static USlagMistViewComponent* GetOrAdd(AActor* Pawn);
    float BlindRemaining() const;
    void ClearBlindness();
    virtual void TickComponent(float DeltaSeconds, ELevelTick Type, FActorComponentTickFunction* Fn) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void RefreshBlindness(float Seconds);
    void RemoveViewLayer();
    UPROPERTY() TObjectPtr<UMaterialInterface> ViewMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ViewInstance;
    TWeakObjectPtr<UCameraComponent> BoundCamera;
    double BlindUntil = 0., NextDisplayRefresh = 0.;
    float BlurStrength = 0.f;
    bool bShowBlindTile = false;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> ActiveViewMaterial;
};
