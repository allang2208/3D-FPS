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
    void CaptureFocusReturn(bool Detached);
    void SetFocusPose(float Time,float Weight,bool Returning) {FocusPoseTime=Time;FocusPoseWeight=Weight;bFocusReturning=Returning;}
    void SetFocusReturn(float Progress) {FocusPoseTime=0.f;FocusPoseWeight=1.f;bFocusReturning=true;ReturnProgress=Progress;}
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
    float FocusPoseTime=-1.f,FocusPoseWeight=0.f;
    bool bFocusReturning=false;
    void CacheFocusPose();
    void ApplyFocusPose(TArray<FTransform>& LocalPose);
    TArray<TArray<FTransform>> ReturnKeys;
    TArray<FTransform> ReturnEntry;
    float ReturnProgress=0.f;
    bool bReturnDetached=false;
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
    bool IsFocusActive() const {return FocusAge>=0.f;}
    FVector FocusCatchOffset() const;
    USkeletalMeshComponent* ArmsMesh() const {return Arms;}
    UStaticMeshComponent* BookMesh() const {return Book;}
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
    bool bFocusPair=false,bFocusDesired=false,bFocusClosing=false,bFocusDetached=false,bQueuedBookStrike=false;
    float FocusAge=-1.f,PagePhase=0.f,PageAlpha=0.f,OpenAlpha=0.f,DetachAge=0.f;
    float CloseAge=0.f,ClosePageAlpha=0.f,CloseOpenAlpha=0.f,CloseResetSeconds=0.f,CloseBookSeconds=0.f;
    FTransform FocusDepartCamera=FTransform::Identity,FocusReturnCamera=FTransform::Identity;
    void CreateFocusMeshes();
    void BeginCloseFocus();
    void AdvanceFocus(float Delta);
    void PresentFocusBook();
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> FocusGold;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FocusGoldMaterial;
    float GoldFade=0.f;
    void CreateFocusGold(UMaterialInterface* Material);
    void PresentFocusGold();
    void ShowFocusGold(bool Visible);
};
