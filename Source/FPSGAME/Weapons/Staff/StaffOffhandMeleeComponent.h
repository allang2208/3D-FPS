#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "StaffCastMotion.h"
#include "StaffOffhandMeleeComponent.generated.h"

class UKukriArmsMeshComponent;
class UOffhandKukriArmsMeshComponent;
class USkeletalMeshComponent;
class UStaticMeshComponent;
class UCameraComponent;
class UAnimSequence;
class USoundBase;
class UColdSteelStatusModel;
struct FColdSteelItem;
struct FStreamableHandle;

/** Staff + blade presentation, sharing the existing thrust, uppercut and whirlwind controllers. */
UCLASS(ClassGroup=(Weapons))
class FPSGAME_API UStaffOffhandMeleeComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UStaffOffhandMeleeComponent();
    void InitializeLocalPresentation();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    static bool IsEquippedOn(const AActor* Owner);
    static bool PresentsLeftHand(const AActor* Owner);
    bool IsEquipped() const {return !Instance.IsEmpty();}
    bool IsEquipping() const {return IsEquipped()&&(!bReady||bDrawing||!bWasPresenting);}
    bool OwnsLeftHand() const;
    USkeletalMeshComponent* ArmsMesh() const;
    UStaticMeshComponent* WeaponMesh() const {return Blade;}
    void AdvanceBeforeCamera(float Delta);
    void GetCameraMotion(FRotator& Rotation,float& Fov) const;
    FVector StaffOffset() const;
    bool CanQuickCombat() const;
    bool CanQuickCombat(bool Uppercut) const;
    bool HasNativeChop() const {return HatchetChop!=nullptr;}
    FTransform SampleHatchetBlade(float Time);
    bool IsActionPresentationActive() const {return bActionPresentation||bWhirlwindPresentation||ActionReturnAge>=0.f;}
    bool CanWhirlwind() const;
    UAnimSequence* WhirlwindAnimation() const {return Whirlwind;}
    void BeginWhirlwindPresentation();
    void SetWhirlwindPose(float Time,float ClipTime,float Ready,float Spin,float Recover);
    void EndWhirlwindPresentation(bool Interrupted);
    bool ActionUsesChargePose() const {return bActionEntryCharge;}
    void CaptureActionEntry();
    void BeginActionPresentation(bool Uppercut=false,bool bUseHatchetChop=false);
    void BeginShadowStepPresentation(bool bStage2);
    void SetActionTime(float Time){ActionTime=Time;}
    void EndActionPresentation(bool Interrupted);
    FStaffCastPose ActionStaffPose(const FStaffCastPose& Carry) const;
    bool QuickStaffClearance(FVector& Offset,FQuat& Rotation) const;
    FTransform ActionBladeInCamera(float Time) const;
private:
    void SampleActionPose();
    void SampleWhirlwindPose();
    bool UsesStrikeRig() const;
    void RefreshEquipment();
    void ApplyAssets(const FString& Key,const FColdSteelItem& Item,const FSoftObjectPath& BladePath,bool NewInstance);
    void StartDraw();
    void SamplePose();
    void UpdateVisibility();
    UPROPERTY(Transient) TObjectPtr<UKukriArmsMeshComponent> Arms;
    UPROPERTY(Transient) TObjectPtr<UOffhandKukriArmsMeshComponent> StrikeArms;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Blade;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Idle;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> HatchetChop;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Equip;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Whirlwind;
    UPROPERTY(Transient) TObjectPtr<USoundBase> TossSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> CatchSound;
    TWeakObjectPtr<UCameraComponent> Camera;
    TWeakObjectPtr<UColdSteelStatusModel> Model;
    TSharedPtr<FStreamableHandle> Load;
    FDelegateHandle EquipmentChanged;
    FString Instance,Recipe;
    FTransform BladeFit=FTransform::Identity;
    float Age=0.f,PairWeight=0.f;
    bool bReady=false,bDrawing=false,bWasPresenting=false,bDrawHatchet=false;
    bool bActionPresentation=false,bReturnFromStrike=false,bActionEntryCharge=false;
    bool bUpperPresentation=false;
    bool bShadowStepPresentation=false,bShadowStepStage2Presentation=false;
    bool bHatchetChopPresentation=false;
    bool bWhirlwindPresentation=false;
    float WhirlwindTime=0.f,WhirlwindClipTime=0.f,WhirlwindReady=.5f,WhirlwindSpin=.8f,WhirlwindRecover=.52f;
    float ActionLength=0.f;
    float ActionTime=0.f,ActionReturnAge=-1.f,ReturnFromLower=0.f;
    FStaffCastPose ActionStaffEntry,ActionStaffRecovery;
    bool bQuickSupportReturn=false;
    FVector QuickSupportReturnOffset=FVector::ZeroVector;
    FQuat QuickSupportReturnRotation=FQuat::Identity;
};
