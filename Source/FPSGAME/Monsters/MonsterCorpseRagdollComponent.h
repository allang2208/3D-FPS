#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Animation/PoseSnapshot.h"
#include "MonsterRagdollPhysics.h"
#include "MonsterCorpseRagdollComponent.generated.h"

class USkeletalMeshComponent;

UENUM(BlueprintType)
enum class EMonsterCorpseRig : uint8 { Canine, Maggot, HandBrain, FleshHand, Mawcrawler, HangingBell };

/** Death-only physics; no living knockdown/get-up behavior and no idle tick. */
UCLASS(ClassGroup=AI)
class FPSGAME_API UMonsterCorpseRagdollComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UMonsterCorpseRagdollComponent();
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float DeltaSeconds, ELevelTick TickType, FActorComponentTickFunction* TickFunction) override;

    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Corpse") EMonsterCorpseRig Rig = EMonsterCorpseRig::Canine;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Corpse", meta=(ClampMin="0", Units="s")) float MinimumPhysicsSeconds = .75f;
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Corpse", meta=(ClampMin=".1", Units="s")) float StableSeconds = .35f;

    void PrepareDeath(USkeletalMeshComponent* Mesh);
    void RecordDeathPose(USkeletalMeshComponent* Mesh, float DeltaSeconds, bool bPoseAlreadyEvaluated = false);
    bool Start(USkeletalMeshComponent* Mesh, const FVector& ImpactVelocity = FVector::ZeroVector);
    bool WasAttempted() const { return bAttempted; }
    void FreezeAnimatedPose(USkeletalMeshComponent* Mesh);
    int32 SimulatedBodyCount() const { return bSimulating ? PhysicsBodyCount : 0; }
    bool CanReleaseCorpseBudget() const;
    void FreezeForBudget();
private:
    FName SelectAnchor(USkeletalMeshComponent* Mesh) const;
    void AlignRootAndTune();
    void FreezePose(bool bFromPhysics);
    void ReleaseBudget();

    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> BodyMesh;
    UPROPERTY(Transient) FPoseSnapshot FrozenPose;
    FName AnchorBone;
    FTransform PreviousAnchor = FTransform::Identity;
    FVector InheritedVelocity = FVector::ZeroVector;
    FVector PoseVelocity = FVector::ZeroVector;
    FVector PoseAngularVelocity = FVector::ZeroVector;
    FMonsterRagdollHandoff Handoff;
    int32 PhysicsBodyCount = 0;
    float PhysicsAge = 0.f, ProbeAge = 0.f, StableAge = 0.f;
    bool bHavePreviousPose = false, bAttempted = false, bSimulating = false;
    bool bFrozen = false, bGrounded = false, bBudgetOwned = false;
};
