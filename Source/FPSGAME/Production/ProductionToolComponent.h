#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "ProductionResource.h"
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
    void CancelUse();
    void ShowFeedback(const FString& Message);
    UPROPERTY(EditAnywhere,Category="Production",meta=(ClampMin="100",ClampMax="500",Units="cm")) float Reach = 320.f;
private:
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
    bool bContacted=false;
    bool bUsesArms=false, bHitConfirmed=false, bSwingSoundPlayed=false;
    bool CanUse() const;
    bool TraceResource(FProductionResource& Resource,FHitResult& Hit,FString& Reason) const;
    bool ResolveContact();
    bool HasReadyPresentation() const;
    void SampleMotion(FName Clip,float Seconds);
    void UpdateHandPresentation(float Delta);
    void UpdateHint();
};
