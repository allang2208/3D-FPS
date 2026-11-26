#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "KukriRelentlessComponent.generated.h"

class UColdSteelStatusModel;
class USwordTasselMeshComponent;
class UPointLightComponent;
struct FColdSteelItem;
struct FColdSteelSkillShot;

USTRUCT()
struct FKukriRelentlessBlade
{
    GENERATED_BODY()
    UPROPERTY() FString Instance;
    UPROPERTY() int32 Stacks=0;
    UPROPERTY() double LastHit=0.;
};
USTRUCT()
struct FKukriRelentlessState
{
    GENERATED_BODY()
    UPROPERTY() TArray<FKukriRelentlessBlade> Blades;
    UPROPERTY() FString EquipmentKey;
    UPROPERTY() uint32 Revision=0;
};

/** Per-blade attack snapshots; cosmetic chain is simulated by SwordTasselMesh. */
UCLASS()
class FPSGAME_API UKukriRelentlessComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    static constexpr int32 MaximumStacks=10;
    static constexpr float DamagePerStack=.03f; static constexpr float ToughnessPerStack=.06f;
    UKukriRelentlessComponent();
    void Configure(const UColdSteelStatusModel* Model);
    void CaptureAttack(uint32 Serial,const UColdSteelStatusModel* Model);
    void PrepareServerAttack(int32 Family);
    void BindServerAttack(int32 Family,uint32 Serial);
    void ConfirmHit(const FColdSteelSkillShot& Shot,float Damage);
    bool GetBuff(bool bOffhand,int32& Count,float& Remaining,float& Duration) const;
    static FVector2D Multipliers(const FColdSteelSkillShot& Shot,const UColdSteelStatusModel* Model);
    static bool Installed(const FColdSteelItem& Item,const UColdSteelStatusModel* Model);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    struct FBladeSnapshot {FString Instance;int32 Stacks=0;double DamageWeight=0.,ToughnessWeight=0.;bool bPendant=false,bGranted=false;};
    struct FAttackSnapshot {uint32 Serial=0;FString EquipmentKey;TArray<FBladeSnapshot> Blades;};
    struct FVisual {TWeakObjectPtr<USwordTasselMeshComponent> Mesh;FString Instance;bool bWorld=false;};
    double Clock() const;
    int32 Stacks(const FString& Instance) const;
    FAttackSnapshot Freeze(const UColdSteelStatusModel* Model) const;
    void Store(FAttackSnapshot Attack);
    void ResolveVisuals();
    void Present();
    UFUNCTION() void OnRep_State();
    UPROPERTY(ReplicatedUsing=OnRep_State) FKukriRelentlessState State;
    UPROPERTY(Transient) TArray<TObjectPtr<UPointLightComponent>> Lights;
    TWeakObjectPtr<const UColdSteelStatusModel> Profile;
    TArray<FString> Equipped;
    FString EquipmentKey;
    uint32 RequiredRevision=0;
    bool bConfigured=false;
    TArray<FAttackSnapshot> Attacks;
    FAttackSnapshot Pending[5];
    TArray<FVisual> Visuals;
    float ResolveAge=0.f;
};
