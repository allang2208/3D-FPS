#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelSkillRules.h"
#include "FireMagicDamage.h"
#include "HolyLightTargets.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"

const FColdSteelSkillDefinition& UColdSteelStatusModel::FireMagicDefinition(FName Id) const
{return Id==TEXT("flameArmor")?FlameArmorSkill:MeteorSkill;}
FColdSteelSkillProgress UColdSteelStatusModel::FireMagicProgress(FName Id) const
{const auto* P=Current.Skills.Find(Id);return P?*P:FColdSteelSkillProgress();}
float UColdSteelStatusModel::FireMagicCooldown(FName Id) const
{return HasNoAbilityCooldown()?0.f:(Id==TEXT("flameArmor")?Current.FlameArmorCooldown:Current.MeteorCooldown);}
float UColdSteelStatusModel::FireMagicCooldownDuration(FName Id) const
{return Id==TEXT("flameArmor")?Current.FlameArmorCooldownDuration:Current.MeteorCooldownDuration;}

FFireMagicCast UColdSteelStatusModel::FireMagicStats(FName Id,int32 AtLevel) const
{
    const auto& D=FireMagicDefinition(Id);const auto& T=D.FireMagic;
    const int32 L=FMath::Clamp(AtLevel<0?FireMagicProgress(Id).Level:AtLevel,1,D.MaxLevel);
    const float Growth=float(L-1)/FMath::Max(1,D.MaxLevel-1);
    FFireMagicCast C;C.Skill=Id;C.MagicAttack=Derived(TEXT("matk"));
    const float Intelligence=Attribute(TEXT("int"));
    C.Damage=FMath::FloorToFloat(T.DamageBase+L*T.DamagePerLevel+C.MagicAttack*(T.MagicBase+L*T.MagicPerLevel)+Intelligence*(T.IntelligenceBase+L*T.IntelligencePerLevel));
    C.AuraDamage=FMath::FloorToFloat(T.AuraDamageBase+L*T.AuraDamagePerLevel+C.MagicAttack*(T.AuraMagicBase+L*T.AuraMagicPerLevel)+Intelligence*(T.AuraIntelligenceBase+L*T.AuraIntelligencePerLevel));
    C.Radius=(T.RadiusBase+L*T.RadiusPerLevel)*T.UnitsToCM;
    C.AuraRadius=(T.AuraRadiusBase+L*T.AuraRadiusPerLevel)*T.UnitsToCM;
    C.ManaCost=T.ManaBase+FMath::FloorToFloat(Growth*T.ManaGrowth);
    C.Cooldown=T.Cooldown-FMath::FloorToFloat(Growth*T.CooldownReduction);
    C.Duration=T.DurationBase+FMath::FloorToFloat(Growth*T.DurationGrowth);
    C.Range=T.Range*T.UnitsToCM;C.FallSeconds=T.FallSeconds;C.TickSeconds=T.TickSeconds;
    C.StunSeconds=T.StunSeconds;C.BurnStacks=T.BurnStacks;C.BurnSeconds=T.BurnSeconds;C.BurnMultiplier=T.BurnMultiplier;
    C.AuraBurnStacks=T.AuraBurnStacks;C.AuraBurnSeconds=T.AuraBurnSeconds;C.AuraBurnMultiplier=T.AuraBurnMultiplier;C.bRequiresStaff=T.bRequiresStaff;
    C.CriticalChance=Derived(TEXT("crit"));C.CriticalDamageBonus=CriticalStrikeEffect().CriticalDamageBonus;
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    C.MagicDamageBonus=(1+SetEffect(TEXT("magicDamage")))*Rune.MagicDamage-1;
    float DamageFactor=1,CostFactor=1,CooldownReduction=0;
    const auto* Player=UGameplayStatics::GetPlayerPawn(this,0);
    const auto* Status=Player?Player->FindComponentByClass<UCombatStatusFormula>():nullptr;
    const int32 Chain=Status?Status->ChainSpellStacks():0;
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* Key){return E->CraftEffect(*Item,Key);};
            C.CriticalChance+=100*(E->Effect(*Item,TEXT("critRate"))+Craft(TEXT("critChancePercent"))+Craft(TEXT("magicCritPercent")));
            C.MagicPenetration=E->Effect(*Item,TEXT("magicPenetrationPercent"))+Craft(TEXT("magicPenetrationPercent"));
            CostFactor+=Craft(TEXT("magicMpCostPercent"))+Chain*Craft(TEXT("chainSpellMpCostPercent"));
            CooldownReduction=Craft(TEXT("magicCooldownPercent"));C.Range*=1+Craft(TEXT("magicRangePercent"));
            C.CastSpeed=FMath::Max(.1f,float(1+Craft(TEXT("castSpeedPercent"))));
            DamageFactor=(1+Craft(TEXT("magicDamagePercent")))*(1+Chain*Craft(TEXT("chainSpellDamagePercent")));
            C.bGrantChain=Craft(TEXT("chainSpellDamagePercent"))!=0;
            C.CastHasteStacks=Craft(TEXT("castHasteStacks"));C.CastHasteDuration=E->CraftEffect(*Item,TEXT("castHasteDuration"),5000)/1000;
        }
    DamageFactor*=MagicImplementMultiplier();C.Damage=FMath::FloorToFloat(C.Damage*DamageFactor);C.AuraDamage=FMath::FloorToFloat(C.AuraDamage*DamageFactor);
    C.ManaCost=FMath::Max(0.f,FMath::FloorToFloat(C.ManaCost*CostFactor)*float(Rune.MagicCost));
    C.Cooldown*=FMath::Max(.2,double(1-CooldownReduction)*(1-SetEffect(TEXT("cooldown"))));C.Cooldown*=Rune.MagicCooldown;
    return C;
}

bool UColdSteelStatusModel::BeginFireMagicCast(const FFireMagicCast& Spell)
{
    if(!FireMagic::IsSkill(Spell.Skill)||FireMagicCooldown(Spell.Skill)>0||!CanSpendMana(Spell.ManaCost))return false;
    SyncRuntime();auto P=Snapshot();if(!HasInfiniteMana())P.Mana-=Spell.ManaCost;
    float& Remaining=Spell.Skill==TEXT("meteor")?P.MeteorCooldown:P.FlameArmorCooldown;
    float& Duration=Spell.Skill==TEXT("meteor")?P.MeteorCooldownDuration:P.FlameArmorCooldownDuration;
    Duration=Remaining=HasNoAbilityCooldown()?0.f:Spell.Cooldown;return CommitState(P);
}

bool UColdSteelStatusModel::ApplyFireMagicHit(APawn* Shooter,AActor* Target,const FFireMagicCast& Spell,float Damage,FFireMagicRewards& Batch)
{
    auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Shooter||!Shooter->IsPlayerControlled()||!Shooter->HasAuthority()||Target==Shooter||!Combat||Combat->IsDead()||HolyLightTargets::IsFriendly(Target))return false;
    // Weapon-triggered bonus hits must not claim a weapon mastery kill, recurse
    // through the weapon hook, or defer character XP for the entire buff duration.
    TGuardValue<FTrainingHit*> TrainingScope(ActiveTrainingHit,nullptr);
    TGuardValue<FFireballRewards*> RewardScope(ActiveFireballRewards,nullptr);
    bool Critical=false;
    const CombatFormulaRuntime::MagicHit Context{Spell.CriticalChance,Spell.CriticalDamageBonus,Spell.MagicPenetration,Spell.MagicDamageBonus,&Critical,false};
    TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(CombatFormulaRuntime::ActiveMagicHit,&Context);
    const float Applied=UGameplayStatics::ApplyDamage(Target,Damage,Shooter->GetController(),Shooter,UFireMagicDamage::StaticClass());
    if(Applied<=0)return false;
    if(auto* Player=Cast<AFPSGAMECharacter>(Shooter))Player->NotifyConfirmedWeaponHit(Target,Applied);
    if(!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining")))
    {
        ++Batch.Hits;if(Combat->IsDead())++Batch.Kills;
        if(Critical){++Batch.CriticalHits;if(Combat->IsDead())++Batch.CriticalKills;}
    }
    return true;
}

void UColdSteelStatusModel::FinishFireMagicCast(FName Id,const FFireMagicRewards& Batch)
{
    if(!FireMagic::IsSkill(Id)||Batch.Hits<=0)return;
    SyncRuntime();auto P=Snapshot();const auto& D=FireMagicDefinition(Id);const auto& T=D.FireMagic;
    ColdSteelSkills::AddExperience(P,D,Batch.Hits*T.HitExperience+Batch.Kills*T.KillExperience+(Batch.bMultiHit?T.MultiHitExperience:0)+(Batch.Kills>=2?T.MultiKillExperience:0));
    ColdSteelSkills::AddExperience(P,CriticalStrikeSkill,Batch.CriticalHits*CriticalStrikeSkill.CriticalHitExperience+Batch.CriticalKills*CriticalStrikeSkill.CriticalKillExperience);
    // 命中与击杀修炼先落实时档案（StageTraining 内部会在升级时立即写盘）。
    StageTraining(MoveTemp(P));
}
