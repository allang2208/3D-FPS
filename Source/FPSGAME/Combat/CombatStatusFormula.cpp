#include "CombatStatusFormula.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Pawn.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/HandBrainMonster.h"
#include "../Monsters/PoisonMaggotMonster.h"
#include "../Monsters/WolfMonster.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Skills/FireballDamage.h"
#include "../UI/StatusEffectsComponent.h"
UCombatStatusFormula::UCombatStatusFormula(){PrimaryComponentTick.bCanEverTick=true;}
UCombatStatusFormula* UCombatStatusFormula::GetOrAdd(AActor* Target)
{
    if(!IsValid(Target))return nullptr;
    auto* C=Target->FindComponentByClass<UCombatStatusFormula>();
    if(!C){C=NewObject<UCombatStatusFormula>(Target);Target->AddInstanceComponent(C);C->RegisterComponent();}return C;
}
void UCombatStatusFormula::AddCorrosion(int32 Stacks,float Seconds,float Reduction)
{
    if(bImmune||Stacks<=0)return;
    CorrosionStacks+=Stacks;CorrosionDuration=FMath::Max(.001f,Seconds);CorrosionTime=CorrosionDuration;
    CorrosionReduction=FMath::Max(CorrosionReduction,Reduction);
}
void UCombatStatusFormula::AddMagicResistanceShred(float Ratio,float Seconds)
{
    if(bImmune||Seconds<=0||Ratio<=0)return;
    Shred=FMath::Max(ShredTime>0?Shred:0,FMath::Clamp(Ratio,0.f,.95f));ShredTime=FMath::Max(ShredTime,Seconds);
}
void UCombatStatusFormula::AddHolyWard(float Multiplier,float Seconds)
{if(Seconds>0){Ward=FMath::Min(WardTime>0?Ward:1,FMath::Clamp(Multiplier,.05f,1.f));WardTime=FMath::Max(WardTime,Seconds);}}
void UCombatStatusFormula::AddMagicVulnerability(int32 Stacks)
{if(!bImmune&&Stacks>0){VulnerabilityStacks+=Stacks;VulnerabilityTime=5;}}
void UCombatStatusFormula::AddBleeding(AActor* Source,int32 Stacks)
{if(!bImmune&&Stacks>0){BleedStacks+=Stacks;BleedTime=10;if(BleedTick<=0)BleedTick=1;BleedSource=Source;}}
void UCombatStatusFormula::AddBurn(AActor* Source,float Matk,int32 Stacks,float Seconds,float Multiplier,float TickSeconds)
{
    if(bImmune||Stacks<=0||Seconds<=0||TickSeconds<=0)return;
    for(int32 I=0;I<Stacks;++I)Burns.Add({Source,FMath::Max(1.f,FMath::FloorToFloat(Matk*Multiplier)),Seconds});
    BurnInterval=TickSeconds;if(BurnTick<=0)BurnTick=BurnInterval;
}
void UCombatStatusFormula::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Fn)
{
    Super::TickComponent(Delta,Type,Fn);ShredTime=FMath::Max(0.f,ShredTime-Delta);WardTime=FMath::Max(0.f,WardTime-Delta);
    auto Expire=[&](float& Time,int32& Stacks,FName Name){if(Time<=0)return;Time=FMath::Max(0.f,Time-Delta);if(Time==0){Stacks=0;UStatusEffectsComponent::GetOrCreate(GetOwner())->Remove(Name);}};
    Expire(ChillTime,ChillStacks,TEXT("chill"));Expire(HasteTime,HasteStacks,TEXT("haste"));Expire(ChainTime,ChainStacks,TEXT("chainSpell"));
    FrozenTime=FMath::Max(0.f,FrozenTime-Delta);
    if(CorrosionStacks>0){CorrosionTime-=Delta;while(CorrosionTime<=0&&CorrosionStacks>0){--CorrosionStacks;CorrosionTime+=CorrosionDuration;}}
    if(VulnerabilityStacks>0){VulnerabilityTime-=Delta;while(VulnerabilityTime<=0&&VulnerabilityStacks>0){--VulnerabilityStacks;VulnerabilityTime+=5;}}
    auto Apply=[&](float Damage,AActor* Source,bool bMagicDamage){const auto* Pawn=Cast<APawn>(Source);UGameplayStatics::ApplyDamage(GetOwner(),Damage,Pawn?Pawn->GetController():nullptr,Source,bMagicDamage?UFireballDamage::StaticClass():UCombatDirectDamage::StaticClass());};
    if(BleedStacks>0)
    {
        BleedTime-=Delta;BleedTick-=Delta;
        while(BleedTick<=0)
        {
            float Health=0;if(const auto* N=Cast<ANurseZombie>(GetOwner()))Health=N->Health;
            else if(const auto* H=Cast<AHandBrainMonster>(GetOwner()))Health=H->Health;
            else if(const auto* M=Cast<APoisonMaggotMonster>(GetOwner()))Health=M->Health;
            else if(const auto* W=Cast<AWolfMonster>(GetOwner()))Health=W->Health;
            else if(const auto* C=GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>())Health=C->Health;
            if(Health>0)Apply(FMath::Max(1.f,FMath::FloorToFloat(Health*.01f*BleedStacks)),BleedSource.Get(),false);BleedTick+=1;
        }
        while(BleedTime<=0&&BleedStacks>0){--BleedStacks;BleedTime+=10;}
    }
    if(!Burns.IsEmpty())
    {
        BurnTick-=Delta;for(auto& B:Burns)B.Remaining-=Delta;Burns.RemoveAll([](const auto& B){return B.Remaining<=0;});
        if(Burns.IsEmpty())BurnTick=0;
        else while(BurnTick<=0){float Damage=0;AActor* Source=nullptr;for(const auto& B:Burns){Damage+=B.Damage;if(!Source)Source=B.Source.Get();}Apply(Damage,Source,true);BurnTick+=BurnInterval;}
    }
}

void UCombatStatusFormula::AddChill(int32 Stacks,float Seconds,float SlowPerStack)
{
    if(bImmune||FrozenTime>0||Stacks<=0||Seconds<=0)return;
    if(ChillStacks==0)ChillSlow=SlowPerStack;
    ChillStacks+=Stacks;ChillTime+=Seconds;
    if(ChillStacks>=20)
    {
        ChillStacks-=10;FrozenTime=Seconds;
        if(auto* W=Cast<AWolfMonster>(GetOwner()))W->InterruptAttack(Seconds);
        if(auto* M=Cast<APoisonMaggotMonster>(GetOwner()))M->InterruptAttack(Seconds);
        if(auto* N=Cast<ANurseZombie>(GetOwner()))N->InterruptAttack(Seconds);
        if(auto* H=Cast<AHandBrainMonster>(GetOwner()))H->InterruptAttack(Seconds);
        UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("frozen"),Seconds,1);
    }
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("chill"),ChillTime,ChillStacks);
}
void UCombatStatusFormula::AddHaste(int32 Stacks,float Seconds)
{
    if(bImmune||Stacks<=0||Seconds<=0)return;HasteStacks+=Stacks;HasteTime+=Stacks*Seconds;
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("haste"),HasteTime,HasteStacks);
}
void UCombatStatusFormula::AddChainSpell()
{
    if(bImmune)return;++ChainStacks;ChainTime+=10;
    UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(TEXT("chainSpell"),ChainTime,ChainStacks);
}
void UCombatStatusFormula::ConsumeChainSpell()
{ChainTime=0;ChainStacks=0;UStatusEffectsComponent::GetOrCreate(GetOwner())->Remove(TEXT("chainSpell"));}
