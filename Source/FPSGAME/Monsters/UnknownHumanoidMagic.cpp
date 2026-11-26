#include "UnknownHumanoid.h"
#include "MonsterDamageBalance.h"
#include "UnknownSpellCombat.h"
#include "GameFramework/Controller.h"
#include "../Combat/CombatStatusFormula.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Skills/FPSBlizzardComponent.h"
#include "../Skills/BlizzardEnvironment.h"
#include "../Skills/MeteorGround.h"
#include "../Skills/FPSElectricMagicComponent.h"
#include "../Skills/FPSFireballComponent.h"
#include "../Skills/FPSFireballProjectile.h"
#include "../Skills/FPSFireMagicComponent.h"
#include "../Skills/FPSHolyLightComponent.h"
#include "../Skills/FPSIceArmorComponent.h"
#include "../Skills/FPSIceSpikeComponent.h"
#include "../Skills/FPSIceSpikeVolley.h"
#include "../Skills/FPSIceWallComponent.h"
#include "../Skills/FPSLightningComponent.h"
#include "../Skills/FPSLightningHasteComponent.h"
#include "../Skills/LightningHasteSpeed.h"

namespace
{
enum class ESpell : uint8 { Fireball, Spikes, Wall, Blizzard, Lightning, Holy, Haste, IceArmor, Meteor, FlameArmor, Breath, Domain, Lance };
struct FChoice
{
    ESpell Spell;
    FName Id;
    float Cooldown, Range, Speed;
    double Available=0;
    double RetryAfter=0;
};
template<class T> void Install(AUnknownHumanoid* Owner)
{
    auto* Component=NewObject<T>(Owner);
    Owner->AddInstanceComponent(Component);
    Component->SetIsReplicated(true);
    Component->RegisterComponent();
}
}
struct FUnknownSpellbook
{
    TArray<FChoice> Choices;
    int32 Selected=INDEX_NONE;
    bool bSelf=false;
    bool bSawFocus=false;
    TWeakObjectPtr<APawn> Focus;
    uint32 Serial=0;
    double DecideAfter=0;
    FIceSpikeCast Spikes;
    FIceWallCast Wall;
    FBlizzardCast Blizzard;
    FLightningCast Lightning;
    FHolyLightCast Holy;
    FLightningHasteCast Haste;
    FIceArmorCast IceArmor;
    FFireMagicCast Meteor, FlameArmor, Breath;
    FElectricMagicCast Domain,Lance;
};

void AUnknownHumanoid::PrepareMagic()
{
    if (!HasAuthority() || !Sheet || Spellbook || Loadout.Role!=EUnknownRole::Magic) return;
    Spellbook=MakeShared<FUnknownSpellbook>();
    auto& B=*Spellbook;
    const int32 Rank=FMath::Clamp(Loadout.Level/10,1,3);
    Spell=Sheet->FireballStats(Rank);
    B.Spikes=Sheet->IceSpikeStats(Rank); B.Wall=Sheet->IceWallStats(Rank);
    B.Blizzard=Sheet->BlizzardStats(Rank); B.Lightning=Sheet->LightningStats(Rank);
    B.Holy=Sheet->HolyLightStats(Rank); B.Haste=Sheet->LightningHasteStats(Rank);
    B.IceArmor=Sheet->IceArmorStats(Rank);
    B.Meteor=Sheet->FireMagicStats(TEXT("meteor"),Rank);
    B.FlameArmor=Sheet->FireMagicStats(TEXT("flameArmor"),Rank);
    B.Breath=Sheet->FireMagicStats(TEXT("dragonBreath"),Rank);
    B.Domain=Sheet->ElectricMagicStats(TEXT("stormDomain"),Rank);
    B.Lance=Sheet->ElectricMagicStats(TEXT("thunderLance"),Rank);
    UnknownDamageBalance::Tune(Loadout.Level,Spell);
    UnknownDamageBalance::Tune(Loadout.Level,B.Spikes);
    UnknownDamageBalance::Tune(Loadout.Level,B.Wall);
    UnknownDamageBalance::Tune(Loadout.Level,B.Blizzard);
    UnknownDamageBalance::Tune(Loadout.Level,B.Lightning);
    UnknownDamageBalance::Tune(Loadout.Level,B.Holy);
    UnknownDamageBalance::Tune(Loadout.Level,B.Meteor);
    UnknownDamageBalance::Tune(Loadout.Level,B.FlameArmor);
    UnknownDamageBalance::Tune(Loadout.Level,B.Breath);
    UnknownDamageBalance::Tune(Loadout.Level,B.Domain,false);
    UnknownDamageBalance::Tune(Loadout.Level,B.Lance,true);
    auto Add=[&](ESpell Type,FName Id,const auto& Stats,float Range)
    { B.Choices.Add({Type,Id,Stats.Cooldown,Range,Stats.CastSpeed}); };
    Add(ESpell::Fireball,TEXT("fireball"),Spell,Spell.Range);
    Add(ESpell::Spikes,TEXT("iceSpike"),B.Spikes,B.Spikes.Range);
    Add(ESpell::Wall,TEXT("iceWall"),B.Wall,B.Wall.Range);
    Add(ESpell::Blizzard,TEXT("blizzard"),B.Blizzard,B.Blizzard.Range);
    Add(ESpell::Lightning,TEXT("lightningStrike"),B.Lightning,B.Lightning.Range);
    Add(ESpell::Holy,TEXT("holyLight"),B.Holy,B.Holy.Range);
    Add(ESpell::Haste,TEXT("lightningHaste"),B.Haste,Spell.Range);
    Add(ESpell::IceArmor,TEXT("iceArmor"),B.IceArmor,Spell.Range);
    Add(ESpell::Meteor,TEXT("meteor"),B.Meteor,B.Meteor.Range);
    Add(ESpell::FlameArmor,TEXT("flameArmor"),B.FlameArmor,B.FlameArmor.AuraRadius);
    Add(ESpell::Breath,TEXT("dragonBreath"),B.Breath,B.Breath.Radius);
    Add(ESpell::Domain,TEXT("stormDomain"),B.Domain.Hit,B.Domain.Radius);
    Add(ESpell::Lance,TEXT("thunderLance"),B.Lance.Hit,B.Lance.Hit.Range);
    Install<UFPSIceSpikeComponent>(this); Install<UFPSIceWallComponent>(this);
    Install<UFPSBlizzardComponent>(this); Install<UFPSLightningComponent>(this);
    Install<UFPSHolyLightComponent>(this); Install<UFPSIceArmorComponent>(this);
    Install<UFPSLightningHasteComponent>(this); Install<UFPSFireMagicComponent>(this);
    Install<UFPSElectricMagicComponent>(this);
}

bool AUnknownHumanoid::HasChosenMagic() const
{
    return Spellbook && Spellbook->Choices.IsValidIndex(Spellbook->Selected);
}
bool AUnknownHumanoid::SelfCast() const { return HasChosenMagic() && Spellbook->bSelf; }
FName AUnknownHumanoid::ChosenMagicId() const
{
    return HasChosenMagic()?Spellbook->Choices[Spellbook->Selected].Id:NAME_None;
}

void AUnknownHumanoid::StartMagicAttack()
{
    const FName Skill=ChosenMagicId();
    const float Windup=Skill==TEXT("thunderLance")?FMath::Max(AttackSeconds*.7f,Spellbook->Lance.MinCharge):AttackSeconds*.7f;
    const float Recovery=AttackSeconds*.3f;
    SetAction(EUnknownAction::Cast,Windup+Recovery+(Skill==TEXT("dragonBreath")?Spellbook->Breath.Duration:0.f));
    Motion.Skill=Skill;
    Motion.Windup=Windup;
    Motion.Preparation=FMath::Max(.01f,Windup-AttackSeconds*.18f);
    Motion.Recovery=Recovery;
    ContactAt=Motion.Started+Windup;
}

void AUnknownHumanoid::CancelRangedAction()
{
    if (Motion.Action!=EUnknownAction::Cast && Motion.Action!=EUnknownAction::DrawBow) return;
    if (Spellbook)
    {
        if (HasChosenMagic()) Spellbook->Choices[Spellbook->Selected].RetryAfter=ServerTime()+.9;
        Spellbook->Selected=INDEX_NONE;
        Spellbook->DecideAfter=ServerTime();
    }
    if (auto* Fire=FindComponentByClass<UFPSFireMagicComponent>()) Fire->FinishDragonBreathForRemoval();
    // A cancelled preparation spends its elapsed hold cost, but does not fire
    // a delayed projectile or consume a successful-release cooldown.
    NextAttack=FMath::Max(NextAttack,double(ServerTime())+.3);
    SetAction(EUnknownAction::Ready);
}

void AUnknownHumanoid::SelectMagic(float Distance,bool bVisible)
{
    // A moving cast must keep the spell/range snapshot chosen at its start.
    // Replanning a route is not permission to replace an in-flight gesture.
    if (!Spellbook || Motion.Action==EUnknownAction::Cast) return;
    auto& B=*Spellbook;
    const double Now=ServerTime();
    auto* Focus=TacticalTarget.Get();
    const FVector Axis=bVisible&&Focus?(Focus->GetActorLocation()-GetActorLocation()).GetSafeNormal2D():FVector::ZeroVector;
    const float Closing=bVisible && Focus?-FVector::DotProduct(Focus->GetVelocity()-GetVelocity(),Axis):0.f;
    const bool Pressed=bVisible && Distance-FMath::Max(0.f,Closing)*.55f<550.f;
    const bool CanPlant=!Pressed && !bRetreating && Now>=CrowdYieldUntil &&
        (Position==EUnknownPosition::Open || Position==EUnknownPosition::Peeking);
    if(Now<B.DecideAfter && bVisible==B.bSawFocus && B.Focus.Get()==Focus &&
        !(ChosenMagicId()==TEXT("thunderLance") && !CanPlant))return;
    B.bSawFocus=bVisible; B.Focus=Focus;
    const auto* EnemyStatus=bVisible&&Focus?Focus->FindComponentByClass<UCombatStatusFormula>():nullptr;
    const bool Cluster=bVisible && HasVisibleCluster(Focus,B.Blizzard.RadiusX);
    const bool Immobilized=EnemyStatus && (EnemyStatus->IsFrozen() || EnemyStatus->IsStunned());
    const bool SlowTarget=bVisible && Focus && Focus->GetVelocity().Size2D()<120.f;
    float Best=-MAX_flt;
    double NextReady=Now+.45;
    B.Selected=INDEX_NONE; B.bSelf=false;
    for (int32 I=0;I<B.Choices.Num();++I)
    {
        const auto& C=B.Choices[I];
        const double ReadyAt=FMath::Max(C.Available,C.RetryAfter);
        if (Now<ReadyAt)
        {
            NextReady=FMath::Min(NextReady,ReadyAt);
            continue;
        }
        bool Self=false;
        float Score=FMath::FRandRange(0,.65f);
        switch(C.Spell)
        {
        case ESpell::Blizzard:
            if (Cluster || Immobilized) Score+=1.f;
            break;
        case ESpell::Meteor:
            if (Cluster || Immobilized) Score+=1.f;
            else if (SlowTarget) Score+=.45f;
            break;
        case ESpell::Lance:
            if (!CanPlant) continue;
            if (Distance>Spell.Range*.75f && Distance<=C.Range) Score+=.65f;
            if (EnemyStatus && EnemyStatus->ElectrifiedCount()>0) Score+=.55f;
            break;
        case ESpell::Lightning:
            if(EnemyStatus&&EnemyStatus->ElectrifiedCount()>0)Score+=.55f;
            break;
        case ESpell::Spikes:
            if (Pressed) Score+=.8f;
            if(bVisible && Focus && EnemyStatus && EnemyStatus->ChillCount()==0 && Focus->GetVelocity().Size2D()>240.f)Score+=.4f;
            break;
        case ESpell::Holy: Self=Health<MaxHealth*.72f; if(Self)Score+=1.45f; break;
        case ESpell::Wall:
            if (!bVisible || bHasCover || Now-LastIncomingHit>2.5f) continue;
            Score+=1.0f; break;
        case ESpell::IceArmor:
            Self=true; Score+=Now-LastIncomingHit<1.8f?.65f:(bVisible?-.45f:.45f); break;
        case ESpell::Haste:
            Self=true; Score+=Pressed?1.1f:Distance>Spell.Range?.6f:(bVisible?-.45f:.45f); break;
        case ESpell::FlameArmor: case ESpell::Domain:
            // Both effects are centred on the caster. Only spend a cast on a visible opponent inside the effect.
            if (!bVisible || Distance>C.Range) continue;
            // These effects follow their caster. Once chosen near a threat,
            // keep withdrawing while applying them instead of adopting their
            // short damage radius as a new pursuit/standing distance.
            Self=true;
            Score+=C.Spell==ESpell::Domain && Cluster ? 1.2f : .5f;
            break;
        case ESpell::Breath:
            if (Distance<C.Range*.88f) Score+=Cluster || Immobilized ? 1.f : .6f;
            break;
        default: break;
        }
        if (!Self)
        {
            if (!bVisible) continue;
            if (C.Spell!=ESpell::Wall && Distance>C.Range)
                Score-=2.f+((Distance-C.Range)/FMath::Max(100.f,C.Range));
        }
        if (Score>Best) {Best=Score; B.Selected=I; B.bSelf=Self;}
    }
    B.DecideAfter=HasChosenMagic()?Now+1.65:NextReady;
    if (!HasChosenMagic())
    {
        // Waiting for cooldowns must not preserve a previous close-range
        // spell's pursuit radius and send the caster back towards the enemy.
        AttackRange=Spell.Range;
        PreferredRange=AttackRange*.78f;
        return;
    }
    const auto& C=B.Choices[B.Selected];
    AttackRange=C.Spell==ESpell::Wall||B.bSelf?Spell.Range:C.Range;
    PreferredRange=AttackRange*(C.Spell==ESpell::Breath?.62f:.78f);
    AttackSeconds=(C.Spell==ESpell::Lance?FMath::Max(1.f,B.Lance.MinCharge):1.f)/
        FMath::Max(.1f,C.Speed*LightningHaste::ActionSpeed(this));
}

bool AUnknownHumanoid::ReleaseMagic(APawn* Target,FVector Aim)
{
    if (!HasChosenMagic()) return false;
    auto& B=*Spellbook;
    auto& C=B.Choices[B.Selected];
    bool Cast=false;
    FColdSteelNetCastRequest Req;
    Req.SkillId=C.Id; Req.SourcePawn=this; Req.CastId=++B.Serial; Req.Target=Target;
    Req.AimNormal=(Aim-GetPawnViewLocation()).GetSafeNormal();
    Req.AimAxis=Req.AimNormal.GetSafeNormal2D(); Req.AimPoint=Target->GetNavAgentLocation();
    const bool Clear=B.bSelf || (FVector::DistSquared(GetActorLocation(),Target->GetActorLocation())<=FMath::Square(AttackRange) &&
        HasFiringLane(AimOrigin(),*Target,Target->GetActorLocation()));
    if (Clear)
    {
        switch(C.Spell)
        {
        case ESpell::Fireball:
            if(auto* Orb=Fireball?Fireball->SpawnOrbForCast(this,Spell):nullptr)
            {
                Orb->LaunchAt(Aim,Target); Cast=Orb->IsFlying();
            } break;
        case ESpell::Spikes:
            if(auto* V=FindComponentByClass<UFPSIceSpikeComponent>()->SpawnVolleyForCast(this,B.Spikes))
            { V->LaunchAt(Aim,Target); Cast=V->IsFlying(); } break;
        case ESpell::Wall:
            Req.AimPoint=GetNavAgentLocation()+Req.AimAxis*FMath::Clamp(FVector::Dist2D(GetActorLocation(),Aim)*.45f,145.f,B.Wall.Range*.8f);
            Req.AimNormal=Req.AimAxis;
            Cast=FindComponentByClass<UFPSIceWallComponent>()->NetCommitWall(this,Req,Sheet,B.Wall); break;
        case ESpell::Blizzard:
            Req.AimNormal=FVector::UpVector;
            Cast=FindComponentByClass<UFPSBlizzardComponent>()->NetCommitZone(this,Req,Sheet,B.Blizzard); break;
        case ESpell::Lightning: Cast=FindComponentByClass<UFPSLightningComponent>()->NetRelease(this,Req,Sheet,B.Lightning); break;
        case ESpell::Holy:
            Req.Variant=B.bSelf?1:0;
            Cast=FindComponentByClass<UFPSHolyLightComponent>()->NetRelease(this,Req,Sheet,B.Holy); break;
        case ESpell::Haste: Cast=FindComponentByClass<UFPSLightningHasteComponent>()->NetRelease(this,Req,Sheet,B.Haste); break;
        case ESpell::IceArmor: Cast=FindComponentByClass<UFPSIceArmorComponent>()->NetRelease(this,Req,Sheet,B.IceArmor); break;
        case ESpell::Meteor:
        {
            Req.AimNormal=FVector::UpVector;
            // The meteor has a fixed fall time at a ground location. Lock a visible
            // floor under the forecast, falling back to the original point when invalid.
            const FVector Travel=Target->GetVelocity()*FVector(1,1,0)*B.Meteor.FallSeconds;
            if (!Travel.IsNearlyZero())
            {
                FHitResult Floor;
                if (BlizzardEnvironment::Floor(this,Req.AimPoint+Travel,90.f,160.f,Floor))
                {
                    FVector Point=Floor.ImpactPoint, Normal=Floor.ImpactNormal;
                    FString Failure;
                    if (MeteorGround::Validate(this,B.Meteor.Range,Point,Normal,true,Failure))
                    {
                        Req.AimPoint=Point;
                        Req.AimNormal=Normal;
                    }
                }
            }
            Cast=FindComponentByClass<UFPSFireMagicComponent>()->NetRelease(this,Req,Sheet,B.Meteor);
            break;
        }
        case ESpell::FlameArmor: Cast=FindComponentByClass<UFPSFireMagicComponent>()->NetRelease(this,Req,Sheet,B.FlameArmor); break;
        case ESpell::Breath:
            if(GetController())GetController()->SetControlRotation(Req.AimNormal.Rotation());
            Req.AimPoint=FVector(75,15,0);
            Cast=FindComponentByClass<UFPSFireMagicComponent>()->NetRelease(this,Req,Sheet,B.Breath);
            if(Cast) { Motion.Duration=ServerTime()-Motion.Started+B.Breath.Duration+Motion.Recovery; ForceNetUpdate(); }
            break;
        case ESpell::Domain: Cast=FindComponentByClass<UFPSElectricMagicComponent>()->NetRelease(this,Req,Sheet,B.Domain); break;
        case ESpell::Lance:
            Req.Charge=FMath::Clamp(Motion.Windup,B.Lance.MinCharge,B.Lance.MaxCharge);
            Cast=FindComponentByClass<UFPSElectricMagicComponent>()->NetRelease(this,Req,Sheet,B.Lance); break;
        }
    }
    const double Now=ServerTime();
    // These two shared executors play locally on authority; their replicated
    // arc/light actors carry visuals only. Forward the release to observers.
    if(Cast&&(C.Spell==ESpell::Lightning||C.Spell==ESpell::Holy))
        MulticastMagicReleaseSound(C.Id,C.Spell==ESpell::Holy&&!B.bSelf?Target->GetActorLocation():GetActorLocation());
    C.Available=Now+(Cast?C.Cooldown:1.5f);
    B.Selected=INDEX_NONE; B.DecideAfter=Now;
    if (!Cast)
    {
        Motion.Duration=Now-Motion.Started+Motion.Recovery;
        ForceNetUpdate();
    }
    return Cast;
}
