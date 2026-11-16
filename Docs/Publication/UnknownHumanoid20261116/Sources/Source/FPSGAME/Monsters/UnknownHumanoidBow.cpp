#include "UnknownHumanoidBow.h"
#include "UnknownHumanoid.h"
#include "MonsterDamageBalance.h"
#include "UnknownSpellCombat.h"
#include "MonsterAIController.h"
#include "MonsterSpellAim.h"
#include "FPSCombatHealthComponent.h"
#include "../Weapons/Bow/BowArrow.h"
#include "../Weapons/Bow/BowFlexMeshComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Skills/FPSMagicArrowRain.h"
#include "../Skills/MagicArrowRainGround.h"
#include "../Skills/FPSIlluminationArrowComponent.h"
#include "../Skills/IlluminationMarkComponent.h"
#include "../Skills/ElementalArrowVisual.h"
#include "../Skills/IlluminationArrowVisual.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Skills/EnemyAttackDamage.h"
#include "../Combat/CoreCombatFormula.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Characters/FPSBodyBowMotion.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

namespace
{
    bool FindRainImpact(APawn* Shooter, APawn* Target, const FMagicArrowRainCast& Rain, FVector Start,
        FVector& Ground, FVector& Normal, FVector& Burst)
    {
        const FVector Feet=Target->GetNavAgentLocation();
        const FVector Predicted=MonsterSpellAim::LaunchAim(Shooter,Target,Start,Target->GetActorLocation(),
            Rain.SeedSpeed,Rain.Range);
        Ground=Feet+Predicted-Target->GetActorLocation()+Target->GetVelocity()*MagicArrowRainTiming::DamageDelay;
        FString Failure;
        Normal=FVector::UpVector;
        if (MagicArrowRainGround::Validate(Shooter,Rain,Start,Ground,Normal,Burst,Failure)) return true;
        Ground=Feet; Normal=FVector::UpVector;
        return MagicArrowRainGround::Validate(Shooter,Rain,Start,Ground,Normal,Burst,Failure);
    }
}

void AUnknownHumanoid::CacheBowStats()
{
    const auto Stats=ColdSteelBow::Evaluate(*Sheet->Equipped(),Sheet);
    WeaponDamage=Stats.Damage.Scaled(Sheet->AmmoDamageMultiplier(*Sheet->Equipped()));
    PhysicalPenetration+=Sheet->AmmoArmorPenetration(*Sheet->Equipped());
    AttackRange=FMath::Min(3400.f,float(Stats.Range*100.));
    PreferredRange=AttackRange*.70f;
    AttackSeconds=Stats.Draw+.34f;
    StaminaCost=Stats.Stamina+Stats.ChargeStamina*Stats.Draw;
    CriticalBonus=Sheet->CriticalStrikeEffect().CriticalDamageBonus+Stats.CriticalDamageBonus;
}

void AUnknownHumanoid::PrepareArchery()
{
    if (!HasAuthority() || !BowSheet || Archery) return;
    Archery=MakeShared<FUnknownArchery>();
    auto& B=*Archery;
    const int32 Rank=FMath::Clamp(Loadout.Level/10,1,3);
    const auto* Guns=GetGameInstance()->GetSubsystem<UGunsmithSystem>();
    const auto Item=Guns->ResolveBowVisual(*BowSheet->Equipped());
    B.Stats=ColdSteelBow::Evaluate(Item,BowSheet);
    B.Elements[0]=BowSheet->ElementalArrowStats(EArrowElement::Fire,Rank);
    B.Elements[1]=BowSheet->ElementalArrowStats(EArrowElement::Ice,Rank);
    B.Elements[2]=BowSheet->ElementalArrowStats(EArrowElement::Lightning,Rank);
    B.Rain=BowSheet->MagicArrowRainStats(Rank);
    B.Illumination=BowSheet->IlluminationArrowStats(Rank);
    for(auto& Element:B.Elements)UnknownDamageBalance::Tune(Loadout.Level,Element);
    UnknownDamageBalance::Tune(Loadout.Level,B.Rain);
    UnknownDamageBalance::Tune(Loadout.Level,B.Illumination);
    B.Mana=B.MaxMana=BowSheet->Derived(TEXT("maxMp"));
    B.ManaRegen=BowSheet->Derived(TEXT("mpRegen"));
    B.ElementHoldMana=BowSheet->MasteryDefinition(TEXT("elementalArrow")).ElementalArrow.ManaPerSecond;
    B.Gravity=ColdSteelInventory::Number(Item,TEXT("arrow_gravity_cm"),520.f);
    B.Ammo=BowSheet->AmmoDefinitionFor(Item);
    B.ArrowMesh=FSoftObjectPath(ColdSteelInventory::Text(Item,TEXT("bow_part_arrow_mesh")));
    B.ArrowLength=ColdSteelInventory::Number(Item,TEXT("arrow_length_cm"),76.f);
    B.ArrowRadius=ColdSteelInventory::Number(Item,TEXT("bow_part_arrow_radius_cm"),.3f);
    auto* Marks=NewObject<UFPSIlluminationArrowComponent>(this);
    AddInstanceComponent(Marks); Marks->RegisterComponent(); Marks->SetComponentTickEnabled(false);
}

bool AUnknownHumanoid::StartBowAttack(APawn* Target)
{
    PrepareArchery();
    if (!Archery || Stamina<StaminaCost) return false;
    auto& B=*Archery;
    const float Distance=FVector::Dist(AimOrigin(),Target->GetActorLocation());
    const float ClosingSpeed=FVector::DotProduct(Target->GetVelocity()-GetVelocity(),(GetActorLocation()-Target->GetActorLocation()).GetSafeNormal2D());
    const bool Closing=ClosingSpeed>100.f;
    const double Now=ServerTime();
    const float FullDraw=B.Stats.Draw*ColdSteelBow::DrawSpeedScale(B.bPerfectPending);
    const auto PiercingStats=HeartPiercingArrow::ForModel(BowSheet,FMath::Clamp(Loadout.Level/10,1,3),FullDraw);
    const float PiercingDraw=FMath::Max(FullDraw,PiercingStats.ChargeSeconds);
    B.Selected=EUnknownArrow::Normal;
    B.ReleaseMana=0.f; B.HoldMana=0.f;
    float Best=.35f;
    for (int32 I=1; I<7; ++I)
    {
        if (Now<B.Available[I]) continue;
        const auto Kind=static_cast<EUnknownArrow>(I);
        const float SkillDraw=Kind==EUnknownArrow::Piercing?PiercingDraw:Kind==EUnknownArrow::Rain?B.Rain.ChargeSeconds:FullDraw;
        // Do not choose a long charge when the visible opponent can reach the
        // blade-switch band before release. Faster/control arrows remain usable.
        if ((Kind==EUnknownArrow::Piercing || Kind==EUnknownArrow::Rain) &&
            Distance-FMath::Max(0.f,ClosingSpeed)*FMath::Min(SkillDraw,1.5f)<550.f) continue;
        if (Stamina<B.Stats.Stamina+B.Stats.ChargeStamina*SkillDraw) continue;
        const bool Elemental=Kind>=EUnknownArrow::Fire && Kind<=EUnknownArrow::Lightning;
        const float ReleaseMana=Elemental?B.Elements[I-int32(EUnknownArrow::Fire)].ManaCost:
            Kind==EUnknownArrow::Rain?B.Rain.ManaCost:Kind==EUnknownArrow::Illumination?B.Illumination.ManaCost:0.f;
        const float HoldMana=Elemental?B.ElementHoldMana:Kind==EUnknownArrow::Rain?B.Rain.ManaPerSecond:0.f;
        if (B.Mana<ReleaseMana+HoldMana*SkillDraw) continue;
        float Score=0.f;
        switch (Kind)
        {
        case EUnknownArrow::Piercing: Score=Distance>1500.f && !Closing?1.3f:0.f; break;
        case EUnknownArrow::Fire: Score=1.f; break;
        case EUnknownArrow::Ice: Score=Closing?2.f:.85f; break;
        case EUnknownArrow::Lightning: Score=Distance<1300.f?1.5f:.85f; break;
        case EUnknownArrow::Illumination: Score=UIlluminationMarkComponent::IsMarked(Target)?0.f:1.7f; break;
        case EUnknownArrow::Rain:
        {
            FVector Ground,Normal,Burst;
            if (FindRainImpact(this,Target,B.Rain,AimOrigin(),Ground,Normal,Burst))
            {
                Score=HasVisibleCluster(Target,B.Rain.Radius)?2.3f:Target->GetVelocity().Size2D()<140.f?1.4f:.4f;
            }
            break;
        }
        default: break;
        }
        if (Kind==B.Previous) Score*=.4f;
        Score*=FMath::FRandRange(.85f,1.15f);
        if (Score>Best)
        {
            Best=Score; B.Selected=Kind;
            B.ReleaseMana=ReleaseMana; B.HoldMana=HoldMana;
        }
    }
    const bool Piercing=B.Selected==EUnknownArrow::Piercing;
    const float Draw=Piercing?PiercingDraw:
        B.Selected==EUnknownArrow::Rain?B.Rain.ChargeSeconds:FullDraw;
    const float Cost=B.Stats.Stamina+B.Stats.ChargeStamina*Draw;
    if (Stamina<Cost) return false;
    B.DrawAccountedAt=Now;
    B.Shot={}; B.Shot.ItemDefinition=Loadout.Weapon;
    B.Shot.DamagePanel=WeaponDamage.Scaled(Piercing?PiercingStats.DamageMultiplier:1.f);
    if(Piercing && B.Shot.DamagePanel.Total()>0.f)
        B.Shot.DamagePanel=B.Shot.DamagePanel.Scaled(
            UnknownDamageBalance::Piercing(B.Shot.DamagePanel.Total(),Loadout.Level)/B.Shot.DamagePanel.Total());
    B.Shot.CriticalChance=CriticalChance; B.Shot.CriticalDamageBonus=CriticalBonus;
    B.Shot.WeakpointPercent=WeakpointPercent;
    B.Shot.ArmorPenetration=PhysicalPenetration; B.Shot.MagicPenetration=MagicPenetration;
    B.Shot.bHeartPiercingArrow=Piercing; B.Shot.BowTargetPenetration=Piercing?PiercingStats.TargetPenetration:0;
    B.Shot.bPerfectBowRelease=!Piercing;
    B.LaunchSpeed=B.Stats.Speed*100.f*(Piercing?PiercingStats.SpeedMultiplier:1.f);
    AttackTarget=Target;
    SetAction(EUnknownAction::DrawBow,Draw+.34f);
    Motion.Windup=Draw; Motion.Preparation=FMath::Min(FullDraw,Draw); Motion.Recovery=.34f;
    Motion.ArrowKind=uint8(B.Selected); ContactAt=Now+Draw; bPendingContact=true; ForceNetUpdate();
    return true;
}

void AUnknownHumanoid::ReleaseBowAttack(APawn* Target)
{
    if (!Archery || bBowBlades || !FacingTarget(*Target) ||
        FVector::DistSquared(GetActorLocation(),Target->GetActorLocation())>FMath::Square(AttackRange) ||
        !HasFiringLane(AimOrigin(),*Target,Target->GetActorLocation())) return;
    auto& B=*Archery;
    const FVector Start=AimOrigin();
    if (B.Selected==EUnknownArrow::Rain)
    {
        FVector Ground,Normal,Burst;
        if (!FindRainImpact(this,Target,B.Rain,Start,Ground,Normal,Burst)) return;
        auto Snapshot=B.Rain; Snapshot.SurfaceNormal=Normal;
        FActorSpawnParameters Spawn; Spawn.Owner=this; Spawn.Instigator=this;
        if (auto* Rain=GetWorld()->SpawnActor<AFPSMagicArrowRain>(Start,FRotator::ZeroRotator,Spawn))
            Rain->Launch(BowSheet,Snapshot,Start,Ground,Burst);
        else return;
        B.Available[int32(B.Selected)]=ServerTime()+Snapshot.Cooldown;
    }
    else
    {
        // Shared hostile-projectile interception includes cover, range and gravity.
        const FVector Aim=Target->GetActorLocation()+FVector(0,0,14);
        const FVector Led=MonsterSpellAim::LaunchAim(this,Target,Start,Aim,B.LaunchSpeed,B.Stats.Range*100.f,B.Gravity);
        const FVector Direction=FMath::VRandCone((Led-Start).GetSafeNormal(),float(B.Stats.Spread*.35));
        FActorSpawnParameters Spawn; Spawn.Owner=this; Spawn.Instigator=this;
        Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Arrow=GetWorld()->SpawnActor<ABowArrow>(Start,Direction.Rotation(),Spawn);
        if (!Arrow) return;
        Arrow->Configure(B.Shot.DamagePanel.Total(),B.LaunchSpeed,B.Gravity,B.Stats.Range*100.f,
            B.Shot,B.ArrowMesh.Get(),nullptr,B.ArrowRadius,B.ArrowLength,B.Ammo,false,8.f);
        if (B.Selected>=EUnknownArrow::Fire && B.Selected<=EUnknownArrow::Lightning)
        {
            const auto& Element=B.Elements[int32(B.Selected)-int32(EUnknownArrow::Fire)];
            Arrow->SetElementalCast(Element); B.Available[int32(B.Selected)]=ServerTime()+Element.Cooldown;
        }
        if (B.Selected==EUnknownArrow::Illumination)
        {
            auto Mark=B.Illumination; Mark.Id=FGuid::NewGuid(); Arrow->SetIlluminationCast(Mark);
            B.Available[int32(B.Selected)]=ServerTime()+Mark.Cooldown;
        }
        Arrow->ResolveLaunchObstruction(Start);
    }
    Stamina=FMath::Max(0.f,Stamina-float(B.Stats.Stamina));
    ResourceDelay=Sheet->StaminaSettings().RecoveryDelay;
    B.Mana=FMath::Max(0.f,B.Mana-B.ReleaseMana);
    B.Previous=B.Selected;
    B.bPerfectPending=B.Selected!=EUnknownArrow::Piercing && B.Selected!=EUnknownArrow::Rain;
    NextAttack=ServerTime()+.34f+B.Stats.Nock;
    MulticastBowRelease();
}

float AUnknownHumanoid::HitWithArrow(const FHitResult& Hit,float Damage,FVector Direction,const FColdSteelSkillShot& Shot)
{
    auto* Victim=Cast<APawn>(Hit.GetActor());
    if (!HasAuthority() || !UnknownSpell::IsTarget(this,Victim)) return 0.f;
    const bool Weak=ColdSteelSkills::IsCriticalHit(Hit);
    const auto* Model=Victim->FindComponentByClass<UFPSCombatHealthComponent>();
    if (!Model || Model->IsDead()) return 0.f;
    const auto* Defender=ColdSteelAuthority::ForPawn(Victim);
    const float Resistance=Defender?Defender->Derived(TEXT("critRes")):0.f;
    if (Weak) Damage*=1.f+Shot.WeakpointPercent/100.f;
    if (Weak || FMath::FRand()*100.f<CoreCombatFormula::CriticalChance(Shot.CriticalChance,Resistance))
        Damage=CoreCombatFormula::CriticalDamage(Damage,Shot.CriticalDamageBonus);
    const UnknownSpell::FWeaponSnapshot Snapshot{Shot.DamagePanel.Total()>0.f?
        float((Shot.DamagePanel.BaseMagic+Shot.DamagePanel.AddedMagic)/Shot.DamagePanel.Total()):0.f,Shot.ArmorPenetration,Shot.MagicPenetration};
    TGuardValue<const UnknownSpell::FWeaponSnapshot*> Scope(UnknownSpell::ActiveWeapon,&Snapshot);
    return UGameplayStatics::ApplyPointDamage(Victim,Damage,Direction,Hit,GetController(),this,UEnemyRangedDamage::StaticClass());
}

void AUnknownHumanoid::OnRep_BowMode()
{
    if (Loadout.Role!=EUnknownRole::Bow) return;
    HeldWeapon->SetVisibility(!bBowBlades,true);
    for (auto* Blade:{BackupRight.Get(),BackupLeft.Get()}) if (Blade) Blade->SetVisibility(bBowBlades,true);
    if (NockedArrow) NockedArrow->SetVisibility(!bBowBlades && Motion.Action==EUnknownAction::DrawBow && ServerTime()<Motion.Started+Motion.Windup);
    if(bBowBlades){if(HeldArrowElement)HeldArrowElement->Clear();if(HeldArrowLight)HeldArrowLight->Clear();}
}

void AUnknownHumanoid::MulticastBowRelease_Implementation()
{
    if (GetNetMode()!=NM_DedicatedServer)
        if (auto* Sound=BowReleaseSound.Get()) UGameplayStatics::PlaySoundAtLocation(this,Sound,AimOrigin(),.85f,1.f,0.f,MeleeAttenuation);
}

void AUnknownHumanoid::UpdateBowPresentation()
{
    if (Loadout.Role!=EUnknownRole::Bow || bBowBlades || !bVisualReady || GetNetMode()==NM_DedicatedServer) return;
    auto* Anim=GetMesh()->GetAnimInstance(); if (!Anim) return;
    double V[7]; for (int32 I=0; I<7; ++I) V[I]=Anim->GetCurveValue(FPSBodyBowMotion::GripCurves[I]);
    FQuat Q(V[3],V[4],V[5],V[6]);
    if (Q.SizeSquared()>UE_SMALL_NUMBER)
        HeldWeapon->SetRelativeTransform(FTransform(Q.GetNormalized(),FVector(V[0],V[1],V[2]),FVector(BowScale)));
    const bool Drawing=Motion.Action==EUnknownAction::DrawBow && ServerTime()<Motion.Started+Motion.Windup;
    if(!Drawing){if(HeldArrowElement)HeldArrowElement->Clear();if(HeldArrowLight)HeldArrowLight->Clear();}
    FVector Nock=BowBrace;
    if (Drawing)
    {
        const FVector Grip(Anim->GetCurveValue(FPSBodyBowMotion::NockCurves[0]),Anim->GetCurveValue(FPSBodyBowMotion::NockCurves[1]),Anim->GetCurveValue(FPSBodyBowMotion::NockCurves[2]));
        Nock=HeldWeapon->GetComponentTransform().InverseTransformPosition(GetMesh()->GetSocketTransform(TEXT("hand_r")).TransformPosition(Grip));
    }
    FVector Tips[2]={BowTips[0],BowTips[1]};
    if(BowFlex){BowFlex->ApplyStringLoad(Nock,BowBrace,BowFlexDistribution);BowFlex->Tips(Tips[0],Tips[1]);}
    for (int32 I=0; I<2; ++I) if (BowStrings[I])
    {
        const FVector D=Tips[I]-Nock;
        BowStrings[I]->SetRelativeTransform(FTransform(FQuat::FindBetweenNormals(FVector::UpVector,D.GetSafeNormal()),(Tips[I]+Nock)*.5,
            FVector(BowStringRadius/50.f,BowStringRadius/50.f,D.Size()/100.f)));
    }
    if (NockedArrow)
    {
        NockedArrow->SetVisibility(Drawing);
        if (Drawing)
        {
            const FVector Start=HeldWeapon->GetComponentTransform().TransformPosition(Nock);
            const FVector Direction=GetActorForwardVector();
            NockedArrow->SetWorldTransform(ArrowFromNock*FTransform(Direction.Rotation(),Start));
            const auto Kind=EUnknownArrow(Motion.ArrowKind);
            if(Kind>=EUnknownArrow::Fire && Kind<=EUnknownArrow::Lightning)
            {
                if(!HeldArrowElement){HeldArrowElement=NewObject<UElementalArrowVisual>(this);HeldArrowElement->RegisterComponent();}
                const EArrowElement Elements[]={EArrowElement::Fire,EArrowElement::Ice,EArrowElement::Lightning};
                HeldArrowElement->Update(Elements[int32(Kind)-int32(EUnknownArrow::Fire)],Start,Start+Direction*76.f,GetWorld()->GetDeltaSeconds(),true,true,NockedArrow);
            }
            else if(Kind==EUnknownArrow::Illumination)
            {
                if(!HeldArrowLight){HeldArrowLight=NewObject<UIlluminationArrowVisual>(this);HeldArrowLight->RegisterComponent();}
                HeldArrowLight->Update(Start,Start+Direction*76.f,GetWorld()->GetDeltaSeconds(),true);
            }
        }
    }
}
