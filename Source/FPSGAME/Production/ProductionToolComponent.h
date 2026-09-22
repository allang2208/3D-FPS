#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "ProductionResource.h"
#include "ProductionAxeImpactMotion.h"
#include "../Skills/ColdSteelSkillTypes.h"
#include "ProductionToolComponent.generated.h"

class AFPSGAMECharacter;
class UCameraComponent;
class UStaticMeshComponent;
class USkeletalMeshComponent;
class UAnimSequence;
class USceneComponent;
class USoundBase;
class UParticleSystem;
class UColdSteelPickupPrompt;
struct FStreamableHandle;

/** Local production-tool presentation. Profile owns inventory and depletion commits. */
UCLASS(ClassGroup=(Production),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UProductionToolComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UProductionToolComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    bool IsEquipped() const { return !EquippedId.IsEmpty(); }
    bool IsBusy() const { return Elapsed>=0.f || EquipElapsed>=0.f; }
    void RefreshHeldTool();
    void BeginUse();
    /** Right-click while a shovel is out: raise one 20 cm layer, spending soil. */
    void BeginRefill();
    void CancelUse();
    void ShowFeedback(const FString& Message);
    /** Owner advances the shared hit/pose clock before composing its camera. */
    void AdvanceActionBeforeCamera(float Delta);
    void GetCameraMotion(FVector& Location,FRotator& Rotation) const;
    UPROPERTY(EditAnywhere,Category="Production",meta=(ClampMin="100",ClampMax="500",Units="cm")) float Reach = 320.f;
    // Camera-space travel and angles around the accepted two-hand idle hold.
    UPROPERTY(EditAnywhere,Category="Production|Axe Locomotion",meta=(Units="cm")) FVector AxeWalkTravelCM=FVector(.3f,.8f,.55f);
    UPROPERTY(EditAnywhere,Category="Production|Axe Locomotion",meta=(Units="cm")) FVector AxeRunTravelCM=FVector(.65f,2.8f,1.65f);
    UPROPERTY(EditAnywhere,Category="Production|Axe Locomotion") FRotator AxeWalkAngles=FRotator(.3f,.35f,.65f);
    UPROPERTY(EditAnywhere,Category="Production|Axe Locomotion") FRotator AxeRunAngles=FRotator(1.2f,1.2f,2.4f);
    UPROPERTY(EditAnywhere,Category="Production|Pickaxe Locomotion",meta=(Units="cm")) FVector PickaxeWalkTravelCM=FVector(.3f,.7f,.5f);
    UPROPERTY(EditAnywhere,Category="Production|Pickaxe Locomotion",meta=(Units="cm")) FVector PickaxeRunTravelCM=FVector(.55f,2.3f,1.35f);
    UPROPERTY(EditAnywhere,Category="Production|Pickaxe Locomotion") FRotator PickaxeWalkAngles=FRotator(.3f,.3f,.55f);
    UPROPERTY(EditAnywhere,Category="Production|Pickaxe Locomotion") FRotator PickaxeRunAngles=FRotator(1.f,1.f,2.f);
private:
    friend class UFPSPlayerBodyComponent;
    TWeakObjectPtr<AFPSGAMECharacter> Character;
    UPROPERTY(Transient) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> Pivot;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> ToolMesh;
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> Viewmodel;
    UPROPERTY(Transient) TMap<FName,TObjectPtr<UAnimSequence>> Motions;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> CurrentMotion;
    UPROPERTY(Transient) TObjectPtr<USoundBase> HitSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> SwingSound;
    UPROPERTY(Transient) TObjectPtr<UParticleSystem> ImpactDust;
    UPROPERTY(Transient) TObjectPtr<UColdSteelPickupPrompt> Prompt;
    TSharedPtr<FStreamableHandle> LoadHandle;
    FString EquippedId, Kind, ToolName, Feedback;
    float SwingSeconds=.68f, ContactSeconds=.24f, Elapsed=-1.f, HintCountdown=0, FeedbackSeconds=0;
    float EquipElapsed=-1.f, VisualTime=0.f, SprintBlend=0.f;
    float AxeStridePhase=0.f;
    FVector AxeLocomotionOffset=FVector::ZeroVector;
    FQuat AxeLocomotionRotation=FQuat::Identity;
    bool bContacted=false;
    bool bUsesArms=false, bHitConfirmed=false, bSwingSoundPlayed=false;
    FProductionAxeImpactMotion AxeMotion;
    FColdSteelSkillShot AxeStrike;
    float AxeHarvestReach=320.f, AxeCombatReach=180.f;
    float AxeHarvestRadius=32.f, AxeCombatRadius=24.f;
    bool CanUse() const;
    /** Shared single-target query for the hint and the contact event. */
    bool TraceAxeContact(FProductionResource& Resource,FHitResult& Hit,FString& Reason) const;
    bool ResolveAxeEnemyContact(const FHitResult& Hit);
    bool TraceResource(FProductionResource& Resource,FHitResult& Hit,FString& Reason) const;
    bool ResolveContact();
    bool HasReadyPresentation() const;
    void SampleMotion(FName Clip,float Seconds);
    void UpdateHandPresentation(float Delta);
    void UpdateTwoHandLocomotion(float Delta);
    void UpdateHint();
};
