#include "../Dungeon/DungeonLayout.h"
#include "../Weapons/Bow/EclipseBowMark.h"
#include "ColdSteelSkillTree.h"
#include "../Monsters/UnknownHumanoid.h"
#include "../Combat/RangedAttackQuery.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelCurrency.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "ColdSteelSkillRules.h"
#include "ColdSteelSpellRewards.h"
#include "ColdSteelSpellFeedback.h"
#include "FireballDamage.h"
#include "MagicOcclusion.h"
#include "FPSIceWall.h"
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../Combat/CombatStatusFormula.h"
#include "FPSMagicPreview.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/MonsterCoreStats.h"
#include "Components/CapsuleComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

namespace
{
bool IsFireballTarget(AActor* Target,APawn* Shooter)
{
    const auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    return Target!=Shooter&&Combat&&!Combat->IsDead()&&!RangedAttackQuery::IsFriendlyUnit(Shooter,Target);
}

void ApplyFireballBurns(const FFireballCast& Spell,APawn* Shooter,AActor* Target)
{
    if(Spell.BurnMultiplier>0.f)
        UCombatStatusFormula::GetOrAdd(Target)->AddBurn(Shooter,Spell.BurnMagicAttack,1,
            Spell.BurnSeconds,Spell.BurnMultiplier,Spell.BurnTick);
    if(Spell.SpecBurnStacks>0 && Spell.SpecBurnMultiplier>0.f)
        UCombatStatusFormula::GetOrAdd(Target)->AddBurn(Shooter,Spell.SpecBurnMagicAttack,
            Spell.SpecBurnStacks,Spell.SpecBurnSeconds,Spell.SpecBurnMultiplier,.5f);
}

}

bool MagicOcclusion::BlastExposure(UWorld* World,APawn* Shooter,AActor* Target,const FVector& Center,float Radius,
    const FCollisionQueryParams& Query,float& Distance)
{
    const auto* Body=Cast<UPrimitiveComponent>(Target->GetRootComponent());
    if(!Body)return false;
    // Keep the closest collision point for blast falloff, plus exposed body probes.
    MagicOcclusion::FBodySamples Samples;MagicOcclusion::BodySamples(Target,Center,Samples);
    FVector Closest=Body->GetComponentLocation();
    if(Body->GetClosestPointOnCollision(Center,Closest)>=0)Samples.Add(Closest);
    bool Visible=false;Distance=Radius;
    for(const FVector& Sample:Samples)
    {
        const float SampleDistance=FVector::Distance(Center,Sample);
        if(SampleDistance>Radius)continue;
        FHitResult Cover;
        if(MagicOcclusion::TraceBlocker(World,Center,Sample,Query,Cover,Shooter))continue;
        Visible=true;Distance=FMath::Min(Distance,SampleDistance);
    }
    return Visible;
}

FColdSteelSkillProgress UColdSteelStatusModel::FireballProgress() const
{ const auto* P=Current.Skills.Find(FireballSkill.Id);return P?*P:FColdSteelSkillProgress(); }

double UColdSteelStatusModel::MagicImplementMultiplier() const
{
    // Wand hook (2026-09-16): a wand declares `wandSpellMultiplier` in its item data and
    // that value multiplies spell damage. Nothing defines the key yet, so this returns 1
    // and the fireball formula keeps today's numbers until the wand lands.
    const auto* Item=Equipped();
    if(!Item)return 1.;
    const double Value=ColdSteelInventory::Number(*Item,TEXT("wandSpellMultiplier"),1.);
    return Value>0.?Value:1.;
}

FFireballCast UColdSteelStatusModel::FireballStats(int32 AtLevel,bool bApplySpecs) const
{
    const int32 L=FMath::Clamp(AtLevel<0?FireballProgress().Level:AtLevel,1,FireballSkill.MaxLevel);
    const auto& F=FireballSkill.Fireball;FFireballCast C;
    C.CriticalChance=Derived(TEXT("crit"));C.CriticalDamageBonus=CriticalStrikeEffect().CriticalDamageBonus;
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            C.MagicPenetration=E->Effect(*Item,TEXT("magicPenetrationPercent"))+E->CraftEffect(*Item,TEXT("magicPenetrationPercent"));
            C.CriticalChance+=100*(E->Effect(*Item,TEXT("critRate"))+E->CraftEffect(*Item,TEXT("critChancePercent"))+E->CraftEffect(*Item,TEXT("magicCritPercent")));
        }
    C.MagicMultiplier=F.MagicBase+(L-1)*F.MagicPerLevel;
    // The wand multiplier is a pure damage factor on top of the magic attack scaling;
    // it stays 1 until a wand with `wandSpellMultiplier` is equipped.
    C.Damage=FMath::FloorToFloat(Derived(TEXT("matk"))*C.MagicMultiplier*MagicImplementMultiplier());
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    C.MagicDamageBonus=(1+SetEffect(TEXT("magicDamage")))*Rune.MagicDamage-1;
    C.Radius=(F.RadiusBase+L*F.RadiusPerLevel)*F.UnitsToCM*F.RadiusScale;
    C.Speed=F.Speed*F.UnitsToCM;C.Range=F.Range*F.UnitsToCM;
    C.Gravity=F.Gravity*FPSMagicPreview::GravityScale();
    const float Growth=float(L-1)/FMath::Max(1,FireballSkill.MaxLevel-1);
    const float BaseCooldown=FMath::Lerp(F.Cooldown,F.MinimumCooldown,Growth);
    C.Cooldown=FMath::Max(F.MinimumCooldown,BaseCooldown*float(1-SetEffect(TEXT("cooldown"))));
    C.Cooldown*=Rune.SkillCooldown*Rune.MagicCooldown;
    if(const auto* I=Equipped();I&&ColdSteelInventory::Text(*I,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* K){return E->CraftEffect(*I,K);};
            const auto* Pawn=RuntimePawn();
            const auto* Status=Pawn?Pawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
            const int32 Chain=Status?Status->ChainSpellStacks():0;
            C.Damage=FMath::FloorToFloat(C.Damage*(1+Craft(TEXT("magicDamagePercent"))+Craft(TEXT("fireDamagePercent")))*(1+Chain*Craft(TEXT("chainSpellDamagePercent"))));
            C.Radius*=1+Craft(TEXT("fireballExplosionRadiusPercent"));C.Range*=1+Craft(TEXT("magicRangePercent"));
            C.Cooldown=BaseCooldown*FMath::Max(.2,(1-Craft(TEXT("magicCooldownPercent")))*(1-SetEffect(TEXT("cooldown"))))*Rune.SkillCooldown*Rune.MagicCooldown;
            C.CastSpeed=FMath::Max(.1f,float(1+Craft(TEXT("castSpeedPercent"))));C.bGrantChain=Craft(TEXT("chainSpellDamagePercent"))!=0;
            C.CastHasteStacks=Craft(TEXT("castHasteStacks"));C.CastHasteDuration=E->CraftEffect(*I,TEXT("castHasteDuration"),5000)/1000;
            C.BurnMagicAttack=Derived(TEXT("matk"));C.BurnMultiplier=Craft(TEXT("fireBurnDamageMul"));
            C.BurnSeconds=E->CraftEffect(*I,TEXT("fireBurnDuration"),3000)/1000;C.BurnTick=E->CraftEffect(*I,TEXT("fireBurnTickMs"),500)/1000;
        }
    // Specializations (skill-tree.json, 2026-11-15). Elemental arrows ask for bApplySpecs=false and
    // apply their 50% inherited share themselves. NPC sheets have no specs, so these read 0.
    if(bApplySpecs)
    {
        C.Radius*=1.f+SpecStat(TEXT("fireball"),TEXT("radiusPercent"))/100.f;
        C.Range+=100.f*SpecStat(TEXT("fireball"),TEXT("rangeMeters"));
        C.DropDelay=FMath::Clamp(SpecStat(TEXT("fireball"),TEXT("dropDelaySeconds")),0.f,3.f);
        C.SpecBurnStacks=FMath::RoundToInt(SpecStat(TEXT("fireball"),TEXT("burnStacks")));
        if(const auto* Spec=ColdSteelSkillTree::FindSpec(TEXT("fireball")))if(const auto* Ignite=Spec->Find(TEXT("ignite")))
        {C.SpecBurnSeconds=Ignite->Param(TEXT("burnSeconds"),3.5f);C.SpecBurnMultiplier=Ignite->Param(TEXT("burnMultiplier"),.5f);}
        C.SpecBurnMagicAttack=Derived(TEXT("matk"));
    }
    C.Range*=float(MagicRangeMultiplier());
    C.ManaCost=SpellManaCost(TEXT("fireball"),L);
    C.HoverDuration=F.HoverDuration;ApplySpellCastSpeed(C.CastSpeed);
    return C;
}

bool UColdSteelStatusModel::BeginFireballCast()
{
    if(Current.bFireballReserved || FireballCooldown()>0){Message=TEXT("火球尚未就绪");return false;}
    const auto F=FireballStats();
    if(!CanSpendMana(F.ManaCost)){Message=TEXT("魔法不足");return false;}
    SyncRuntime();auto P=Snapshot();if(!HasInfiniteMana())P.Mana-=F.ManaCost;
    P.bFireballReserved=true;P.FireballCooldown=HasNoAbilityCooldown()?0.f:F.Cooldown;
    P.FireballCooldownDuration=P.FireballCooldown;
    return CommitState(P);
}

bool UColdSteelStatusModel::RefundInterruptedSpellMana(float PaidMana)
{
    return RefundUnreleasedCast(PaidMana,NAME_None);
}

bool UColdSteelStatusModel::RefundUnreleasedCast(float PaidMana,FName Skill)
{
    if(PaidMana<=0.f&&Skill.IsNone())return true;
    SyncRuntime();auto P=Snapshot();
    if(Skill==TEXT("blizzard"))PaidMana=P.bBlizzardReserved?P.BlizzardReservedMana:0.f;
    if(Skill==TEXT("absoluteZero"))PaidMana=P.bAbsoluteZeroReserved?P.AbsoluteZeroReservedMana:0.f;
    if(Skill==TEXT("dragonBreath"))PaidMana=P.bDragonBreathReserved?P.DragonBreathReservedMana:0.f;
    if(ElectricMagic::IsSkill(Skill))PaidMana=P.ElectricReservedMana.FindRef(Skill);
    if(Skill==TEXT("iceWall"))PaidMana=P.bIceWallReserved?P.IceWallReservedMana:0.f;
    if(PaidMana>0.f)P.Mana=FMath::Min(float(Derived(TEXT("maxMp"))),P.Mana+PaidMana);
    auto Clear=[&](float& Remaining,float& Duration){Remaining=0.f;Duration=0.f;};
    if(ElectricMagic::IsSkill(Skill)){P.ElectricReservedMana.Remove(Skill);P.ElectricCooldowns.Add(Skill,0);P.ElectricCooldownDurations.Add(Skill,0);}
    if(Skill==TEXT("holyLight"))Clear(P.HolyLightCooldown,P.HolyLightCooldownDuration);
    else if(Skill==TEXT("lightning"))Clear(P.LightningCooldown,P.LightningCooldownDuration);
    else if(Skill==TEXT("meteor"))Clear(P.MeteorCooldown,P.MeteorCooldownDuration);
    else if(Skill==TEXT("flameArmor"))Clear(P.FlameArmorCooldown,P.FlameArmorCooldownDuration);
    else if(Skill==TEXT("iceArmor"))Clear(P.IceArmorCooldown,P.IceArmorCooldownDuration);
    else if(Skill==TEXT("lightningHaste"))Clear(P.LightningHasteCooldown,P.LightningHasteCooldownDuration);
    else if(Skill==TEXT("dragonBreath")){P.bDragonBreathReserved=false;P.DragonBreathReservedMana=0;Clear(P.DragonBreathCooldown,P.DragonBreathCooldownDuration);}
    else if(Skill==TEXT("fireball")){P.bFireballReserved=false;Clear(P.FireballCooldown,P.FireballCooldownDuration);}
    else if(Skill==TEXT("blizzard")){P.bBlizzardReserved=false;P.BlizzardReservedMana=0;Clear(P.BlizzardCooldown,P.BlizzardCooldownDuration);}
    else if(Skill==TEXT("absoluteZero")){P.bAbsoluteZeroReserved=false;P.AbsoluteZeroReservedMana=0;Clear(P.AbsoluteZeroCooldown,P.AbsoluteZeroCooldownDuration);}
    else if(Skill==TEXT("iceSpike"))Clear(P.IceSpikeCooldown,P.IceSpikeCooldownDuration);
    else if(Skill==TEXT("iceWall")){P.bIceWallReserved=false;P.IceWallReservedMana=0;Clear(P.IceWallCooldown,P.IceWallCooldownDuration);}
    return CommitState(MoveTemp(P));
}

void UColdSteelStatusModel::FinishFireballCast()
{
    if(!Current.bFireballReserved)return;
    // The entity cannot be resumed after destruction. Its already-reserved cooldown starts now.
    Current.bFireballReserved=false;SyncRuntime();CommitState(Snapshot());
}

void UColdSteelStatusModel::ApplyFireballExplosion(APawn* Shooter,const FVector& Center,const FFireballCast& Cast,const FHitResult* DirectHit,bool bElementalArrow,FEclipseBowShot* EclipseShot)
{
    if(auto* Unknown=::Cast<AUnknownHumanoid>(Shooter)){Unknown->FireballImpact(Center,Cast,DirectHit);return;}
    if(!Shooter || !GetWorld() || !Shooter->IsPlayerControlled() || !Shooter->HasAuthority())return;
    if(Cast.Damage>0)
    {
        UWardBreakableGlass::BreakInRadius(GetWorld(),Center,Cast.Radius,Shooter);
        if(DirectHit)UWardBreakableGlass::BreakHit(*DirectHit,-DirectHit->ImpactNormal);
    }
    AActor* DirectTarget=DirectHit?DirectHit->GetActor():nullptr;
    const bool DirectWeakpoint=DirectHit&&DirectHit->bBlockingHit&&ColdSteelSkills::IsCriticalHit(*DirectHit);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FireballBlast),false,Shooter);
    TArray<FOverlapResult> Overlaps;
    GetWorld()->OverlapMultiByObjectType(Overlaps,Center,FQuat::Identity,FCollisionObjectQueryParams(ECC_Pawn),FCollisionShape::MakeSphere(Cast.Radius),Query);
    TSet<AActor*> Targets;
    for(const auto& O:Overlaps)
    {
        AActor* Target=O.GetActor();
        if(IsFireballTarget(Target,Shooter))Targets.Add(Target);
    }
    // A real projectile contact is a full-strength hit, settled once in the same AOE.
    if(IsFireballTarget(DirectTarget,Shooter))Targets.Add(DirectTarget);
    FFireballRewards Rewards;TGuardValue<FFireballRewards*> Scope(ActiveFireballRewards,&Rewards);
    // Other victims do not act as walls shielding the rest of the explosion.
    for(AActor* Target:Targets)Query.AddIgnoredActor(Target);
    int32 HitCount=0,KillCount=0,CriticalHits=0,CriticalKills=0;
    for(AActor* Target:Targets)
    {
        if(!IsValid(Target))continue;
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if(!Combat || Combat->IsDead())continue;
        float Distance=0;
        if(Target!=DirectTarget&&!MagicOcclusion::BlastExposure(GetWorld(),Shooter,Target,Center,Cast.Radius,Query,Distance))continue;
        const float Ratio=FMath::Clamp(Distance/Cast.Radius,0.f,1.f);
        const bool Eligible=!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
        Rewards.Victim=Target;
        bool Critical=false;
        const CombatFormulaRuntime::MagicHit MagicContext{Cast.CriticalChance,Cast.CriticalDamageBonus,Cast.MagicPenetration,Cast.MagicDamageBonus,&Critical,Target==DirectTarget&&DirectWeakpoint};
        TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(CombatFormulaRuntime::ActiveMagicHit,&MagicContext);
        // 火球是爆炸：按冲击折算削韧。
        const MonsterToughness::FScopedForm FormScope(EMonsterAttackForm::Impact);
        StarMarrow::FHitRecovery CrystalRecovery(Shooter,Target,Cast.StarMarrow);
        FEclipseBowImpact EclipseImpact(EclipseShot, Target);
        const float Applied=UGameplayStatics::ApplyDamage(Target,FMath::FloorToFloat(Cast.Damage*(1.f-.5f*Ratio)),Shooter->GetController(),Shooter,UFireballDamage::StaticClass());
        EclipseImpact.Confirm(Applied);
        CrystalRecovery.Finish(Applied);
        Rewards.Victim=nullptr;
        if(Applied<=0)continue;
        if(!Combat->IsDead())ApplyFireballBurns(Cast,Shooter,Target);
        ColdSteelSpellFeedback::NotifyHit(Shooter,Target,Applied,*Combat,Critical);
        if(Eligible)
        {
            ++HitCount;if(Combat->IsDead())++KillCount;
            if(Critical){++CriticalHits;if(Combat->IsDead())++CriticalKills;}
        }
    }
    // Settle the struck neutral cover after blast exposure, so this same
    // explosion cannot destroy its blocker and then reach victims behind it.
    if(auto* Wall=::Cast<AFPSIceWall>(DirectTarget))
        UGameplayStatics::ApplyDamage(Wall,Cast.Damage,Shooter->GetController(),Shooter,UFireballDamage::StaticClass());
    // An ignition-bearing projectile can leave its real, timed burn on the
    // struck fortification. Neutral cover stays outside blast rewards and AoE.
    else if(const auto* Section=::Cast<AVillageDefenseSection>(DirectTarget);Section && Section->GetHealth()>0.f && Cast.Damage>0.f)
        ApplyFireballBurns(Cast,Shooter,DirectTarget);
    SyncRuntime();auto P=Snapshot();if(!bElementalArrow)P.bFireballReserved=false;
    if(bElementalArrow)StageElementalArrowTraining(P,HitCount,KillCount);
    const auto& F=FireballSkill.Fireball;
    ColdSteelSkills::AddExperience(P,FireballSkill,HitCount*F.HitExperience+KillCount*FireballSkill.KillExperience+(HitCount>=2?F.MultiHitExperience:0)+(KillCount>=2?F.MultiKillExperience:0));
    ColdSteelSpellRewards::AccumulateCriticalTraining(P,CriticalStrikeSkill,CriticalHits,CriticalKills);
    for(const auto& K:Rewards.Kills)
    {
        if(!DungeonLayout::RecordKill(P.DungeonRun,K.Key.Get()))continue;
        P.Kills=FMath::Min(P.Kills+1,MAX_int32-1);
        const int64 Granted=FMath::FloorToInt64(MonsterCoreStats::ScaleKillExperience(K.Key.Get(),Level,K.Value)*TributeEffect(TEXT("expPercent")));
        P.Experience+=Granted;
        if(Granted>0 && !CreditCombatSouls(P,Granted))return;
    }
    ColdSteelSpellRewards::ApplyExperienceLevels(P);
    if(StageTraining(MoveTemp(P)))for(const auto& K:Rewards.Kills)RewardedVictims.Add(K.Key);
}
