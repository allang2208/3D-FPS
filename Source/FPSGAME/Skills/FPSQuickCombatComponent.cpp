#include "FPSQuickCombatComponent.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "QuickCombatImpactShake.h"
#include "ColdSteelSkillRules.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "FPSCastingMeshComponent.h"
#include "../Weapons/FPSGunplayAnimInstance.h"
#include "../Weapons/MeleeSmallTargetQuery.h"
#include "../Weapons/PistolDualWieldComponent.h"
#include "../Weapons/DualPistolQuickCombatMotion.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowQuickCombatMotion.h"
#include "../Weapons/Staff/StaffWeaponComponent.h"
#include "../Weapons/Staff/StaffQuickCombatMotion.h"
#include "../Weapons/Spellbook/SpellbookComponent.h"
#include "../Weapons/Spellbook/SpellbookAuthoredStrike.h"
#include "../Weapons/Unarmed/FPSUnarmedIdleComponent.h"
#include "../Weapons/Unarmed/UnarmedPunchTuning.h"
#include "../Weapons/MeleeWeaponStats.h"
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

void UFPSQuickCombatComponent::ConfigureForClipLength(float Length,bool bDualPistol)
{
    using namespace QuickCombatPistolMotion;
    Style=bDualPistol?EQuickCombatStyle::DualPistol:EQuickCombatStyle::Pistol;
    ClipLength=FMath::Max(0.05f,Length);
    ReleaseEnd=ClipLength*ReleaseFraction;
    CockEnd=ClipLength*CockFraction;
    ContactTime=ClipLength*ContactFraction;
    FollowEnd=ClipLength*FollowFraction;
    if(bDualPistol)
    {
        ReleaseEnd=ClipLength*DualPistolQuickCombatMotion::ReleaseFraction;
        CockEnd=ClipLength*DualPistolQuickCombatMotion::CockFraction;
        ContactTime=ClipLength*DualPistolQuickCombatMotion::ContactFraction;
        FollowEnd=ClipLength*DualPistolQuickCombatMotion::FollowFraction;
    }
    AttackEnd=ClipLength;
}

void UFPSQuickCombatComponent::ConfigureForRifle(float Length,bool bM4Reference)
{
    using namespace QuickCombatRifleMotion;
    Style=bM4Reference?EQuickCombatStyle::M4ReferenceRifle:EQuickCombatStyle::Rifle;
    ClipLength=FMath::Max(0.05f,Length);
    ReleaseEnd=ClipLength*(bM4Reference?M4ReferenceReleaseFraction:ReleaseFraction);
    CockEnd=ClipLength*(bM4Reference?M4ReferenceCockFraction:CockFraction);
    ContactTime=ClipLength*(bM4Reference?M4ReferenceContactFraction:ContactFraction);
    FollowEnd=ClipLength*(bM4Reference?M4ReferenceFollowFraction:FollowFraction);
    AttackEnd=ClipLength;
    // 步枪是双手持枪的整枪动作，命中探针改用枪身（见 ContactHit），
    // 其余结算口径与手枪版完全一致：同一体力、修炼与击退公式。
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 步枪砸击时钟 总长=%.3f 接触=%.3f"),AttackEnd,ContactTime);
}

void UFPSQuickCombatComponent::ConfigureForBow(float Length)
{
    Style=EQuickCombatStyle::Bow;
    ClipLength=FMath::Max(.05f,Length);
    const float Scale=ClipLength/BowQuickCombatMotion::Length;
    ReleaseEnd=BowQuickCombatMotion::Grip*Scale;
    CockEnd=BowQuickCombatMotion::Cock*Scale;
    ContactTime=BowQuickCombatMotion::Contact*Scale;
    FollowEnd=BowQuickCombatMotion::Follow*Scale;
    AttackEnd=ClipLength;
}

void UFPSQuickCombatComponent::ConfigureForStaffPunch()
{
    Style=EQuickCombatStyle::StaffPunch;
    ClipLength=AttackEnd=StaffQuickCombatMotion::Length;
    ReleaseEnd=StaffQuickCombatMotion::Release;
    CockEnd=StaffQuickCombatMotion::Cock;
    ContactTime=StaffQuickCombatMotion::Contact;
    FollowEnd=StaffQuickCombatMotion::Follow;
}

void UFPSQuickCombatComponent::ConfigureForStaffOffhandPistol(float Length)
{
    ConfigureForClipLength(Length,true);
    Style=EQuickCombatStyle::StaffOffhandPistol;
}

void UFPSQuickCombatComponent::ConfigureForSpellbookPush()
{
    Style=EQuickCombatStyle::SpellbookPush;
    ClipLength=AttackEnd=SpellbookAuthoredStrike::Length;
    ReleaseEnd=SpellbookAuthoredStrike::Release;
    CockEnd=SpellbookAuthoredStrike::Cock;
    ContactTime=SpellbookAuthoredStrike::Contact;
    FollowEnd=SpellbookAuthoredStrike::Follow;
}

void UFPSQuickCombatComponent::ConfigureForUnarmedPunch()
{
    ConfigureForStaffPunch();
    Style=EQuickCombatStyle::UnarmedPunch;
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
    // 挥击音：用户 2026-09-18 指定的 quickhit2.mp3（导入口径见
    // SourceAssets/QuickCombatSwingAudio20260918，44.1kHz/立体声/16bit、FORCE_INLINE）；
    // 2026-09-19 起改为命中确认时播放（ContactHit），挥空不出声。
    SwingSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Audio/QuickCombat20260918/S_QuickCombatSwing.S_QuickCombatSwing"));
    // 命中音：保持与符文剑配重锤共用同一枚钝器音（用户本轮只要求换挥击音时机）。
    ImpactSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick"));
    // 判定用：一行说清两个音各加载到了什么（"声音没换"类问题先看这行）。
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 音效资产 挥击音=%s 命中音=%s"),
        SwingSound?*SwingSound->GetName():TEXT("未加载"),
        ImpactSound?*ImpactSound->GetName():TEXT("未加载"));
}

UColdSteelStatusModel* UFPSQuickCombatComponent::Model() const
{ return GetOwner()&&GetOwner()->GetGameInstance()?GetOwner()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr; }

bool UFPSQuickCombatComponent::BeginAction()
{
    auto* Profile=Model();if(!Profile)return false;
    if(IsOccupyingLeftHand())return false;
    // Start the bar with the real playback duration, including weapon-specific rates.
    if(Style==EQuickCombatStyle::UnarmedPunch)
    {
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

float UFPSQuickCombatComponent::ActionDuration() const
{
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

float UFPSQuickCombatComponent::ActionRemaining() const
{
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
    if(Style==EQuickCombatStyle::Bow)
        return Phase!=EQuickCombatBashPhase::None&&ImpactStrength>0.f
            &&ImpactAge<BowQuickCombatMotion::HitStopSeconds;
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    return Player&&Player->bUseASH12&&IsRifleStyle()
        &&Phase!=EQuickCombatBashPhase::None&&ImpactStrength>0.f
        &&ImpactAge<QuickCombatRifleMotion::ASH12HitStopSeconds;
}

float UFPSQuickCombatComponent::PhaseFraction() const
{
    float Begin=0.f,Span=1.f;
    switch(Phase)
    {
    case EQuickCombatBashPhase::Release:Begin=0.f;Span=ReleaseEnd;break;
    case EQuickCombatBashPhase::Cock:Begin=ReleaseEnd;Span=CockEnd-ReleaseEnd;break;
    case EQuickCombatBashPhase::Smash:Begin=CockEnd;Span=ContactTime-CockEnd;break;
    case EQuickCombatBashPhase::Follow:Begin=ContactTime;Span=FollowEnd-ContactTime;break;
    case EQuickCombatBashPhase::Recover:Begin=FollowEnd;Span=AttackEnd-FollowEnd;break;
    default:return 0.f;
    }
    return FMath::Clamp((ActionAge-Begin)/FMath::Max(.01f,Span),0.f,1.f);
}

float UFPSQuickCombatComponent::LayerWeight() const
{
    if(Phase!=EQuickCombatBashPhase::Recover)return 1.f;
    const float T=PhaseFraction();
    return 1.f-T*T*(3.f-2.f*T);   // 回握段把姿态层交还给动画
}

void UFPSQuickCombatComponent::GetCameraMotion(FVector& Location,FRotator& Rotation) const
{
    using namespace QuickCombatPistolMotion;
    Location=FVector::ZeroVector;Rotation=FRotator::ZeroRotator;
    // The bow shove shares the impact timing, with a smaller axial kick and
    // restrained lateral motion. Apply the same gain to the residual tail.
    const auto AddImpact=[&]()
    {
        if(!bContactDone)return;
        FVector ImpactLocation=FVector::ZeroVector;
        FRotator ImpactRotation=FRotator::ZeroRotator;
        const float ShakeAge=Style==EQuickCombatStyle::Bow
            ?ImpactAge*BowQuickCombatMotion::ImpactTimeScale:ImpactAge;
        QuickCombatImpactShake::Add(ShakeAge,ImpactLocation,ImpactRotation);
        if(Style==EQuickCombatStyle::Bow)
        {
            ImpactLocation*=FVector(BowQuickCombatMotion::AxialImpactScale,.16f,.25f);
            ImpactRotation.Pitch*=BowQuickCombatMotion::PitchImpactScale;
            ImpactRotation.Yaw*=.16f;
            ImpactRotation.Roll*=.16f;
        }
        Location+=ImpactLocation;Rotation+=ImpactRotation;
    };
    if(Phase==EQuickCombatBashPhase::None)
    {
        AddImpact();
        return;
    }
    if(Style==EQuickCombatStyle::StaffPunch||Style==EQuickCombatStyle::UnarmedPunch||Style==EQuickCombatStyle::SpellbookPush)
    {
        const float T=PhaseFraction(),K=FMath::SmoothStep(0.f,1.f,T);
        switch(Phase)
        {
        case EQuickCombatBashPhase::Release:
            Location=FVector(-.15f,-.1f,.12f)*K;Rotation=FRotator(.1f,.15f,.12f)*K;break;
        case EQuickCombatBashPhase::Cock:
            Location=FMath::Lerp(FVector(-.15f,-.1f,.12f),FVector(-.65f,-.2f,.2f),K);
            Rotation=FMath::Lerp(FRotator(.1f,.15f,.12f),FRotator(.35f,.4f,.3f),K);break;
        case EQuickCombatBashPhase::Smash:
            Location=FMath::Lerp(FVector(-.65f,-.2f,.2f),FVector(2.6f,.35f,-.35f),T*T);
            Rotation=FMath::Lerp(FRotator(.35f,.4f,.3f),FRotator(-.8f,-.9f,-.4f),T*T);break;
        case EQuickCombatBashPhase::Follow:
            Location=FMath::Lerp(FVector(2.6f,.35f,-.35f),FVector(.25f,.1f,-.1f),K);
            Rotation=FMath::Lerp(FRotator(-.8f,-.9f,-.4f),FRotator(-.15f,-.15f,-.1f),K);break;
        default:
            Location=FVector(.25f,.1f,-.1f)*(1.f-K);Rotation=FRotator(-.15f,-.15f,-.1f)*(1.f-K);break;
        }
        if(Style==EQuickCombatStyle::UnarmedPunch)
            if(const auto* Hands=GetOwner()->FindComponentByClass<UFPSUnarmedIdleComponent>();Hands&&Hands->GetPunchSide()==1)
            {Location.Y=-Location.Y;Rotation.Yaw=-Rotation.Yaw;Rotation.Roll=-Rotation.Roll;}
        if(Style==EQuickCombatStyle::SpellbookPush)
        {
            Location*=FVector(.65f,.2f,.4f);
            Rotation.Pitch*=.6f;Rotation.Yaw*=.2f;Rotation.Roll*=.2f;
        }
        AddImpact();return;
    }
    if(Style==EQuickCombatStyle::Bow)
    {
        // Short backward loading, a straight forward drive, then recoil.
        const float T=PhaseFraction();
        const float K=FMath::SmoothStep(0.f,1.f,T);
        switch(Phase)
        {
        case EQuickCombatBashPhase::Release:
            Location=FVector(-.3f,0.f,.2f)*K;
            Rotation=FRotator(.2f,0.f,0.f)*K;break;
        case EQuickCombatBashPhase::Cock:
            Location=FMath::Lerp(FVector(-.3f,0.f,.2f),FVector(-1.2f,0.f,.35f),K);
            Rotation=FMath::Lerp(FRotator(.2f,0.f,0.f),FRotator(.65f,0.f,0.f),K);break;
        case EQuickCombatBashPhase::Smash:
            Location=FMath::Lerp(FVector(-1.2f,0.f,.35f),FVector(4.2f,0.f,-.25f),T*T);
            Rotation=FMath::Lerp(FRotator(.65f,0.f,0.f),FRotator(-1.5f,0.f,0.f),T*T);break;
        case EQuickCombatBashPhase::Follow:
            Location=FMath::Lerp(FVector(4.2f,0.f,-.25f),FVector(.45f,0.f,-.1f),K);
            Rotation=FMath::Lerp(FRotator(-1.5f,0.f,0.f),FRotator(-.3f,0.f,0.f),K);break;
        default:
            Location=FVector(.45f,0.f,-.1f)*(1.f-K);
            Rotation=FRotator(-.3f,0.f,0.f)*(1.f-K);break;
        }
        AddImpact();
        return;
    }
    if(Style==EQuickCombatStyle::DualPistol||Style==EQuickCombatStyle::StaffOffhandPistol)
    {
        // Follow the lateral whip, leaving the gun roll to the authored bones.
        // The sign follows the same accepted action as the contact probe.
        const float Sign=Style==EQuickCombatStyle::StaffOffhandPistol?-1.f:DualPistolQuickCombatMotion::StrikingHand(Serial)==0?1.f:-1.f;
        const float U=ActionAge/FMath::Max(ClipLength,.001f);
        const float Contact=DualPistolQuickCombatMotion::ContactFraction;
        const float Follow=DualPistolQuickCombatMotion::FollowFraction;
        if(U<Contact)
        {
            const float T=FMath::SmoothStep(0.f,1.f,U/Contact);
            Location=FVector(1.2f,-.5f*Sign,-.35f)*T;
            Rotation=FRotator(-.55f,-1.1f*Sign,-.85f*Sign)*T;
        }
        else if(U<Follow)
        {
            const float T=FMath::SmoothStep(0.f,1.f,(U-Contact)/(Follow-Contact));
            Location=FMath::Lerp(FVector(1.2f,-.5f*Sign,-.35f),FVector(.2f,.35f*Sign,-.2f),T);
            Rotation=FMath::Lerp(FRotator(-.55f,-1.1f*Sign,-.85f*Sign),FRotator(-.2f,.55f*Sign,.4f*Sign),T);
        }
        else
        {
            const float Weight=1.f-FMath::SmoothStep(0.f,1.f,(U-Follow)/(.72f-Follow));
            Location=FVector(.2f,.35f*Sign,-.2f)*Weight;
            Rotation=FRotator(-.2f,.55f*Sign,.4f*Sign)*Weight;
        }
        if(bContactDone)QuickCombatImpactShake::Add(ImpactAge,Location,Rotation);
        return;
    }
    // 步枪的整枪抬升与下扫使用更大的动作镜头幅度；判定冲量统一。
    const bool bRifle=!IsPistolStyle();
    const float Shape=bRifle?QuickCombatRifleMotion::RifleCameraShapeScale:1.f;
    const float Strength=bRifle?QuickCombatRifleMotion::RifleStockCameraStrength:PistolBashCameraStrength;
    // 镜头语言分两层（与剑版同一合同）：
    // ① 动作镜头：随枪蓄势微抬 → 下砸压头前送 → 跟随回位（动作本体在作者源 clip 里，
    //    这里只做镜头，幅度按已接受的配重锤量级给）。
    // ② 判定冲量：伤害查询当帧立即强震一次，随后反向回弹；命中停顿仍单独确认。
    const float T=PhaseFraction();
    if(Phase==EQuickCombatBashPhase::Release)
    {
        Location=FVector(-0.4f,0.2f,0.5f)*EaseOut(T);Rotation=FRotator(0.4f,0.f,-0.3f)*EaseOut(T);
    }
    else if(Phase==EQuickCombatBashPhase::Cock)
    {
        const float K=FMath::SmoothStep(0.f,1.f,T);
        Location=FMath::Lerp(FVector(-0.4f,0.2f,0.5f),FVector(-1.4f,0.5f,1.6f),K);
        Rotation=FMath::Lerp(FRotator(0.4f,0.f,-0.3f),FRotator(1.3f,0.f,-1.0f),K);
    }
    else if(Phase==EQuickCombatBashPhase::Smash)
    {
        const float K=T*T;   // 与动作同步加速
        Location=FMath::Lerp(FVector(-1.4f,0.5f,1.6f),FVector(3.6f,0.f,-1.6f),K);
        Rotation=FMath::Lerp(FRotator(1.3f,0.f,-1.0f),FRotator(-3.0f,0.f,0.7f),K);
    }
    else if(Phase==EQuickCombatBashPhase::Follow)
    {
        const float K=FMath::SmoothStep(0.f,1.f,T);
        Location=FMath::Lerp(FVector(3.6f,0.f,-1.6f),FVector(6.5f,0.f,-2.4f),K);
        Rotation=FMath::Lerp(FRotator(-3.0f,0.f,0.7f),FRotator(-3.6f,0.f,1.0f),K);
    }
    else
    {
        const float K=1.f-FMath::SmoothStep(0.f,1.f,T);
        Location=FVector(6.5f,0.f,-2.4f)*K;Rotation=FRotator(-3.6f,0.f,1.0f)*K;
    }
    Location*=Strength*Shape;
    Rotation*=Strength*Shape;
    if(bContactDone)QuickCombatImpactShake::Add(ImpactAge,Location,Rotation);
}

void UFPSQuickCombatComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    // The character advances ASH before sampling its pose and camera. Never
    // advance twice or let the wall-clock state finish through a hit stop.
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(Style==EQuickCombatStyle::UnarmedPunch&&Player)return; // advanced once before the character camera
    if(Style==EQuickCombatStyle::SpellbookPush&&Player)return;
    if(Player&&Player->HasOffhandPistol()&&(Style==EQuickCombatStyle::DualPistol||Style==EQuickCombatStyle::StaffOffhandPistol))return;
    if(Style==EQuickCombatStyle::StaffPunch&&Player)
        if(const auto* Staff=Player->FindComponentByClass<UStaffWeaponComponent>();Staff&&Staff->IsEquipped())return;
    if(Style==EQuickCombatStyle::Bow&&IsOccupyingLeftHand())return;
    if(Player&&Player->bUseASH12&&IsRifleStyle()&&IsOccupyingLeftHand())return;
    AdvanceAction(Delta);
}

void UFPSQuickCombatComponent::AdvanceAction(float Delta)
{
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
    const bool bUnarmed=Style==EQuickCombatStyle::UnarmedPunch;
    const bool bBook=Style==EQuickCombatStyle::SpellbookPush;
    const bool bWeaponMatches=Player&&(bBook
        ?(Book&&Book->OwnsLeftHand()&&!Player->IsDoorPushActive()
            &&!AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(Player->GetController())))
        :bUnarmed
        ?(Hands&&Hands->IsEquipped()&&!Player->IsTraversing()
            &&!AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(Player->GetController())))
        :bStaff
        ?(Staff&&Staff->IsEquipped()&&(Style==EQuickCombatStyle::StaffPunch?!Player->HasOffhandPistol():Dual&&Dual->IsOffhandOnly())
            &&!Player->IsTraversing()&&!AFPSGAMEPlayerController::BlocksOngoingActions(Cast<APlayerController>(Player->GetController())))
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
    else if(bStaff||bUnarmed||bBook)
    {
        const float NextAge=ActionAge+Delta;
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

void UFPSQuickCombatComponent::ContactHit()
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* Profile=Model();
    if(!Player||!Profile||!GetWorld())return;
    auto Stats=Profile->QuickCombatStats();
    const bool bUnarmed=Style==EQuickCombatStyle::UnarmedPunch;
    // Bare hands use the same authored contact when struggling out of a coil.
    {
        auto* Capture=Player->FindComponentByClass<UBoundCongregateCaptureComponent>();
        if(Capture&&Capture->HitRestraintWithQuickMelee())
        {
            // The F contact strikes the coil around us, instead of also sweeping
            // through a second target in front. Keep the held weapon's hit feel.
            ImpactAge=0.f;ImpactStrength=1.f;Player->RefreshQuickCombatCamera();
            if(ImpactSound)UGameplayStatics::PlaySound2D(this,ImpactSound,.9f,.9f);
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.8f,1.f);
            return;
        }
    }
    if(bUnarmed){Stats.Damage=UnarmedPunch::Damage(Profile);Stats.RangeCM=UnarmedPunch::ReachCM;Stats.KnockbackCM=0.f;}
    // 打击射线：起点用握把底（与作者源 clip 的接触位置一致），方向用玩家瞄准
    // （与其它武器/技能同一合同）；不再从眼位沿视线前扫，也不再取实时姿态方向。
    const auto Aim=Player->GetMeleeAimTransform();
    const FVector Direction=Aim.GetUnitAxis(EAxis::X);
    FVector Start=Aim.GetLocation();
    FVector ProbeOrigin=FVector::ZeroVector;
    auto* Viewmodel=Player->FindComponentByClass<UFPSCastingMeshComponent>();
    if(Player->bUseASH12&&Viewmodel&&IsRifleStyle())
    {
        // Evaluate the exact contact pose once before the sweep. The faster
        // entry must not trace from the previous frame's wind-up position.
        if(auto* Animation=Cast<UFPSGunplayAnimInstance>(Viewmodel->GetAnimInstance());Animation&&Animation->ActionClip)
        {
            Animation->ActionTime=ContactTime;
            Animation->ActionAlpha=1.f;
            Viewmodel->TickAnimation(0.f,false);
            Viewmodel->RefreshBoneTransforms();
        }
    }
    // 手枪：握把底（手骨 + 相机空间偏移）；步枪：枪身前段（枪口沿枪轴回撤，跟随实际挥击姿态）。
    const bool bBow=Style==EQuickCombatStyle::Bow;
    const bool bBook=Style==EQuickCombatStyle::SpellbookPush;
    const bool bPunch=Style==EQuickCombatStyle::StaffPunch||bUnarmed;
    const bool bOffhand=Style==EQuickCombatStyle::StaffOffhandPistol;
    const bool bRifle=IsRifleStyle();
    auto* Dual=Player->FindComponentByClass<UPistolDualWieldComponent>();
    auto* Bow=Player->FindComponentByClass<UBowWeaponComponent>();
    auto* Staff=Player->FindComponentByClass<UStaffWeaponComponent>();
    auto* Hands=Player->FindComponentByClass<UFPSUnarmedIdleComponent>();
    auto* Book=Player->FindComponentByClass<USpellbookComponent>();
    const bool bProbe=bBook
        ?(Book&&Book->GetQuickCombatStrikeProbe(ProbeOrigin))
        :bUnarmed
        ?(Hands&&Hands->GetStrikeProbe(ProbeOrigin))
        :bPunch
        ?(Staff&&Staff->GetQuickCombatStrikeProbe(ProbeOrigin,ContactTime))
        :bBow
        ?(Bow&&Bow->GetQuickCombatStrikeProbe(ProbeOrigin,ContactTime))
        :(Style==EQuickCombatStyle::DualPistol||bOffhand)
        ?(Dual&&Dual->GetQuickCombatStrikeProbe(ProbeOrigin,ContactTime))
        :(bRifle
            ?(Viewmodel&&Viewmodel->GetRifleStockMeleeProbe(ProbeOrigin,Style==EQuickCombatStyle::M4ReferenceRifle))
            :(Viewmodel&&Viewmodel->GetQuickCombatStrikeProbe(ProbeOrigin)));
    if(bBook&&!bProbe)return;
    if(bProbe)Start=ProbeOrigin;
    FHitResult Hit;
    // 单目标：实际接触优先；小手低位范围补充共用同一次伤害结算。
    const float Radius=bBook?SpellbookAuthoredStrike::QueryRadiusCM:bPunch?StaffQuickCombatMotion::QueryRadiusCM:bBow?BowQuickCombatMotion::QueryRadiusCM
        :bRifle?QuickCombatRifleMotion::QueryRadiusCM:QuickCombatPistolMotion::QueryRadiusCM;
    const bool bHit=MeleeSmallTargets::QueryQuickContact(GetWorld(),Player,Aim,Start,Stats.RangeCM,Radius,Hit);
    // One impulse per damage query, including misses. Keep hit confirmation
    // separate so ASH and bow only pause their animation after actual damage.
    ImpactAge=0.f;
    Player->RefreshQuickCombatCamera();
    AActor* Target=bHit?Hit.GetActor():nullptr;
    const FString TargetName=Target?Target->GetName():FString(TEXT("无"));
    // R0 诊断：一次动作只打一行，标出射线来源、起点与命中对象，方便对实机反馈。
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 接触 武器=%s 射线=%s 起点=%s 方向=%s 距离=%.0f 目标=%s"),
        bBook?TEXT("魔法书前击"):bUnarmed?TEXT("空手拳击"):bPunch?TEXT("法杖左拳"):bOffhand?TEXT("法杖副手枪"):bBow?TEXT("弓"):bRifle?TEXT("步枪"):TEXT("手枪"),
        bProbe?(bBook?TEXT("书页外沿"):bUnarmed?(Hands->GetPunchSide()==1?TEXT("右拳指节"):TEXT("左拳指节")):bPunch?TEXT("左拳指节"):bOffhand?TEXT("左手持枪拳"):bBow?TEXT("弓身下段"):bRifle?(Style==EQuickCombatStyle::M4ReferenceRifle?TEXT("M4枪托"):TEXT("枪身前段")):TEXT("握把底")):TEXT("眼位回退"),
        *Start.ToCompactString(),*Direction.ToCompactString(),Stats.RangeCM,*TargetName);
    if(bHit && UWardBreakableGlass::BreakHit(Hit,Direction))
    {ImpactAge=0.f;ImpactStrength=1.f;return;}
    auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Combat||Combat->IsDead())return;
    const bool Eligible=!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
    FColdSteelSkillShot Shot;
    if(bPunch)
    {
        // A bare fist must not inherit the held staff's rune/ammo/mastery effects.
        Shot.CriticalChance=Profile->Derived(TEXT("crit"));
        Shot.CriticalDamageBonus=Profile->CriticalStrikeEffect().CriticalDamageBonus;
    }
    else Shot=ColdSteelSkills::Snapshot(Player,bBook?Profile->Equipped(Profile->Snapshot().ActiveWeaponSlot==6?8:11)
        :bOffhand&&Dual?&Dual->Hand(1).Item:bBow?Profile->ActiveBow():Profile->Equipped(),false);
    // 步枪版走 rifleMastery 修炼（与枪械命中同一口径），手枪版走 pistolMastery。
    Shot.bRifle=bRifle;Shot.bPistol=IsPistolStyle();Shot.WeakpointPercent=0;
    // 握把底/枪身砸击是钝器动作，按钝器折算削韧；同时标记为手持枪械发动的近战打击，
    // 使其不受「枪械默认不硬直」闸门约束。
    Shot.AttackForm=EMonsterAttackForm::Blunt;Shot.bMeleeStrike=true;
    Shot.AttackMeta=bUnarmed?UnarmedPunch::AttackMeta:uint8(Shot.AttackMeta|0x80);
    FWeaponDamageResult DamageResult;
    const float Applied=ColdSteelSkills::ApplyHit(Player,Hit,Stats.Damage,Direction,Shot,&DamageResult);
    const bool bKilled=Combat->IsDead();
    // 命中确认通道：与剑/火球/冰锥一致——准星命中标记、钝器确认音、怪物血条反馈。
    // bFirearmHit=false ⇒ 走近战/技能确认（枪械命中的落点是另一条通道）。
    if(Applied>0.f||bKilled)Player->NotifyConfirmedWeaponHit(Target,Applied,&DamageResult,false);
    // Pure push: ReceiveStun would still interrupt attacks even with zero seconds.
    if(Applied>0.f||bKilled)Combat->ReceiveMeleeKnockback(Player,Stats.KnockbackCM);
    // 有效命中控制 ASH／弓的短停顿；镜头冲量已在伤害查询帧触发。
    if(Applied>0.f||bKilled){ImpactAge=0.f;ImpactStrength=1.f;}
    if(!bUnarmed&&Eligible&&bKilled)bKillPending=true;
    if((Applied>0.f||bKilled)&&ImpactSound)
    {
        UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Hit.ImpactPoint,bBow?1.f:.9f,bBow?.88f:.9f);
        UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 命中音播放=%s 目标=%s 伤害=%.1f 位置=%s"),
            *ImpactSound->GetName(),*TargetName,Applied,*Hit.ImpactPoint.ToCompactString());
    }
    // 用户 2026-09-19：这枚挥击音从「松握即播」改到伤害确认时刻——挥空整段不出声，
    // 音效继续要求有效命中，独立于判定帧镜头强震（音量仍为 0.8）。
    if((Applied>0.f||bKilled)&&SwingSound)
        UGameplayStatics::PlaySound2D(this,SwingSound,.8f,1.f);
}

void UFPSQuickCombatComponent::FinishAction()
{
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
