#include "CombatFormulaRuntime.h"
#include "CoreCombatFormula.h"
#include "CombatStatusFormula.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/HandBrainMonster.h"
#include "../Monsters/PoisonMaggotMonster.h"
#include "../Monsters/WolfMonster.h"
#include "../Skills/FireballDamage.h"
#include "../Skills/IceSpikeDamage.h"
#include "../Skills/CorrosivePusDamage.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"

namespace
{
CoreCombatFormula::Attributes MonsterAttributes(const AActor* Target)
{
    if(Target->IsA<AHandBrainMonster>())return {50,25,30,40,20,10};
    if(Target->IsA<APoisonMaggotMonster>())return {7,13,24,22,24,13};
    if(Target->ActorHasTag(TEXT("FatZombie")))return {18,6,3,20,3,5};
    // Nurse is a UE-specific creature with no World-122 config identity.
    return {0,0,0,0,0,0};
}
}
thread_local const CombatFormulaRuntime::MagicHit* CombatFormulaRuntime::ActiveMagicHit=nullptr;
thread_local const double* CombatFormulaRuntime::ActivePhysicalPenetration=nullptr;
bool CombatFormulaRuntime::IsMagic(const UDamageType* Type)
{return Type&&(Type->IsA<UHandBrainMagicDamage>()||Type->IsA<UFireballDamage>()||Type->IsA<UIceSpikeDamage>()||Type->IsA<UCorrosivePusDamage>());}
float CombatFormulaRuntime::MonsterDefense(const AActor* Target,bool Magic)
{
    if(const auto* W=Cast<AWolfMonster>(Target))return Magic?W->MagicDefense:W->PhysicalDefense;
    if(Magic)if(const auto* H=Cast<AHandBrainMonster>(Target))return H->MagicDefense; // Original permitted direct override: 65.
    const auto S=CoreCombatFormula::Enemy(MonsterAttributes(Target));return Magic?S.Mdef:S.Def;
}
float CombatFormulaRuntime::MonsterCriticalResistance(const AActor* Target)
{if(const auto* W=Cast<AWolfMonster>(Target))return W->CriticalResistance;return CoreCombatFormula::Enemy(MonsterAttributes(Target)).CritRes;}
float CombatFormulaRuntime::MitigateMonster(AActor* Target,float Damage,const UDamageType* Type,AActor* Source)
{
    if(Type&&Type->IsA<UCombatDirectDamage>())return Damage;
    const bool Magic=IsMagic(Type);double Penetration=0;
    const auto* Player=Cast<APawn>(Source);
    if(Player&&Player->IsPlayerControlled()&&Source->GetGameInstance())if(auto* P=Source->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        if(const auto* I=P->Equipped())if(auto* E=Source->GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
            Penetration=E->Effect(*I,Magic?TEXT("magicPenetrationPercent"):TEXT("armorPenetrationPercent"))+E->CraftEffect(*I,Magic?TEXT("magicPenetrationPercent"):TEXT("armorPenetrationPercent"));
    if(Magic&&ActiveMagicHit)Penetration=ActiveMagicHit->Penetration;
    if(!Magic&&ActivePhysicalPenetration)Penetration=*ActivePhysicalPenetration;
    const auto* Status=Target->FindComponentByClass<UCombatStatusFormula>();
    double Result=CoreCombatFormula::Defense(Damage,MonsterDefense(Target,Magic),Magic,Penetration,Status?Status->MagicShred():0,Status?Status->CorrosionMultiplier():1);
    if(Magic&&ActiveMagicHit)Result=std::floor(Result*(1+ActiveMagicHit->DamageBonus));
    else if(Magic&&Player&&Player->IsPlayerControlled()&&Source->GetGameInstance())if(const auto* P=Source->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Result=std::floor(Result*(1+P->SetEffect(TEXT("magicDamage"))));
    if(Magic&&Status)Result=std::floor(Result*Status->MagicVulnerabilityMultiplier());
    if(!Magic&&Status&&Status->FrozenRemaining()>0)Result=std::floor(Result*1.5);
    if(Target->GetGameInstance())if(const auto* P=Target->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Result=std::floor(Result*P->TributeEffect(TEXT("monsterDamageTakenPercent")));
    if(Magic&&ActiveMagicHit)
    {
        const bool Critical=ActiveMagicHit->bWeakpoint||FMath::FRand()*100<CoreCombatFormula::CriticalChance(ActiveMagicHit->Chance,MonsterCriticalResistance(Target));
        if(ActiveMagicHit->CriticalResult)*ActiveMagicHit->CriticalResult=Critical;
        if(Critical)Result=CoreCombatFormula::CriticalDamage(Result,ActiveMagicHit->Bonus);
    }
    return Status?std::floor(Result*Status->FinalMultiplier()):Result;
}
