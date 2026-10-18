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
class USceneComponent;
struct FStreamableHandle;

/** Shared left-hand consumable use, with a single inventory/effect contact. */
UCLASS(ClassGroup=(Items))
class FPSGAME_API UFPSPotionUseComponent : public UActorComponent
{
    GENERATED_BODY()
    friend class UFPSPlayerBodyComponent;
    friend class UFPSConsumableAuditCommandlet;
    friend class ULargeLambMealAuditCommandlet;
    friend class UBowSkillTrainingAuditCommandlet;
    friend class AShotgunWireAuditController;
public:
    UFPSPotionUseComponent();
    bool TryBegin(const FString& ItemId,const FString& Definition);
    bool IsActive() const { return bActive; }
    bool IsStowingOffhand() const { return bActive && bStowOffhand; }
    float OffhandLowerWeight() const;
    bool IsOffhandWeaponHidden() const;
    bool IsTwoHanded() const { return bActive&&Motion.bTwoHanded; }
    bool UsesBowSupport() const { return bActive&&bBowSupport; }
    bool IsReturningBow() const { return BowReturnWeight>0.f; }
    /** Reset the transient equipment offset before native weapon sampling. */
    void BeginEquipmentFrame();
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
    FPotionArmPose RightArmPose;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> EquipmentPivot;
    struct FEquipmentRoot
    {
        TWeakObjectPtr<USceneComponent> Root,Parent;
        FName Socket;
    };
    TArray<FEquipmentRoot> EquipmentRoots;
    void BeginEquipmentStow();
    void RestoreEquipment();
    FString UsingItem;
    FName PresentationDefinition;
    uint16 PresentationSerial=0;
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
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> ChickenMesh;
    FPotionUseMotion ChickenMotion;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> LambRibsMesh;
    FPotionUseMotion LambRibsMotion;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> SausageMesh;
    FPotionUseMotion SausageMotion;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> LargeLambMesh;
    FPotionUseMotion LargeLambMotion;
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
    bool bStowOffhand=false;
    bool bBowSupport=false,bWaitingForBow=false;
    // Cosmetic recovery after a cancelled two-hand meal. The use transaction
    // ends immediately; the existing presentation parent raises separately.
    float BowReturnWeight=0.f;
    double BowReturnStartedAt=0;
    static constexpr float BowReturnHoldSeconds=.1f;
    static constexpr float OffhandLowerSeconds=.28f;
    static constexpr float OffhandRaiseSeconds=.26f;
};
