#include "../UI/ColdSteelStatusModel.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "ColdSteelSkillRules.h"
#include "FireballDamage.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/MonsterCombatComponent.h"
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
    return Target!=Shooter&&Combat&&!Combat->IsDead()&&!Target->ActorHasTag(TEXT("Friendly"));
}

bool FireballExposure(UWorld* World,AActor* Target,const FVector& Center,float Radius,
    const FCollisionQueryParams& Query,float& Distance)
{
    const auto* Body=Cast<UPrimitiveComponent>(Target->GetRootComponent());
    if(!Body)return false;
    // Sample the nearest collision surface and the body at multiple heights. A
    // hidden centre must not reject an exposed shoulder or the top of a capsule.
    TArray<FVector,TInlineAllocator<4>> Samples;
    FVector Closest=Body->GetComponentLocation();
    if(Body->GetClosestPointOnCollision(Center,Closest)>=0)Samples.Add(Closest);
    Samples.Add(Body->GetComponentLocation());
    if(const auto* Capsule=Cast<UCapsuleComponent>(Body))
    {
        const float HalfSegment=FMath::Max(0.f,Capsule->GetScaledCapsuleHalfHeight()-Capsule->GetScaledCapsuleRadius());
        Samples.Add(Capsule->GetComponentLocation()+Capsule->GetUpVector()*HalfSegment);
        Samples.Add(Capsule->GetComponentLocation()-Capsule->GetUpVector()*HalfSegment);
    }
    bool Visible=false;Distance=Radius;
    for(const FVector& Sample:Samples)
    {
        const float SampleDistance=FVector::Distance(Center,Sample);
        if(SampleDistance>Radius)continue;
        FHitResult Cover;
        if(World->LineTraceSingleByChannel(Cover,Center,Sample,ECC_Visibility,Query))continue;
        Visible=true;Distance=FMath::Min(Distance,SampleDistance);
    }
    return Visible;
}
}

FColdSteelSkillProgress UColdSteelStatusModel::FireballProgress() const
{ const auto* P=Current.Skills.Find(FireballSkill.Id);return P?*P:FColdSteelSkillProgress(); }

FFireballCast UColdSteelStatusModel::FireballStats(int32 AtLevel) const
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
    C.Damage=FMath::FloorToFloat(Derived(TEXT("matk"))*C.MagicMultiplier);
    C.MagicDamageBonus=SetEffect(TEXT("magicDamage"));
    C.Radius=(F.RadiusBase+L*F.RadiusPerLevel)*F.UnitsToCM*F.RadiusScale;
    C.Speed=F.Speed*F.UnitsToCM;C.Range=F.Range*F.UnitsToCM;
    C.ManaCost=F.ManaCost+(L-1)*F.ManaCostPerLevel;
    const float Growth=float(L-1)/FMath::Max(1,FireballSkill.MaxLevel-1);
    const float BaseCooldown=FMath::Lerp(F.Cooldown,F.MinimumCooldown,Growth);
    C.Cooldown=FMath::Max(F.MinimumCooldown,BaseCooldown*float(1-SetEffect(TEXT("cooldown"))));
    C.HoverDuration=F.HoverDuration;return C;
}

bool UColdSteelStatusModel::BeginFireballCast()
{
    if(Current.bFireballReserved || FireballCooldown()>0){Message=TEXT("火球尚未就绪");return false;}
    const auto F=FireballStats();
    if(!CanSpendMana(F.ManaCost)){Message=TEXT("魔法不足");return false;}
    SyncRuntime();auto P=Snapshot();if(!HasInfiniteMana())P.Mana-=F.ManaCost;
    P.bFireballReserved=true;P.FireballCooldown=HasNoAbilityCooldown()?0.f:F.Cooldown;
    return CommitState(P);
}

void UColdSteelStatusModel::FinishFireballCast()
{
    if(!Current.bFireballReserved)return;
    // The entity cannot be resumed after destruction. Its already-reserved cooldown starts now.
    Current.bFireballReserved=false;SyncRuntime();CommitState(Snapshot());
}

void UColdSteelStatusModel::ApplyFireballExplosion(APawn* Shooter,const FVector& Center,const FFireballCast& Cast,AActor* DirectTarget)
{
    if(!Shooter || !GetWorld() || !Shooter->IsPlayerControlled() || !Shooter->HasAuthority())return;
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
        if(Target!=DirectTarget&&!FireballExposure(GetWorld(),Target,Center,Cast.Radius,Query,Distance))continue;
        const float Ratio=FMath::Clamp(Distance/Cast.Radius,0.f,1.f);
        const bool Eligible=!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
        Rewards.Victim=Target;
        bool Critical=false;
        const CombatFormulaRuntime::MagicHit MagicContext{Cast.CriticalChance,Cast.CriticalDamageBonus,Cast.MagicPenetration,Cast.MagicDamageBonus,&Critical};
        TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(CombatFormulaRuntime::ActiveMagicHit,&MagicContext);
        const float Applied=UGameplayStatics::ApplyDamage(Target,FMath::FloorToFloat(Cast.Damage*(1.f-.5f*Ratio)),Shooter->GetController(),Shooter,UFireballDamage::StaticClass());
        Rewards.Victim=nullptr;
        if(Applied<=0)continue;
        if(auto* Player=::Cast<AFPSGAMECharacter>(Shooter))Player->NotifyConfirmedWeaponHit(Target,Applied);
        if(Eligible)
        {
            ++HitCount;if(Combat->IsDead())++KillCount;
            if(Critical){++CriticalHits;if(Combat->IsDead())++CriticalKills;}
        }
    }
    SyncRuntime();auto P=Snapshot();P.bFireballReserved=false;
    const auto& F=FireballSkill.Fireball;
    ColdSteelSkills::AddExperience(P,FireballSkill,HitCount*F.HitExperience+KillCount*FireballSkill.KillExperience+(HitCount>=2?F.MultiHitExperience:0)+(KillCount>=2?F.MultiKillExperience:0));
    ColdSteelSkills::AddExperience(P,CriticalStrikeSkill,CriticalHits*CriticalStrikeSkill.CriticalHitExperience+CriticalKills*CriticalStrikeSkill.CriticalKillExperience);
    for(const auto& K:Rewards.Kills){P.Kills=FMath::Min(P.Kills+1,MAX_int32-1);P.Experience+=FMath::FloorToInt64(K.Value*TributeEffect(TEXT("expPercent")));}
    while(P.Level<10000){const int64 Need=(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8;if(P.Experience<Need)break;P.Experience-=Need;++P.Level;P.Points=FMath::Min(P.Points+3,1000000);}
    if(P.Level==10000)P.Experience=FMath::Min(P.Experience,(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8-1);
    if(CommitState(P))for(const auto& K:Rewards.Kills)RewardedVictims.Add(K.Key);
}
