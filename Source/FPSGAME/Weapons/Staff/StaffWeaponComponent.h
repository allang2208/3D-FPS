#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../../Skills/ColdSteelSkillTypes.h"
#include "StaffLocomotion.h"
#include "StaffCastMotion.h"
#include "StaffWeaponComponent.generated.h"
class UColdSteelStatusModel;
class UStaticMeshComponent;
class USkeletalMeshComponent;
class UStaffArmsMeshComponent;
class UCameraComponent;
class UFPSFootstepAudioComponent;
class USoundBase;
class UPointLightComponent;
class UMaterialInstanceDynamic;
struct FColdSteelItem;
struct FStreamableHandle;
struct FHitResult;

/** One-handed staff: one action clock, immutable physical swing, six-slot assembly. */
UCLASS(ClassGroup=(Weapons),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UStaffWeaponComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UStaffWeaponComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    void RefreshEquipment(UColdSteelStatusModel* Profile);
    bool IsEquipped()const{return !Instance.IsEmpty();}
    bool IsBusy()const{return Age>=0||EquipAge<.35f||IsQuickCombatActive();}
    bool IsEquipping()const{return IsEquipped()&&EquipAge<.35f;}
    bool IsQuickCombatActive()const;
    bool BeginQuickCombat();
    bool GetQuickCombatStrikeProbe(FVector& Origin,float ContactTime);
    bool IsPrimaryAttacking()const{return Age>=0.f;}
    bool CanBeginCast()const;
    void BeginPrimaryAttack();
    void ToggleIllumination();
    bool HasIlluminationSpecial()const{return IsEquipped()&&bCanIlluminate;}
    bool IsIlluminationOn()const{return HasIlluminationSpecial()&&bIlluminationOn;}
    void CancelAction();
    FTransform GripInCamera()const;
    FStaffCastPose CarryPoseInCamera()const;
    FStaffCastPose CastingPoseInCamera()const;
    FStaffCastPose ActionPoseInCamera()const;
    void AdvanceActionBeforeCamera(float Delta);
    void GetCameraMotion(FVector& Location,FRotator& Rotation)const;
    const FStaffLocomotion& CarryPose()const{return Locomotion;}
    UStaticMeshComponent* AssemblyRoot()const{return Staff;}
    USkeletalMeshComponent* ArmsMesh()const;
    int32 GripVariant()const{return AuthoredGripVariant;}
private:
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Staff;
    UPROPERTY(Transient) TObjectPtr<UStaffArmsMeshComponent> Arms;
    UPROPERTY(Transient) TObjectPtr<UCameraComponent> Camera;
    TSharedPtr<FStreamableHandle> Load;
    TWeakObjectPtr<UFPSFootstepAudioComponent> Footsteps;
    FStaffLocomotion Locomotion;
    FString Instance,Recipe;
    int32 AuthoredGripVariant=0;
    float Age=-1,EquipAge=0,Damage=0,Duration=.5f;
    bool bBlocked=false;
    FColdSteelSkillShot Shot;
    TSet<TWeakObjectPtr<AActor>> HitActors;
    FTransform Previous=FTransform::Identity;
    void TraceSwing(const FTransform& From,const FTransform& To);
    void ConfirmImpact(const FHitResult& Hit,bool bWorld);
    FTransform AttackRootInCamera(bool bFeedback)const;
    FStaffCastPose SamplePrimaryPose()const;
    FStaffCastPose AttackEntry,BlockedPose;
    float BlockedAge=0,HitStopRemaining=0,ImpactAge=-1,ImpactStrength=0;
    bool bSwingSoundPlayed=false,bAirImpulse=false,bImpactConfirmed=false;
    UPROPERTY(Transient) TObjectPtr<USoundBase> SwingSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ImpactSound;
    // Local held-weapon light; neither a learned spell nor a resource transaction.
    void ConfigureIllumination(const FColdSteelItem& Resolved);
    void UpdateIllumination(float Delta);
    void ResetIllumination();
    bool bCanIlluminate=false,bIlluminationOn=false;
    float IlluminationBlend=0.f,PublishedIllumination=-1.f;
    UPROPERTY(Transient) TObjectPtr<UPointLightComponent> CrystalLight;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> CrystalLightMaterials;
    FStaffCastPose IlluminationGestureEntry;
    float IlluminationGestureAge=-1.f;
    FStaffCastPose SampleIlluminationGesture(const FStaffCastPose& Carry)const;
    void PublishIllumination();
};
