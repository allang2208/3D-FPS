#include "FPSQuickCombatComponent.h"
#include "QuickCombatImpactShake.h"
#include "ColdSteelSkillRules.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "FPSCastingMeshComponent.h"
#include "../Weapons/FPSGunplayAnimInstance.h"
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

void UFPSQuickCombatComponent::ConfigureForClipLength(float Length)
{
    using namespace QuickCombatPistolMotion;
    Style=EQuickCombatStyle::Pistol;
    ClipLength=FMath::Max(0.05f,Length);
    ReleaseEnd=ClipLength*ReleaseFraction;
    CockEnd=ClipLength*CockFraction;
    ContactTime=ClipLength*ContactFraction;
    FollowEnd=ClipLength*FollowFraction;
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
    // 其余结算口径与手枪版完全一致：同一冷却、同一修炼、同一击退/眩晕公式。
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 步枪砸击时钟 总长=%.3f 接触=%.3f"),AttackEnd,ContactTime);
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
    // 排队不扣费：动作实际开始才一次性提交冷却与使用修炼（与剑版同一事务口径）。
    Profile->CommitQuickCombatCast();
    Profile->TrainQuickCombat(Profile->QuickCombatDefinition().UseExperience);
    ++Serial;ActionAge=0.f;Phase=EQuickCombatBashPhase::Release;
    bContactDone=bKillPending=false;
    ImpactAge=1.f;ImpactStrength=0.f;
    return true;
}

void UFPSQuickCombatComponent::Cancel()
{
    if(Phase!=EQuickCombatBashPhase::None)FinishAction();
    bContactDone=false;ImpactAge=1.f;ImpactStrength=0.f;
}

bool UFPSQuickCombatComponent::IsImpactPaused() const
{
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    return Player&&Player->bUseASH12&&Style!=EQuickCombatStyle::Pistol
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
    if(Phase==EQuickCombatBashPhase::None)
    {
        if(bContactDone)QuickCombatImpactShake::Add(ImpactAge,Location,Rotation);
        return;
    }
    // 步枪的整枪抬升与下扫使用更大的动作镜头幅度；判定冲量统一。
    const bool bRifle=Style!=EQuickCombatStyle::Pistol;
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
    if(Player&&Player->bUseASH12&&Style!=EQuickCombatStyle::Pistol&&IsOccupyingLeftHand())return;
    AdvanceAction(Delta);
}

void UFPSQuickCombatComponent::AdvanceAction(float Delta)
{
    const float PreviousImpactAge=ImpactAge;
    ImpactAge=FMath::Min(1.f+QuickCombatPistolMotion::ImpactSpan,ImpactAge+Delta);
    if(Phase==EQuickCombatBashPhase::None)return;
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    // 换枪/双持/死亡立刻收手；冷却与已提交的修炼照常保留。
    const auto* Health=Player?Player->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const bool bWeaponMatches=Player&&(Style!=EQuickCombatStyle::Pistol
        ?!Player->IsPistolWeapon()
        :(Player->IsPistolWeapon()&&!Player->IsDualWieldingPistols()));
    if(!Player||!bWeaponMatches||(Health&&Health->IsDead())){Cancel();return;}
    const bool bASH12=Player->bUseASH12&&Style!=EQuickCombatStyle::Pistol;
    if(bASH12)
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
    else
    {
        ActionAge+=Delta;
        Phase=PhaseForAge(ActionAge);
        if(!bContactDone&&ActionAge>=ContactTime){bContactDone=true;ContactHit();}
    }
    if(ActionAge>=AttackEnd)FinishAction();
}

void UFPSQuickCombatComponent::ContactHit()
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());auto* Profile=Model();
    if(!Player||!Profile||!GetWorld())return;
    const auto Stats=Profile->QuickCombatStats();
    // 打击射线：起点用握把底（与作者源 clip 的接触位置一致），方向用玩家瞄准
    // （与其它武器/技能同一合同）；不再从眼位沿视线前扫，也不再取实时姿态方向。
    const auto Aim=Player->GetMeleeAimTransform();
    const FVector Direction=Aim.GetUnitAxis(EAxis::X);
    FVector Start=Aim.GetLocation();
    FVector ProbeOrigin=FVector::ZeroVector;
    auto* Viewmodel=Player->FindComponentByClass<UFPSCastingMeshComponent>();
    if(Player->bUseASH12&&Viewmodel)
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
    const bool bRifle=Style!=EQuickCombatStyle::Pistol;
    const bool bProbe=bRifle
        ?(Viewmodel&&Viewmodel->GetRifleStockMeleeProbe(ProbeOrigin,Style==EQuickCombatStyle::M4ReferenceRifle))
        :(Viewmodel&&Viewmodel->GetQuickCombatStrikeProbe(ProbeOrigin));
    if(bProbe)Start=ProbeOrigin;
    const FVector End=Start+Direction*Stats.RangeCM;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(QuickCombatBash),false,Player);
    // 单目标：最近一次阻挡即结算，不像剑刃那样沿路径多次采样。
    const float Radius=bRifle?QuickCombatRifleMotion::QueryRadiusCM:QuickCombatPistolMotion::QueryRadiusCM;
    const bool bHit=GetWorld()->SweepSingleByChannel(Hit,Start,End,FQuat::Identity,ECC_Pawn,
        FCollisionShape::MakeSphere(Radius),Params);
    // One impulse per damage query, including misses. Keep hit confirmation
    // separate so ASH only freezes its animation after actual damage.
    ImpactAge=0.f;
    Player->RefreshQuickCombatCamera();
    AActor* Target=bHit?Hit.GetActor():nullptr;
    const FString TargetName=Target?Target->GetName():FString(TEXT("无"));
    // R0 诊断：一次动作只打一行，标出射线来源、起点与命中对象，方便对实机反馈。
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 接触 武器=%s 射线=%s 起点=%s 方向=%s 距离=%.0f 目标=%s"),
        bRifle?TEXT("步枪") :TEXT("手枪"),
        bProbe?(bRifle?(Style==EQuickCombatStyle::M4ReferenceRifle?TEXT("M4枪托"):TEXT("枪身前段")):TEXT("握把底")):TEXT("眼位回退"),
        *Start.ToCompactString(),*Direction.ToCompactString(),Stats.RangeCM,*TargetName);
    auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Combat||Combat->IsDead())return;
    const bool Eligible=!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
    auto Shot=ColdSteelSkills::Snapshot(Player,Profile->Equipped());
    // 步枪版走 rifleMastery 修炼（与枪械命中同一口径），手枪版走 pistolMastery。
    Shot.bRifle=bRifle;Shot.bPistol=!bRifle;Shot.WeakpointPercent=0;
    FWeaponDamageResult DamageResult;
    const float Applied=ColdSteelSkills::ApplyHit(Player,Hit,Stats.Damage,Direction,Shot,&DamageResult);
    const bool bKilled=Combat->IsDead();
    // 命中确认通道：与剑/火球/冰锥一致——准星命中标记、钝器确认音、怪物血条反馈。
    // bFirearmHit=false ⇒ 走近战/技能确认（枪械命中的落点是另一条通道）。
    if(Applied>0.f||bKilled)Player->NotifyConfirmedWeaponHit(Target,Applied,&DamageResult,false);
    // 击退与眩晕合并进 ReceiveStun 的一次提交（无该组件的怪物与剑版口径一致：不硬控）。
    if(Applied>0.f||bKilled)Combat->ReceiveStun(Player,Stats.StunSeconds,Stats.KnockbackCM);
    // 命中确认只控制 ASH 停顿；镜头强震已在伤害查询帧触发。
    if(Applied>0.f||bKilled){ImpactAge=0.f;ImpactStrength=1.f;}
    if(Eligible&&bKilled)bKillPending=true;
    if((Applied>0.f||bKilled)&&ImpactSound)
    {
        UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Hit.ImpactPoint,.9f,.9f);
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
    if(auto* Profile=Model())
    {
        // 冷却在动作结束后才起跳（预留-结束起跳合同）；击杀修炼随收势统一提交。
        Profile->FinishQuickCombatCast();
        if(bKillPending)Profile->TrainQuickCombat(Profile->QuickCombatDefinition().KillExperience);
    }
    bKillPending=false;
    Phase=EQuickCombatBashPhase::None;ActionAge=0.f;
}

void UFPSQuickCombatComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    // 销毁路径同样解除冷却预留并保留已提交的冷却。
    if(Phase!=EQuickCombatBashPhase::None)FinishAction();
    Super::EndPlay(Reason);
}
