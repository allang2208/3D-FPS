#include "ProductionToolComponent.h"
#include "RuneboundHammerTuning.h"
#include "FinalTollHeavyMotion.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "WarhammerAudioPaths.h"

bool RuneboundHammer::HasFinalToll(const FColdSteelItem& Item)
{
    if(Item.Definition!=Definition)return false;
    const auto Data=ColdSteelItemData::Read(Item.Data);
    const TSharedPtr<FJsonObject>* Parts=nullptr;FString Head;
    return Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts)&&
        (*Parts)->TryGetStringField(TEXT("hammer_heads"),Head)&&Head==FinalTollHead;
}

bool UProductionToolComponent::UsesFinalTollHeavy() const
{return bFinalTollHead&&bBluntHeavy&&!bBluntSprintAttack;}

void UProductionToolComponent::AdvanceFinalTollHeavy(float Delta)
{
    const float Before=Elapsed,Next=FMath::Min(FinalTollHeavy::Duration,Elapsed+Delta*FinalTollActionRate);
    for(int32 Cut=0;Cut<2;++Cut)
    {
        const float Contact=Cut==0?FinalTollHeavy::FirstContact:FinalTollHeavy::SecondContact;
        if((FinalTollStrikes&(1<<Cut))||Before>Contact||Next<Contact)continue;
        FinalTollStrikes|=1<<Cut;bContacted=true;
        if(Cut==1)
        {
            if(auto* Sound=Cast<USoundBase>(WarhammerAudioPaths::Uppercut.ResolveObject()))
                UGameplayStatics::PlaySound2D(this,Sound,.72f,1.04f,.25f);
            if(GetNetMode()==NM_Standalone)
            {
                const auto* Profile=ColdSteelAuthority::ForPawn(Character.Get());
                if(const auto* Item=Profile?Profile->ActiveProductionTool():nullptr)
                    AxeStrike.MasteryAttackSerial=ColdSteelSkills::Snapshot(Character.Get(),Item).MasteryAttackSerial;
                FinalTollHeavySerial=AxeStrike.MasteryAttackSerial;
            }
        }
        if(GetNetMode()==NM_Standalone)bHitConfirmed=ResolveBluntContact()||bHitConfirmed;
        if(Elapsed<0.f||!UsesFinalTollHeavy())return;
    }
    Elapsed=Next;
    if(Elapsed>=FinalTollHeavy::Duration)FinishUse();
}

float UProductionToolComponent::FinalTollToughnessMultiplier(const FColdSteelSkillShot& Shot,AActor* Target) const
{
    if(!FinalTollHeavySerial||Shot.MasteryAttackSerial!=FinalTollHeavySerial||RuneboundClock()>FinalTollCommitUntil)return 1.f;
    const auto* Profile=ColdSteelAuthority::ForPawn(Character.Get());
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!Item||Shot.ItemInstance!=Item->InstanceId||!RuneboundHammer::HasFinalToll(*Item)||!IsRuneboundAwakened(*Item))return 1.f;
    for(const auto& Seal:FinalTollMarks)
        if(Seal.Target.Get()==Target&&Seal.Expires>RuneboundClock()&&Seal.Serial!=Shot.MasteryAttackSerial)return 2.f;
    return 1.f;
}

void UProductionToolComponent::RecordFinalTollHit(const FColdSteelSkillShot& Shot,const FHitResult& Hit)
{
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());auto* Target=Hit.GetActor();
    if(!Pawn||!Pawn->HasAuthority()||!Target||!FinalTollHeavySerial||
        Shot.MasteryAttackSerial!=FinalTollHeavySerial||RuneboundClock()>FinalTollCommitUntil)return;
    const auto* Profile=ColdSteelAuthority::ForPawn(Pawn);
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    if(!Item||Shot.ItemInstance!=Item->InstanceId||!RuneboundHammer::HasFinalToll(*Item)||!IsRuneboundAwakened(*Item))return;
    if(FinalTollRecentHits.ContainsByPredicate([&](const FFinalTollReceipt& R){return R.Target.Get()==Target&&R.Serial==Shot.MasteryAttackSerial;}))return;
    if(FinalTollRecentHits.Num()>=64)FinalTollRecentHits.RemoveAt(0);
    FinalTollRecentHits.Add({Target,Shot.MasteryAttackSerial});
    if(const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();Combat&&Combat->IsDead())
    {if(FinalTollMarks.RemoveAll([&](const FFinalTollMark& Mark){return Mark.Target.Get()==Target;}))PublishFinalTollSeals();return;}
    const double Now=RuneboundClock();
    FinalTollMarks.RemoveAll([&](const FFinalTollMark& Mark){return !Mark.Target.IsValid()||Mark.Expires<=Now;});
    auto* Mark=FinalTollMarks.FindByPredicate([&](const FFinalTollMark& M){return M.Target.Get()==Target;});
    if(Mark&&Mark->Serial==Shot.MasteryAttackSerial)return;
    const bool Complete=Mark!=nullptr;
    if(Complete)FinalTollMarks.RemoveAll([&](const FFinalTollMark& M){return M.Target.Get()==Target;});
    else
    {
        if(FinalTollMarks.Num()>=32)FinalTollMarks.RemoveAt(0);
        FFinalTollMark New;New.Target=Target;New.Serial=Shot.MasteryAttackSerial;New.Started=Now;New.Expires=Now+6.;
        New.LocalPoint=Hit.ImpactPoint-Target->GetActorLocation();FinalTollMarks.Add(New);
    }
    PublishFinalTollSeals();
    if(!Complete)return;
    MulticastFinalTollSeal(RuneboundInstance,Target,Hit.ImpactPoint,Now,true,Shot.MasteryAttackSerial);
    const float Damage=Profile->Derived(TEXT("matk"))*3.5f*(RuneboundHammer::HasDestructionRune(*Item)?2.f:1.f);
    const float Penetration=Shot.MagicPenetration;
    const float Bonus=FMath::Max(0.,(1.+Profile->SetEffect(TEXT("magicDamage")))*ColdSteelMelee::EquippedModifiers(Profile).MagicDamage)-1.;
    const FVector Origin=Hit.ImpactPoint;const TWeakObjectPtr<AActor> Victim=Target;
    GetWorld()->GetTimerManager().SetTimerForNextTick(FTimerDelegate::CreateWeakLambda(this,[this,Victim,Damage,Penetration,Bonus,Origin]()
    {
        auto* Source=Cast<AFPSGAMECharacter>(GetOwner());auto* Enemy=Victim.Get();
        if(!Source||!Source->HasAuthority()||!UFPSMeleeLightningComponent::IsEnemy(Enemy,Source))return;
        CombatFormulaRuntime::MagicHit Context;Context.Penetration=Penetration;Context.DamageBonus=Bonus;
        TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(CombatFormulaRuntime::ActiveMagicHit,&Context);
        FHitResult Contact(Enemy,Cast<UPrimitiveComponent>(Enemy->GetRootComponent()),Origin,FVector::UpVector);
        Contact.ImpactPoint=Origin;Contact.TraceStart=Source->GetActorLocation();Contact.bBlockingHit=true;
        auto Apply=[&](){return UGameplayStatics::ApplyPointDamage(Enemy,Damage,(Origin-Contact.TraceStart).GetSafeNormal(),Contact,Source->GetController(),Source,UStatusMagicDamage::StaticClass());};
        if(auto* Combat=Enemy->FindComponentByClass<UMonsterCombatComponent>())Combat->ApplyHitWithToughnessScale(0.f,Apply);else Apply();
    }));
}

void UProductionToolComponent::MulticastFinalTollSeal_Implementation(const FString& Instance,AActor* Target,FVector_NetQuantize Point,double At,bool Complete,uint32 Serial)
{
    if(GetNetMode()==NM_DedicatedServer||Instance!=RuneboundInstance||!Target||!Complete||RuneboundClock()-At>=1.6)return;
    const double Now=RuneboundClock();
    FinalTollVisualMarks.RemoveAll([&](const FFinalTollVisualMark& M){return !M.Target.IsValid()||M.Expires<=Now||M.Target.Get()==Target;});
    if(FinalTollVisualMarks.Num()>=16)FinalTollVisualMarks.RemoveAt(0);
    FFinalTollVisualMark Mark;Mark.Target=Target;Mark.Expires=At+(Complete?1.6:6.);Mark.Started=At;
    Mark.LocalPoint=FVector(Point)-Target->GetActorLocation();Mark.Complete=Complete;FinalTollVisualMarks.Add(Mark);
    if(Complete)
    {
        MulticastRuneboundImpact_Implementation(Instance,Serial,At,false);
        if(auto* Burst=RuneboundHitBursts.FindByPredicate([&](const FRuneboundHitBurst& B){return B.AttackSerial==Serial;}))
        {Burst->Origin=Point;Burst->bHasOrigin=true;Burst->bFinalToll=true;}
    }
}

void UProductionToolComponent::PublishFinalTollSeals()
{
    FinalTollSealState.Instance=RuneboundInstance;FinalTollSealState.Marks.Reset();
    for(const auto& Mark:FinalTollMarks)
    {
        auto& State=FinalTollSealState.Marks.AddDefaulted_GetRef();
        State.Target=Mark.Target.Get();State.LocalPoint=Mark.LocalPoint;State.Started=Mark.Started;State.Expires=Mark.Expires;
    }
    bFinalTollSealsDirty=true;
    if(auto* Owner=GetOwner())Owner->ForceNetUpdate();
}

void UProductionToolComponent::OnRep_FinalTollSeals(){bFinalTollSealsDirty=true;}

void UProductionToolComponent::ReconcileFinalTollSeals(bool Active)
{
    if(!Active){FinalTollVisualMarks.Reset();bFinalTollSealsDirty=true;return;}
    if(!bFinalTollSealsDirty||FinalTollSealState.Instance!=RuneboundInstance)return;
    const double Now=RuneboundClock();bool Unmapped=false;
    FinalTollVisualMarks.RemoveAll([&](const FFinalTollVisualMark& Mark){return !Mark.Complete||!Mark.Target.IsValid()||Mark.Expires<=Now;});
    for(const auto& State:FinalTollSealState.Marks)
    {
        if(State.Expires<=Now)continue;
        if(!State.Target){Unmapped=true;continue;}
        // A completion RPC can arrive before the property which removes its seal.
        if(FinalTollVisualMarks.ContainsByPredicate([&](const FFinalTollVisualMark& M){return M.Target.Get()==State.Target&&M.Complete&&M.Started>=State.Started;}))continue;
        if(FinalTollVisualMarks.Num()>=16)break;
        FFinalTollVisualMark Mark;Mark.Target=State.Target;Mark.LocalPoint=State.LocalPoint;
        Mark.Started=State.Started;Mark.Expires=State.Expires;FinalTollVisualMarks.Add(Mark);
    }
    bFinalTollSealsDirty=Unmapped;
}
