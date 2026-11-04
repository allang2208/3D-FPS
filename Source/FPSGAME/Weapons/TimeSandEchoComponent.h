#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "../Combat/WeaponDamageTypes.h"
#include "TimeSandEchoComponent.generated.h"

class UColdSteelStatusModel;
struct FColdSteelSkillShot;

USTRUCT()
struct FTimeSandEchoMark
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AActor> Target;
    UPROPERTY() FVector LocalPoint=FVector::ZeroVector;
    UPROPERTY() FVector LocalNormal=FVector::ForwardVector;
    UPROPERTY() float StartedAt=0.f;
    UPROPERTY() float TriggerAt=0.f;
    // Authority-only receipt; reflected fields above carry presentation only.
    FWeaponDamageParts Damage;
    TWeakObjectPtr<UColdSteelStatusModel> Profile;
    FString Group;
    float CooldownReward=0.f;
    bool bSettled=false,bCritical=false;
};

UCLASS(ClassGroup=(Weapons))
class FPSGAME_API UTimeSandEchoComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UTimeSandEchoComponent();
    void Configure(const UColdSteelStatusModel* Profile);
    void Queue(UColdSteelStatusModel* Profile,const FHitResult& Hit,const FColdSteelSkillShot& Shot,const FWeaponDamageParts& Damage,bool Critical);
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
private:
    UPROPERTY(ReplicatedUsing=OnRep_Marks) TArray<FTimeSandEchoMark> Marks;
    UPROPERTY(Transient) TObjectPtr<class UInstancedStaticMeshComponent> Visual;
    UPROPERTY(Transient) TObjectPtr<class UStaticMesh> Plane;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInterface> Material;
    TSharedPtr<struct FStreamableHandle> LoadHandle;
    TArray<FString> RewardedGroups;
    float Clock() const;
    void LoadVisual();
    void Settle(FTimeSandEchoMark& Mark);
    void Present();
    UFUNCTION() void OnRep_Marks();
    UFUNCTION(Client,Reliable) void ClientEchoDamage(AActor* Target,float Damage,bool Critical,bool Killed);
};
