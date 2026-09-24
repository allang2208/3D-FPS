#include "CombatFormulaRuntime.h"
#include "CoreCombatFormula.h"
#include "CombatStatusFormula.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/HandBrainMonster.h"
#include "../Monsters/PoisonMaggotMonster.h"
#include "../Monsters/WolfMonster.h"
#include "../Monsters/MonsterCoreStats.h"
#include "../Skills/FireballDamage.h"
#include "../Skills/IceSpikeDamage.h"
#include "../Skills/LightningDamage.h"
#include "../Skills/HolyLightDamage.h"
#include "../Skills/FireMagicDamage.h"
#include "../Skills/CorrosivePusDamage.h"
#include "../Weapons/RuneOrbBladeDamage.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"

namespace
{
CoreCombatFormula::Attributes MonsterAttributes(const AActor* Target)
{
    // 2026-09-23：六维统一走 MonsterCoreStats 注册表（含狼/护士反解项与巫婆/突变体3）。
    FMonsterCoreStats S;
    return MonsterCoreStats::Get(Target,S)?S.A:CoreCombatFormula::Attributes{0,0,0,0,0,0};
}
}
thread_local const CombatFormulaRuntime::MagicHit* CombatFormulaRuntime::ActiveMagicHit=nullptr;
thread_local CombatFormulaRuntime::WeaponHit* CombatFormulaRuntime::ActiveWeaponHit=nullptr;
thread_local const double* CombatFormulaRuntime::ActivePhysicalPenetration=nullptr;
bool CombatFormulaRuntime::IsMagic(const UDamageType* Type)
{return Type&&(Type->IsA<UHandBrainMagicDamage>()||Type->IsA<UFireballDamage>()||Type->IsA<UIceSpikeDamage>()||Type->IsA<ULightningDamage>()||Type->IsA<UHolyLightDamage>()||Type->IsA<UFireMagicDamage>()||Type->IsA<UCorrosivePusDamage>()||Type->IsA<URuneOrbBladeDamage>()||Type->IsA<UStatusMagicDamage>());}
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
    if(ActiveWeaponHit&&ActiveWeaponHit->Target==Target&&!ActiveWeaponHit->bResolved&&!IsMagic(Type))
    {
        auto& Hit=*ActiveWeaponHit;
        const auto* Status=Target->FindComponentByClass<UCombatStatusFormula>();
        const auto* SourceStatus=Source?Source->FindComponentByClass<UCombatStatusFormula>():nullptr;
        double Common=1;
        if(Target->GetGameInstance())if(const auto* P=Target->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            Common*=P->TributeEffect(TEXT("monsterDamageTakenPercent"));
        auto Resolve=[&](double Amount,bool Magic)
        {
            double Final=CoreCombatFormula::Defense(Amount,MonsterDefense(Target,Magic),Magic,
                Magic?Hit.MagicPenetration:Hit.PhysicalPenetration,Status?Status->MagicShred():0,Status?Status->CorrosionMultiplier():1);
            Final=std::floor(Magic?Final*(Status?Status->MagicVulnerabilityMultiplier():1.):Final*((Status&&Status->FrozenRemaining()>0)?1.5:1.));
            // 旧链顺序：魔法易伤→石化→无人机易伤→献祭承伤→冻结→来源减伤→标记→圣佑（逐段取整）。
            if(Magic&&Status)Final=std::floor(Final*Status->PetrifiedMagicMultiplier());
            if(Status)Final=std::floor(Final*Status->DroneDamageMultiplier(Source));
            if(SourceStatus)Final=std::floor(Final*SourceStatus->OutgoingDamageMultiplier());
            if(Status)Final=std::floor(Final*Status->MarkedMultiplier());
            return FMath::Max(0.,std::floor(Final*Common*(Status?Status->FinalMultiplier():1)));
        };
        const auto& In=Hit.Incoming;
        Hit.Mitigated={Resolve(In.BasePhysical,false),Resolve(In.BaseMagic,true),Resolve(In.AddedPhysical,false),Resolve(In.AddedMagic,true)};
        Hit.bResolved=true;
        return Hit.Mitigated.Total();
    }
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
    if(Magic&&Status)Result=std::floor(Result*Status->PetrifiedMagicMultiplier());
    if(Type&&Type->IsA<ULightningDamage>()&&Status)Result=std::floor(Result*Status->ElectricMultiplier());
    if(Status)Result=std::floor(Result*Status->DroneDamageMultiplier(Source));
    if(Target->GetGameInstance())if(const auto* P=Target->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Result=std::floor(Result*P->TributeEffect(TEXT("monsterDamageTakenPercent")));
    if(!Magic&&Status&&Status->FrozenRemaining()>0)Result=std::floor(Result*1.5);
    if(Magic&&ActiveMagicHit)
    {
        const double CritChance=ActiveMagicHit->Chance+(Status?Status->DroneCritBonusPercent(Source):0);
        const bool Critical=ActiveMagicHit->bWeakpoint||FMath::FRand()*100<CoreCombatFormula::CriticalChance(CritChance,MonsterCriticalResistance(Target));
        if(ActiveMagicHit->CriticalResult)*ActiveMagicHit->CriticalResult=Critical;
        if(Critical)Result=CoreCombatFormula::CriticalDamage(Result,ActiveMagicHit->Bonus);
    }
    // 旧链尾段：来源侧减益（骆驼惊吓等）→ 标记 → 圣佑，逐段取整。
    if(const auto* SourceStatus=Source?Source->FindComponentByClass<UCombatStatusFormula>():nullptr)Result=std::floor(Result*SourceStatus->OutgoingDamageMultiplier());
    if(Status)Result=std::floor(Result*Status->MarkedMultiplier());
    return Status?std::floor(Result*Status->FinalMultiplier()):Result;
}
