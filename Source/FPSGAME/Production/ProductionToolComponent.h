#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "ProductionResource.h"
#include "ProductionToolComponent.generated.h"

class AFPSGAMECharacter;
class UCameraComponent;
class UStaticMeshComponent;
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
    UPROPERTY(Transient) TObjectPtr<USoundBase> HitSound;
    UPROPERTY(Transient) TObjectPtr<UParticleSystem> ImpactDust;
    UPROPERTY(Transient) TObjectPtr<UColdSteelPickupPrompt> Prompt;
    TSharedPtr<FStreamableHandle> LoadHandle;
    FString EquippedId, Kind, ToolName, Feedback;
    float SwingSeconds=.68f, ContactSeconds=.24f, Elapsed=-1.f, HintCountdown=0, FeedbackSeconds=0;
    bool bContacted=false;
    bool CanUse() const;
    bool TraceResource(FProductionResource& Resource,FHitResult& Hit,FString& Reason) const;
    void ResolveContact();
    void UpdateHint();
};
