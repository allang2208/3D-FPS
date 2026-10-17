#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "IceArmorTypes.h"
#include "FPSLeftHandNotice.h"
#include "FPSIceArmorComponent.generated.h"
class UColdSteelStatusModel;
class UFPSFireballComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class USoundBase;
class USkeletalMesh;
class USkeletalMeshComponent;
class UNiagaraSystem;
class UNiagaraComponent;
class UInstancedStaticMeshComponent;
UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSIceArmorComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSIceArmorComponent();
    void Trigger();
    void Cancel();
    void FinishForRemoval();
    bool HasQueuedAction() const{return bQueued;}
    bool HasUnreleasedCast() const{return bCommitted;}
    float Remaining() const;
    float DefenseBonus(bool bMagic) const;
    FString StatusText() const;
    float CooldownFraction() const;
    bool IsHandOccupiedNotice() const;
    float HandNoticeAlpha() const;
    float HandNoticeRise() const;
    bool NetRelease(APawn* Caster,const struct FColdSteelNetCastRequest& Request,UColdSteelStatusModel* Model,const FIceArmorCast& Spell);
    void NetCastResult(uint8 Phase,uint8 Code,uint32 CastId);
    void ObserveAcceptedDamage(AActor* Source,const class UDamageType* Type,float Damage);
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Props) const override;
private:
    friend class USkillNetworkAuditCommandlet;
    UPROPERTY(ReplicatedUsing=OnRep_State) FIceArmorState State;
    UFUNCTION() void OnRep_State();
    UPROPERTY(ReplicatedUsing=OnRep_Impact) FIceArmorImpact Impact;
    UFUNCTION() void OnRep_Impact();
    FIceArmorState Prediction;
    FIceArmorCast Pending;
    uint32 LocalCastId=0,ConfirmedCastId=0,RejectedCastId=0,SoundSerial=0;
    bool bQueued=false,bCommitted=false,bAwaiting=false;
    float PendingRefund=0,PulseClock=0;
    double MessageUntil=0,VisualHitAt=-10,VisualStartedAt=0,VisualEndAt=0,EndingAt=-1,NextOutfitAt=0,NextDetailAt=0;
    uint32 LastImpactSerial=0;
    bool bVisualWasActive=false,bLastFirstPerson=false;
    float VisualPulseSeconds=2,VisualDetail=1;
    FVector VisualHitDirection=FVector::ForwardVector,VisualWind=FVector::ZeroVector;
    FRotator PreviousCameraRotation=FRotator::ZeroRotator,LensSway=FRotator::ZeroRotator;
    int32 OutfitProfiles[3]={0,0,0};
    bool bHideBack=false,bHideThigh=false;
    FString Message;
    FFPSLeftHandNotice HandNotice;
    TWeakObjectPtr<UColdSteelStatusModel> RewardModel;
    int32 Experience=0;
    TMap<TWeakObjectPtr<AActor>,double> TrainingSources;
    UPROPERTY(Transient) TArray<TObjectPtr<USkeletalMesh>> ShellMeshes;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> LensMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> ArmorMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> LensMaterial;
    UPROPERTY(Transient) TObjectPtr<USoundBase> CastSound;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> ChipMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> ChipMaterial;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> MistSystem;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ArmorMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> LensMID;
    UPROPERTY(Transient) TArray<TObjectPtr<USkeletalMeshComponent>> BodyShells;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Lens;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Chips;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> Mist;
    struct FChip { FVector Start=FVector::ZeroVector,Velocity=FVector::ZeroVector;FRotator Rotation=FRotator::ZeroRotator,Spin=FRotator::ZeroRotator;double At=-100;float Size=1; };
    TArray<FChip> ChipParticles;
    int32 ChipCursor=0;
    UColdSteelStatusModel* Model() const;
    UFPSFireballComponent* Hands() const;
    double Clock() const;
    const FIceArmorState& View() const;
    void ServiceQueue();
    void Release();
    void Start(const FIceArmorCast& Spell,uint32 CastId,UColdSteelStatusModel* OwnerModel);
    void End(bool bTrain);
    void Pulse();
    void RefreshStatus();
    void UpdateVisuals(float Delta=0.f);
    void ClearVisuals();
    void UpdateOutfit();
    void EmitChips(const FVector& Direction,int32 Count);
    void UpdateChips();
    void Feedback(const TCHAR* Text);
};
