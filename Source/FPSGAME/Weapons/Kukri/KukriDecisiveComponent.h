#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "KukriDecisiveComponent.generated.h"

class UColdSteelStatusModel;
class USwordTasselMeshComponent;
class UPointLightComponent;
struct FColdSteelItem;
struct FColdSteelSkillShot;
USTRUCT()
struct FKukriDecisiveBlade
{
    GENERATED_BODY()
    UPROPERTY() FString Instance;
    UPROPERTY() double ReadyAt=0.;
    UPROPERTY() double ReleaseAt=-100.;
};
USTRUCT()
struct FKukriDecisiveState
{
    GENERATED_BODY()
    UPROPERTY() TArray<FKukriDecisiveBlade> Blades;
    UPROPERTY() FString EquipmentKey;
    UPROPERTY() uint32 Revision=0;
};
/** One held-blade preparation, consumed on accepted release even on a miss. */
UCLASS()
class FPSGAME_API UKukriDecisiveComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UKukriDecisiveComponent();
    void Configure(const UColdSteelStatusModel* Model);
    void BeginLocal(const FColdSteelSkillShot& Shot,bool Martial,const FString& Second=FString());
    void BeginServer(int32 Family,const FString& First,const FString& Second,bool Martial,float Duration);
    void EndServer(int32 Family);
    void BindServerAttack(int32 Family,uint32 Serial);
    /** Read the authoritative preparation clock; false during a swing or without this pendant. */
    bool PreparationForHand(bool bOffhand,float& Progress) const;
    static FVector2D Multipliers(const FColdSteelSkillShot& Shot,const UColdSteelStatusModel* Model);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
protected:
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    friend struct FKukriDecisiveGlowCheck;
    struct FBlade {FString Instance;double DamageWeight=0.,ToughnessWeight=0.;bool bReady=false,bParticipating=false;};
    struct FAttack {uint32 Serial=0;FString Key;TArray<FBlade> Blades;bool bMartial=false,bEnded=false;};
    struct FVisual {TWeakObjectPtr<USwordTasselMeshComponent> Mesh;FString Instance;bool bWorld=false;};
    FAttack Start(const FString& First,const FString& Second,bool Martial,double EndAt);
    void Store(FAttack Attack);
    double Clock() const;
    bool Matches(const FString& Instance) const;
    float Charge(const FString& Instance) const;
    void ResolveVisuals();
    void Present();
    UFUNCTION() void OnRep_State();
    UPROPERTY(ReplicatedUsing=OnRep_State) FKukriDecisiveState State;
    UPROPERTY(Transient) TArray<TObjectPtr<UPointLightComponent>> Lights;
    TWeakObjectPtr<const UColdSteelStatusModel> Profile;
    FString EquipmentKey;
    FString MainHandInstance;
    TArray<FString> Equipped;
    TSet<FString> LocalActive;
    bool bConfigured=false;
    uint32 RequiredRevision=0;
    TArray<FAttack> Attacks;
    FAttack Pending[5];
    TArray<FVisual> Visuals;
    float ResolveAge=0.f;
};
