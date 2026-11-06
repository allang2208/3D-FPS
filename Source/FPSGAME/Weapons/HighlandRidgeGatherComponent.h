#pragma once
#include "Components/DynamicMeshComponent.h"
#include "HighlandRidgeGatherComponent.generated.h"

/** Cosmetic shoulder-to-tip ribbons, driven by the thrust's presentation clock. */
UCLASS(Transient)
class FPSGAME_API UHighlandRidgeGatherComponent : public UDynamicMeshComponent
{
    GENERATED_BODY()
public:
    UHighlandRidgeGatherComponent();
    static UHighlandRidgeGatherComponent* CreateFor(AActor* Owner,bool FirstPerson);
    void Present(const FTransform& Eye,const FVector& Tip,const FVector& BladeDirection,float SincePeak,float BeforePeak);
    void Hide();
protected:
    virtual void OnRegister() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> GatherMaterial;
    TSharedPtr<struct FStreamableHandle> MaterialLoad;
    double LastPresented=0.;
};
