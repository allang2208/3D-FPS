#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../../Skills/FPSCastingMeshComponent.h"
#include "../Staff/StaffLocomotion.h"
#include "SpellbookComponent.generated.h"

class UCameraComponent;
class UStaticMeshComponent;
class UColdSteelStatusModel;
class UFPSFootstepAudioComponent;
class UAnimSequence;
class UDynamicMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
struct FStreamableHandle;

/** Native V7 left arm; the existing offhand gait drives the whole support chain. */
UCLASS()
class FPSGAME_API USpellbookArmsMeshComponent : public UFPSCastingMeshComponent
{
    GENERATED_BODY()
public:
    float StridePhase=0.f,MoveWeight=0.f,RunWeight=0.f,MotionTime=0.f;
    FVector CarryOffset=FVector::ZeroVector;
    virtual void FinalizeBoneTransform() override;
    void CaptureQuickCombatEntry(uint32 Serial);
    void CaptureFocusEntry();
    void CaptureFocusInterrupt();
    void SetFocusPose(float Time,float Weight,bool Returning) {FocusPoseTime=Time;FocusPoseWeight=Weight;bFocusReturning=Returning;}
    void SetFocusReturn(float SourceTime) {SetFocusPose(SourceTime,1.f,true);}
private:
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    TArray<FTransform> Reference;
    TArray<FTransform> CarryKeys[65];
    TArray<int32> LeftBones,RightBones;
    void CachePose();
    TArray<TArray<FTransform>> StrikeKeys;
    TArray<FTransform> StrikeEntry;
    uint32 StrikeSerial=0;
    void ApplyQuickCombat(TArray<FTransform>& LocalPose);
    TArray<TArray<FTransform>> FocusKeys;
    TArray<FTransform> FocusEntry;
    TArray<FTransform> InterruptEntry;
    float FocusPoseTime=-1.f,FocusPoseWeight=0.f;
    bool bFocusReturning=false;
    void CacheFocusPose();
    void ApplyFocusPose(TArray<FTransform>& LocalPose);
    void ApplyFocusInterruptPose(TArray<FTransform>& LocalPose,const class USpellbookComponent& Book);
};

/** Offhand spellbook: fixed-grip F shove, or staff-only RMB focus with animated pages. */
UCLASS(ClassGroup=(Weapons))
class FPSGAME_API USpellbookComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    USpellbookComponent();
    bool IsEquipped() const {return bEquipped;}
    bool OwnsLeftHand() const;
    bool BeginQuickCombat();
    bool IsQuickCombatActive() const;
    void AdvanceActionBeforeCamera(float Delta);
    bool GetQuickCombatStrikeProbe(FVector& Origin);
    bool ToggleFocus();
    void CancelFocus();
    bool IsFocusActive() const;
    bool IsFocusEmpowered() const;
    bool IsConcentrating() const;
    float FocusMovementMultiplier() const {return IsConcentrating()?FocusMoveMultiplier:1.f;}
    void InterruptFocusFromDamage();
    void ApplyNetFocusRequest(uint32 Session,uint8 State);
    void ReceiveNetFocusStopped(uint32 Session,bool Interrupted);
    bool IsFocusInterrupted() const {return bFocusInterrupted;}
    float FocusInterruptAge() const {return InterruptAge;}
    float FocusInterruptContactSource() const {return InterruptContactSource;}
    FTransform FocusHandSway(float PoseTime) const;
    float FocusRecoveryBlend() const;
    USkeletalMeshComponent* ArmsMesh() const {return Arms;}
    UStaticMeshComponent* BookMesh() const {return Book;}
    USkeletalMeshComponent* FloatingBookMesh() const {return FocusBook;}
    FVector FocusGoldParameters() const;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
    UPROPERTY(Transient) TObjectPtr<USpellbookArmsMeshComponent> Arms;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Book;
    TWeakObjectPtr<UCameraComponent> Camera;
    TWeakObjectPtr<UColdSteelStatusModel> Model;
    TWeakObjectPtr<UFPSFootstepAudioComponent> Footsteps;
    TSharedPtr<FStreamableHandle> Load;
    FDelegateHandle EquipmentChanged;
    FStaffLocomotion Locomotion;
    bool bEquipped=false,bEquipmentResolved=false;
    void RefreshEquipment();
    void ApplyAssets();
    void UpdateVisibility();
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> FocusBook;
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> FocusWorldBook;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> OpenClip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> FlipClip;
    bool bFocusPair=false,bFocusDesired=false,bFocusClosing=false,bFocusDetached=false,bFocusInterrupted=false;
    float FocusMoveMultiplier=.67f,InterruptAge=0.f,InterruptContactSource=0.f;
    float InterruptOpenAlpha=0.f,InterruptGoldFade=0.f;
    TArray<FTransform> InterruptBookEntry,InterruptBookClosed;
    FTransform InterruptBookFrame=FTransform::Identity;
    float FocusAge=-1.f,PagePhase=0.f,PageAlpha=0.f,OpenAlpha=0.f,DetachAge=0.f;
    float CloseAge=0.f,ClosePageAlpha=0.f,ReturnStartTime=0.f,CloseBookSeconds=0.f;
    TArray<int32> PageBones;
    TArray<FTransform> ClosePageDeltas;
    FTransform FocusDepartCamera=FTransform::Identity,FocusReturnCamera=FTransform::Identity;
    void CreateFocusMeshes();
    void BeginCloseFocus();
    void AdvanceFocus(float Delta);
    void PresentFocusBook();
    void AdvanceFocusInterrupt(float Delta);
    void PresentFocusInterruptBook();
    void BeginFocusInterruptPresentation();
    // Transient authority state for remote pawns; independent of first-person meshes.
    uint32 FocusSession=0,NetFocusSession=0;
    double NetFocusStartedAt=-1.0,NetFocusBusyUntil=0.0;
    FString NetFocusBook,NetFocusStaff;
    bool bApplyingFocusReply=false;
    bool UsesNetFocusAuthority() const;
    bool NetFocusEquipmentValid() const;
    void AdvanceNetFocus();
    void SendFocusRequest(uint8 State);
    void StopNetFocus(bool Interrupted);
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> FocusGold;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FocusGoldMaterial;
    float GoldFade=0.f;
    void CreateFocusGold(UMaterialInterface* Material);
    void PresentFocusGold();
    void ShowFocusGold(bool Visible);
};
