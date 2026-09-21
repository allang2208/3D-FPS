#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "GameFramework/DamageType.h"
#include "CombatStatusFormula.generated.h"

UCLASS()
class FPSGAME_API UCombatDirectDamage : public UDamageType { GENERATED_BODY() };

/** Target-owned temporary reductions; seconds in UE, milliseconds in gamedev. */
UCLASS(ClassGroup=(Combat),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UCombatStatusFormula : public UActorComponent
{
    GENERATED_BODY()
public:
    UCombatStatusFormula();
    UFUNCTION(BlueprintCallable) static UCombatStatusFormula* GetOrAdd(AActor* Target);
    UFUNCTION(BlueprintCallable) void AddCorrosion(int32 Stacks=1,float Seconds=5,float ReductionPerStack=.05f);
    UFUNCTION(BlueprintCallable) void AddMagicResistanceShred(float Ratio,float Seconds);
    UFUNCTION(BlueprintCallable) void AddHolyWard(float Multiplier,float Seconds);
    UFUNCTION(BlueprintCallable) void AddMagicVulnerability(int32 Stacks=1);
    void AddRuneMagicVulnerability(float Ratio,float Seconds);
    UFUNCTION(BlueprintCallable) void AddBleeding(AActor* Source,int32 Stacks=1);
    UFUNCTION(BlueprintCallable) void AddBurn(AActor* Source,float MagicAttack,int32 Stacks=1,float Seconds=3,float DamageMultiplier=.5f,float TickSeconds=.5f);
    UFUNCTION(BlueprintCallable) void SetStatusImmune(bool Immune){bImmune=Immune;}
    bool IsImmune()const{return bImmune;}
    // Returns true once at the overload threshold. The spell owns the resulting chain.
    bool AddElectrified(int32 Stacks,float Seconds,int32 OverloadThreshold,float BonusPerStack);
    float ElectricMultiplier()const{return 1+ElectrifiedStacks*ElectrifiedBonus;}
    void AddChill(int32 Stacks,float Seconds,float SlowPerStack);
    void AddHaste(int32 Stacks,float Seconds);
    void AddChainSpell();
    void ConsumeChainSpell();
    int32 ChainSpellStacks()const{return ChainTime>0?ChainStacks:0;}
    float MovementMultiplier()const{return FrozenTime>0?0.f:FMath::Max(.01f,1-ChillStacks*ChillSlow)*(1+.1f*HasteStacks);}
    float FrozenRemaining()const{return FrozenTime;}
    float CorrosionMultiplier()const{return FMath::Max(0.f,1-CorrosionStacks*CorrosionReduction);}
    float MagicShred()const{return ShredTime>0?Shred:0;}
    float FinalMultiplier()const{return WardTime>0?Ward:1;}
    float MagicVulnerabilityMultiplier()const{return (1+VulnerabilityStacks*.05f)*(1+(RuneVulnerabilityTime>0?RuneVulnerability:0));}
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Fn)override;
private:
    bool bImmune=false;
    int32 ElectrifiedStacks=0;
    float ElectrifiedTime=0,ElectrifiedBonus=.03f;
    int32 ChillStacks=0,HasteStacks=0,ChainStacks=0;
    float ChillTime=0,ChillSlow=.05f,FrozenTime=0,HasteTime=0,ChainTime=0;
    int32 CorrosionStacks=0;
    float CorrosionTime=0,CorrosionDuration=5,CorrosionReduction=.05f;
    float ShredTime=0,Shred=0,WardTime=0,Ward=1;
    int32 VulnerabilityStacks=0,BleedStacks=0;
    float VulnerabilityTime=0,BleedTime=0,BleedTick=0,BurnTick=0,BurnInterval=.5f;
    float RuneVulnerability=0,RuneVulnerabilityTime=0;
    TWeakObjectPtr<AActor> BleedSource;
    struct FBurn {TWeakObjectPtr<AActor> Source;float Damage=0,Remaining=0;};
    TArray<FBurn> Burns;
};
