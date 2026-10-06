#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../../Skills/FPSCastingMeshComponent.h"
#include "FPSUnarmedIdleComponent.generated.h"

class UCameraComponent;
class UColdSteelStatusModel;
class USkeletalMesh;
class UFPSFootstepAudioComponent;
class UFPSQuickCombatComponent;
struct FStreamableHandle;

/** The empty-hand base is evaluated before the existing left-hand actions. */
UCLASS()
class FPSGAME_API UFPSUnarmedArmsMeshComponent : public UFPSCastingMeshComponent
{
    GENERATED_BODY()
public:
    void SetMotionSample(float Weight,float EnterWeight,float Phase,float Move,float Run);
    void CapturePunchEntry();
    void SetPunchSample(float Age,int32 Side) {PunchAge=Age;PunchSide=Side;}
    virtual void FinalizeBoneTransform() override;
private:
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    TArray<FTransform> Reference,Keys[2];
    TArray<int32> ArmBones;
    TArray<FTransform> WalkKeys,RunKeys;
    TArray<int32> GaitBones;
    int32 GaitSamples=0,CachedRevision=0;
    int32 LowerBones[2]={INDEX_NONE,INDEX_NONE};
    float BreathWeight=0.f,EntryWeight=1.f;
    float StridePhase=0.f,MoveWeight=0.f,RunWeight=0.f;
    void CacheIdlePose();
    TWeakObjectPtr<USkeletalMesh> PunchMesh;
    TArray<FTransform> PunchKeys[2][8],PunchEntry;
    TArray<int32> PunchBones[2];
    FVector2D CurrentJoints[2]={FVector2D::ZeroVector,FVector2D::ZeroVector};
    FVector2D EntryJoints[2]={FVector2D::ZeroVector,FVector2D::ZeroVector};
    int32 PunchRevision=0,PunchSide=1;
    float PunchAge=-1.f;
    void CachePunchPose();
    void ApplyPunchPose(TArray<FTransform>& LocalPose);
};

/** Local first-person fists when the active primary and offhand are empty. */
UCLASS(ClassGroup=(Player))
class FPSGAME_API UFPSUnarmedIdleComponent : public UActorComponent
{
    GENERATED_BODY()
    friend class UFPSPlayerBodyComponent;
    friend class UFPSConsumableAuditCommandlet;
public:
    UFPSUnarmedIdleComponent();
    bool IsEquipped() const {return bHandsEmpty&&bEquipmentResolved;}
    USkeletalMeshComponent* ArmsMesh() const { return Arms; }
    bool IsPunching() const;
    bool IsTriggerHeld() const {return bTriggerHeld;}
    int32 GetPunchSide() const {return PunchSide;}
    void SetTriggerHeld(bool Held);
    void CancelAttack();
    void AdvanceActionBeforeCamera(float Delta);
    bool GetStrikeProbe(FVector& Origin);
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
    UPROPERTY(Transient) TObjectPtr<UFPSUnarmedArmsMeshComponent> Arms;
    TWeakObjectPtr<UCameraComponent> Camera;
    TWeakObjectPtr<UColdSteelStatusModel> Model;
    TWeakObjectPtr<UFPSQuickCombatComponent> Combat;
    TSharedPtr<FStreamableHandle> Load;
    FDelegateHandle EquipmentChanged;
    bool bHandsEmpty=false,bLoadRequested=false,bEquipmentResolved=false;
    float CycleTime=0.f,VisibleAge=0.f;
    void RefreshEquipment();
    void LoadArms();
    void ApplyLoadedArms();
    bool ShouldShow() const;
    void UpdateVisibility();
    TWeakObjectPtr<UFPSFootstepAudioComponent> Footsteps;
    float MoveBlend=0.f,RunBlend=0.f,GaitPhase=0.f;
    bool bTriggerHeld=false;
    int32 NextPunchSide=1,PunchSide=1;
    bool CanPunch() const;
    bool BeginPunch();
    void RefreshPunchSample();
};
