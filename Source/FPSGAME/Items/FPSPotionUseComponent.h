#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "PotionUseMotion.h"
#include "PotionArmPose.h"
#include "TimerManager.h"
#include "FPSPotionUseComponent.generated.h"

class UFPSCastingMeshComponent;
class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class USoundBase;
class UAudioComponent;
struct FStreamableHandle;

/** Shared left-hand consumable use, with a single inventory/effect contact. */
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
    static bool IsDrink(const FString& Definition);
    static bool IsFood(const FString& Definition);
    static bool IsAnimatedConsumable(const FString& Definition);
    /** Shared by drinks and world refills. Zero duration plays one random swallow. */
    UFUNCTION(BlueprintCallable,Category="Consumables|Audio")
    bool PlayHydrationAudio(float Duration=0.f);
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
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> WaterMaterial;
    FPotionUseMotion WaterMotion;
    bool bWater=false;
    float WaterStartFill=1.f,WaterEndFill=.5f,WaterBottomCm=.35f,WaterFullCm=18.4f;
    float LastWaterLevel=-1.f;
    uint64 LastHandPoseFrame=MAX_uint64;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> FoodMesh;
    FPotionUseMotion FoodMotion;
    bool bFood=false;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> BreadMesh;
    FPotionUseMotion BreadMotion;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> WaterSwallowSounds;
    UPROPERTY(Transient) TObjectPtr<USoundBase> FoodSwallowSound;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> SwallowAudio;
    FTimerHandle SwallowTimer;
    double HydrationAudioEnd=0;
    bool bSwallowStarted=false;
    void PlayNextWaterSwallow();
    void EndHydrationAudio();
    void StopSwallowAudio();
    void PlayFoodSwallow();
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> SodaMesh;
    FPotionUseMotion SodaMotion;
    bool bSoda=false;
};
