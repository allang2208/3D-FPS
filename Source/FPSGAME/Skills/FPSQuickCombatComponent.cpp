#include "FPSQuickCombatComponent.h"
#include "LightningHasteSpeed.h"
#include "PlayerSkillPreparation.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelGenericMelee.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowQuickCombatMotion.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/WoodenTorchComponent.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "../Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "../Weapons/Unarmed/UnarmedPunchTuning.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Production/ProductionToolComponent.h"
#include "../Production/WarhammerConicalThrustMotion.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

UFPSQuickCombatComponent::UFPSQuickCombatComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    // 姿态层在 FinalizeBoneTransform 里采样本组件的阶段，必须先于网格求值。
    PrimaryComponentTick.TickGroup=ETickingGroup::TG_PrePhysics;
    ConfigureForClipLength(QuickCombatPistolMotion::DefaultLength);
}

EQuickCombatBashPhase UFPSQuickCombatComponent::PhaseForAge(float Age) const
{
    if(Age<ReleaseEnd)return EQuickCombatBashPhase::Release;
    if(Age<CockEnd)return EQuickCombatBashPhase::Cock;
    if(Age<ContactTime)return EQuickCombatBashPhase::Smash;
    if(Age<FollowEnd)return EQuickCombatBashPhase::Follow;
    return EQuickCombatBashPhase::Recover;
}

void UFPSQuickCombatComponent::BeginPlay()
{
    Super::BeginPlay();
    PlayerSkillAssets::Defer(GetOwner(),TEXT("quickCombat"),FSimpleDelegate::CreateWeakLambda(this,[this]()
    {
    // 挥击音：用户 2026-09-18 指定的 quickhit2.mp3（导入口径见
    // SourceAssets/QuickCombatSwingAudio20260918，44.1kHz/立体声/16bit、FORCE_INLINE）；
    // 2026-09-19 起改为命中确认时播放（ContactHit），挥空不出声。
    SwingSound=PlayerSkillAssets::Resolve<USoundBase>(TEXT("/Game/Audio/QuickCombat20260918/S_QuickCombatSwing.S_QuickCombatSwing"));
    // 命中音：保持与符文剑配重锤共用同一枚钝器音（用户本轮只要求换挥击音时机）。
    ImpactSound=PlayerSkillAssets::Resolve<USoundBase>(TEXT("/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick"));
    // 判定用：一行说清两个音各加载到了什么（"声音没换"类问题先看这行）。
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 音效资产 挥击音=%s 命中音=%s"),
        SwingSound?*SwingSound->GetName():TEXT("未加载"),
        ImpactSound?*ImpactSound->GetName():TEXT("未加载"));
    }));
}

UColdSteelStatusModel* UFPSQuickCombatComponent::Model() const
{ return GetOwner()&&GetOwner()->GetGameInstance()?GetOwner()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr; }

bool UFPSQuickCombatComponent::BeginAction()
{
    auto* Profile=Model();if(!Profile)return false;
    if(IsOccupyingLeftHand())return false;
    // The Pojun pommel strike uses the hammer skill clock. Its ordinary swing
    // penalty belongs to the dao's weapon attacks; haste applies to both skills.
    ActionRate=LightningHaste::ActionSpeed(GetOwner());
    GenericMeleeSerial=0;
    if(Style==EQuickCombatStyle::UnarmedPunch)
    {
        if(GetNetMode()!=NM_Standalone)
        {
            auto* Pawn=Cast<APawn>(GetOwner());
            auto* Net=Pawn?Pawn->GetPlayerState<AColdSteelPlayerState>():nullptr;
            if(!Net)return false;
            GenericMeleeSerial=Net->RequestGenericMeleeStart(Pawn,FString(),ColdSteelGenericMelee::Unarmed,UnarmedPunch::AttackMeta);
            if(!GenericMeleeSerial)return false;
        }
        if(!Profile->SpendStamina(ColdSteelMelee::UnarmedAttackStamina(Profile)))return false;
    }
    else
    {
        if(!Profile->CommitQuickCombatCast(ActionDuration()))return false;
        Profile->TrainQuickCombat(Profile->QuickCombatDefinition().UseExperience);
    }
    ++Serial;ActionAge=0.f;Phase=EQuickCombatBashPhase::Release;
    bContactDone=bKillPending=false;
    ImpactAge=1.f;ImpactStrength=0.f;
    return true;
}

float UFPSQuickCombatComponent::ActionSourceDuration() const
{
    if(UsesWarhammerHeadThrust())
        return AttackEnd+(IsOccupyingLeftHand()&&ImpactStrength>0.f?WarhammerConicalThrust::HitStopSeconds:0.f);
    if(Style==EQuickCombatStyle::Bow)
        return BowQuickCombatMotion::PlaybackSeconds(AttackEnd,ClipLength)
            +(IsOccupyingLeftHand()&&ImpactStrength>0.f?BowQuickCombatMotion::HitStopSeconds:0.f);
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(Player&&Player->bUseASH12&&IsRifleStyle())
        return ContactTime/QuickCombatRifleMotion::ASH12EntryRate
            +(AttackEnd-ContactTime)/QuickCombatRifleMotion::ASH12RecoveryRate
            +(IsOccupyingLeftHand()&&ImpactStrength>0.f?QuickCombatRifleMotion::ASH12HitStopSeconds:0.f);
    return AttackEnd;
}

float UFPSQuickCombatComponent::ActionSourceRemaining() const
{
    if(UsesWarhammerHeadThrust())
        return FMath::Max(0.f,AttackEnd-ActionAge)
            +(ImpactStrength>0.f?FMath::Max(0.f,WarhammerConicalThrust::HitStopSeconds-ImpactAge):0.f);
    if(Style==EQuickCombatStyle::Bow)
        return FMath::Max(0.f,BowQuickCombatMotion::PlaybackSeconds(AttackEnd,ClipLength)
            -BowQuickCombatMotion::PlaybackSeconds(ActionAge,ClipLength))
            +(ImpactStrength>0.f?FMath::Max(0.f,BowQuickCombatMotion::HitStopSeconds-ImpactAge):0.f);
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(Player&&Player->bUseASH12&&IsRifleStyle())
        return FMath::Max(0.f,ContactTime-ActionAge)/QuickCombatRifleMotion::ASH12EntryRate
            +FMath::Max(0.f,AttackEnd-FMath::Max(ContactTime,ActionAge))/QuickCombatRifleMotion::ASH12RecoveryRate
            +(ImpactStrength>0.f?FMath::Max(0.f,QuickCombatRifleMotion::ASH12HitStopSeconds-ImpactAge):0.f);
    return FMath::Max(0.f,AttackEnd-ActionAge);
}

void UFPSQuickCombatComponent::Cancel()
{
    if(Phase!=EQuickCombatBashPhase::None)FinishAction();
    bContactDone=false;ImpactAge=1.f;ImpactStrength=0.f;
}

bool UFPSQuickCombatComponent::IsImpactPaused() const
{
    if(UsesWarhammerHeadThrust())
        return IsOccupyingLeftHand()&&ImpactStrength>0.f&&ImpactAge<WarhammerConicalThrust::HitStopSeconds;
    if(Style==EQuickCombatStyle::Bow)
        return Phase!=EQuickCombatBashPhase::None&&ImpactStrength>0.f
            &&ImpactAge<BowQuickCombatMotion::HitStopSeconds;
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    return Player&&Player->bUseASH12&&IsRifleStyle()
        &&Phase!=EQuickCombatBashPhase::None&&ImpactStrength>0.f
        &&ImpactAge<QuickCombatRifleMotion::ASH12HitStopSeconds;
}

void UFPSQuickCombatComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    // The character advances ASH/SVCH/M24 before sampling the pose and camera. Never
    // advance twice or let the wall-clock state finish through a hit stop.
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(Style==EQuickCombatStyle::UnarmedPunch&&Player)return; // advanced once before the character camera
    if(Style==EQuickCombatStyle::SpellbookPush&&Player)return;
    if(Style==EQuickCombatStyle::Warhammer&&Player&&IsOccupyingLeftHand())return;
    if(Player&&Player->HasOffhandPistol()&&(Style==EQuickCombatStyle::DualPistol||Style==EQuickCombatStyle::StaffOffhandPistol))return;
    if((Style==EQuickCombatStyle::StaffPunch||Style==EQuickCombatStyle::TorchStrike)&&Player)return; // advanced before camera sampling
    if(Style==EQuickCombatStyle::Bow&&IsOccupyingLeftHand())return;
    if(Player&&(Player->IsM24Weapon()||Player->bUseASH12||SVCHWeaponAssets::Matches(Player->AKMViewmodel))&&IsRifleStyle()&&IsOccupyingLeftHand())return;
    AdvanceAction(Delta);
}

void UFPSQuickCombatComponent::AdvanceAction(float Delta)
{
    Delta*=ActionRate;
    const float PreviousImpactAge=ImpactAge;
    ImpactAge=FMath::Min(1.f+QuickCombatPistolMotion::ImpactSpan,ImpactAge+Delta);
    if(Phase==EQuickCombatBashPhase::None)return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    // 单双持切换、换枪或死亡结束本次动作，体力不退还，保留已发生的修炼。
    const auto* Health=Player?Player->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Bow=Player?Player->FindComponentByClass<UBowWeaponComponent>():nullptr;
    const auto* Staff=Player?Player->FindComponentByClass<UStaffWeaponComponent>():nullptr;
    const auto* Dual=Player?Player->FindComponentByClass<UPistolDualWieldComponent>():nullptr;
    const auto* Hands=Player?Player->FindComponentByClass<UFPSUnarmedIdleComponent>():nullptr;
    const auto* Book=Player?Player->FindComponentByClass<USpellbookComponent>():nullptr;
    const bool bStaff=Style==EQuickCombatStyle::StaffPunch||Style==EQuickCombatStyle::StaffOffhandPistol;
    const bool bTorch=Style==EQuickCombatStyle::TorchStrike;
    const auto* Torch=bTorch&&Player?Player->FindComponentByClass<UWoodenTorchComponent>():nullptr;
    const bool bUnarmed=Style==EQuickCombatStyle::UnarmedPunch;
    const bool bBook=Style==EQuickCombatStyle::SpellbookPush;
    const bool bWarhammer=Style==EQuickCombatStyle::Warhammer;
    const auto* Tool=bWarhammer&&Player?Player->FindComponentByClass<UProductionToolComponent>():nullptr;
    const bool bWeaponMatches=Player&&(bWarhammer
        ?(Tool&&Tool->IsWarhammerEquipped()&&!Player->IsTraversing()&&!Player->IsDoorPushActive()
            &&!AFPSGAMEPlayerController::BlocksActionContinuation(Cast<APlayerController>(Player->GetController())))
        :bBook
        ?(Book&&Book->OwnsLeftHand()&&!Player->IsDoorPushActive()
            &&!AFPSGAMEPlayerController::BlocksActionContinuation(Cast<APlayerController>(Player->GetController())))
        :bUnarmed
        ?(Hands&&Hands->IsEquipped()&&!Player->IsTraversing()
            &&!AFPSGAMEPlayerController::BlocksActionContinuation(Cast<APlayerController>(Player->GetController())))
        :bStaff||bTorch
        ?(((bTorch&&Torch&&Torch->UsesQuickAttack()&&Staff&&Staff->IsTorchQuickStrike()&&!Player->IsReloading())
            ||(bStaff&&Staff&&Staff->HasMeleeMoveset()&&(Style==EQuickCombatStyle::StaffPunch?!Player->HasOffhandPistol():Dual&&Dual->IsOffhandOnly()))
            ||(Style==EQuickCombatStyle::StaffOffhandPistol&&Player->IsLoneLeftHandRig()))
            &&!Player->IsTraversing()&&!AFPSGAMEPlayerController::BlocksActionContinuation(Cast<APlayerController>(Player->GetController())))
        :Style==EQuickCombatStyle::Bow
        ?(Bow&&Bow->IsEquipped())
        :Style==EQuickCombatStyle::DualPistol
        ?Player->IsDualWieldingPistols()
        :(!IsPistolStyle()?!Player->IsPistolWeapon()
            :(Player->IsPistolWeapon()&&!Player->IsDualWieldingPistols())));
    if(!Player||!bWeaponMatches||(Health&&Health->IsDead())){Cancel();return;}
    const bool bASH12=Player->bUseASH12&&IsRifleStyle();
    if(Style==EQuickCombatStyle::Bow)
    {
        using namespace BowQuickCombatMotion;
        float Remaining=Delta;
        if(!bContactDone)
        {
            const float UntilContact=FMath::Max(0.f,PlaybackSeconds(ContactTime,ClipLength)
                -PlaybackSeconds(ActionAge,ClipLength));
            if(Remaining<UntilContact)
            {
                ActionAge=SourceSeconds(PlaybackSeconds(ActionAge,ClipLength)+Remaining,ClipLength);
                Remaining=0.f;
            }
            else
            {
                Remaining-=UntilContact;
                ActionAge=ContactTime;
                Phase=PhaseForAge(ActionAge);
                bContactDone=true;
                ContactHit();
                // Cross the exact contact once, then spend only the real time
                // left in this frame on hit stop and recovery. Misses never pause.
                ImpactAge=Remaining;
                if(ImpactStrength>0.f)Remaining=FMath::Max(0.f,Remaining-HitStopSeconds);
            }
        }
        else if(ImpactStrength>0.f)
            Remaining-=FMath::Clamp(HitStopSeconds-PreviousImpactAge,0.f,Remaining);
        if(Remaining>0.f)
            ActionAge=SourceSeconds(PlaybackSeconds(ActionAge,ClipLength)+Remaining,ClipLength);
        Phase=PhaseForAge(ActionAge);
    }
    else if(bASH12)
    {
        using namespace QuickCombatRifleMotion;
        float Remaining=Delta;
        if(!bContactDone)
        {
            const float UntilContact=FMath::Max(0.f,ContactTime-ActionAge)/ASH12EntryRate;
            if(Remaining<UntilContact)
            {
                ActionAge+=Remaining*ASH12EntryRate;
                Remaining=0.f;
            }
            else
            {
                Remaining-=UntilContact;
                ActionAge=ContactTime;
                Phase=PhaseForAge(ActionAge);
                bContactDone=true;
                ContactHit();
                // Account for the part of this frame after the impact, including
                // its pause. Every query shakes, but a miss consumes no stop.
                ImpactAge=Remaining;
                if(ImpactStrength>0.f)
                {
                    Remaining=FMath::Max(0.f,Remaining-ASH12HitStopSeconds);
                }
            }
        }
        else if(ImpactStrength>0.f)
            Remaining-=FMath::Clamp(ASH12HitStopSeconds-PreviousImpactAge,0.f,Remaining);
        ActionAge+=Remaining*ASH12RecoveryRate;
        Phase=PhaseForAge(ActionAge);
    }
    else if(UsesWarhammerHeadThrust())
    {
        float Remaining=Delta;
        if(ActionAge<CockEnd&&ActionAge+Remaining>=CockEnd&&ImpactSound)
            UGameplayStatics::PlaySound2D(this,ImpactSound,1.f,1.f);
        if(!bContactDone)
        {
            const float UntilContact=FMath::Max(0.f,ContactTime-ActionAge);
            if(Remaining<UntilContact)
            {
                ActionAge+=Remaining;
                Remaining=0.f;
            }
            else
            {
                Remaining-=UntilContact;
                ActionAge=ContactTime;Phase=PhaseForAge(ActionAge);
                bContactDone=true;ContactHit();
                // Only real contact resists the thrust. Consume the remaining
                // frame in the pause before recovery, including across a hitch.
                ImpactAge=Remaining;
                if(ImpactStrength>0.f)Remaining=FMath::Max(0.f,Remaining-WarhammerConicalThrust::HitStopSeconds);
            }
        }
        else if(ImpactStrength>0.f)
            Remaining-=FMath::Clamp(WarhammerConicalThrust::HitStopSeconds-PreviousImpactAge,0.f,Remaining);
        ActionAge+=Remaining;
        Phase=PhaseForAge(ActionAge);
    }
    else if(bStaff||bTorch||bUnarmed||bBook||bWarhammer)
    {
        const float NextAge=ActionAge+Delta;
        // Match the sword pommel quick strike: one shared blunt cue on release,
        // including a miss. Crossing the real-time windup boundary also handles
        // a frame that advances past both release and contact without a timer.
        if(bWarhammer&&ActionAge<CockEnd&&NextAge>=CockEnd&&ImpactSound)
            UGameplayStatics::PlaySound2D(this,ImpactSound,1.f,1.f);
        if(!bContactDone&&NextAge>=ContactTime)
        {
            // Contact reads the same authored frame even when a hitch crosses it.
            ActionAge=ContactTime;Phase=PhaseForAge(ActionAge);
            bContactDone=true;ContactHit();
        }
        ActionAge=NextAge;Phase=PhaseForAge(ActionAge);
    }
    else
    {
        ActionAge+=Delta;
        Phase=PhaseForAge(ActionAge);
        if(!bContactDone&&ActionAge>=ContactTime){bContactDone=true;ContactHit();}
    }
    if(ActionAge>=AttackEnd)FinishAction();
    else if(!bUnarmed)if(auto* Profile=Model())Profile->UpdateQuickCombatAction(ActionRemaining(),ActionDuration());
}

void UFPSQuickCombatComponent::FinishAction()
{
    if(Style==EQuickCombatStyle::TorchStrike)
        if(auto* Staff=GetOwner()->FindComponentByClass<UStaffWeaponComponent>())Staff->EndTorchQuickStrike();
    if(Style!=EQuickCombatStyle::UnarmedPunch)if(auto* Profile=Model())
    {
        // Complete recovery unlocks the next strike immediately.
        Profile->FinishQuickCombatCast();
        if(bKillPending)Profile->TrainQuickCombat(Profile->QuickCombatDefinition().KillExperience);
    }
    bKillPending=false;
    Phase=EQuickCombatBashPhase::None;ActionAge=0.f;
}

void UFPSQuickCombatComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    // 销毁路径同样解除动作占用。
    if(Phase!=EQuickCombatBashPhase::None)FinishAction();
    Super::EndPlay(Reason);
}

float UFPSQuickCombatComponent::ActionDuration() const{return ActionSourceDuration()/ActionRate;}
float UFPSQuickCombatComponent::ActionRemaining() const{return ActionSourceRemaining()/ActionRate;}
