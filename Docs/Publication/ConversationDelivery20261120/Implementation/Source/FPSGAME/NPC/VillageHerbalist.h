#pragma once

#include "GameFramework/Actor.h"
#include "ResidentConversation.h"
#include "VillageHerbalist.generated.h"

class USkeletalMeshComponent;
class UCapsuleComponent;
class UAnimSequence;
struct FStreamableHandle;

/** One straight, clearance-tested leg. Positions use the network's zero-origin coordinate frame. */
USTRUCT()
struct FHerbalistRoamLeg
{
    GENERATED_BODY()

    UPROPERTY() FVector_NetQuantize10 Start = FVector::ZeroVector;
    UPROPERTY() FVector_NetQuantize10 End = FVector::ZeroVector;
    UPROPERTY() float StartYaw = 0.f;
    UPROPERTY() float EndYaw = 0.f;
    UPROPERTY() double ServerTime = 0.;
};

/** Lin Zhi works on the ground floor of the restored apothecary. */
UCLASS()
class FPSGAME_API AVillageHerbalist : public AActor
{
    GENERATED_BODY()

public:
    AVillageHerbalist();
    void SetLocalConversation(APlayerController* Player);
    void SetConversationParticipant(APlayerController* Player, bool bTalking);
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;

private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> Body;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCapsuleComponent> Capsule;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> WalkClip;
    UPROPERTY(ReplicatedUsing=OnRep_RoamLeg) FHerbalistRoamLeg RoamLeg;
    FResidentConversationFacing ConversationFacing;
    TWeakObjectPtr<APlayerController> LocalTalker;
    TSharedPtr<FStreamableHandle> AppearanceLoad;
    TSet<TWeakObjectPtr<APlayerController>> Talkers;
    FTimerHandle NextStopTimer;
    FTransform ShopFrame;
    int32 PreviousStop = INDEX_NONE;
    int32 TargetStop = INDEX_NONE;
    float WalkWeight = 0.f;
    float WalkPhase = 0.f;
    bool bHaveRoamLeg = false;

    void ApplyAppearance();
    void StartConversationIdle();
    void UpdateGait(float DeltaSeconds, float Distance);
    void ChooseNextStop();
    void WaitAtStop(float Delay);
    void PublishLeg(const FVector& Target, float TargetYaw);
    bool CanWalkBetween(const FVector& From, const FVector& To) const;
    double ServerNow() const;
    UFUNCTION() void OnRep_RoamLeg();
};
