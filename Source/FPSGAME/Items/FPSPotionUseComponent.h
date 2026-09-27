#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "PotionUseMotion.h"
#include "PotionArmPose.h"
#include "FPSPotionUseComponent.generated.h"

class UFPSCastingMeshComponent;
class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
struct FStreamableHandle;

/** Left-hand potion use: grab, uncap, drink/commit once, discard, recover. */
UCLASS(ClassGroup=(Items))
class FPSGAME_API UFPSPotionUseComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSPotionUseComponent();
    bool TryBegin(const FString& ItemId,const FString& Definition);
    bool IsActive() const { return bActive; }
    void Cancel();
    void ApplyHandPose(UFPSCastingMeshComponent& Mesh);
    static bool IsPotion(const FString& Definition);
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Bottle;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Liquid;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Stopper;
    UPROPERTY(Transient) TObjectPtr<UFPSCastingMeshComponent> FallbackHands;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMesh>> Assets;
    TSharedPtr<FStreamableHandle> LoadHandle;
    TWeakObjectPtr<UFPSCastingMeshComponent> ActiveHands;
    FPotionUseMotion HealthMotion,ManaMotion,Motion;
    FPotionArmPose ArmPose;
    FString UsingItem;
    double StartTime=0;
    bool bActive=false,bCommitted=false,bUncapped=false,bDiscarded=false;
    float Age() const;
    void Finish();
    void UpdateBottle(const FTransform& PalmWorld);
    void Discard(UStaticMeshComponent* Visual,const FVector& Velocity,float Lifetime);
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInterface>> LiquidMaterials;
};
