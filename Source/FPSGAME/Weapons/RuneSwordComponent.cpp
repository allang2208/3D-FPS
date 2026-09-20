#include "RuneSwordComponent.h"
#include "RuneSwordMeshComponent.h"
#include "RuneSwordOverheadFeel.h"
#include "MeleeRuneVisual.h"
#include "MeleeGuardAssets.h"
#include "ModularSwordVisual.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "RuneSwordCombatTuning.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Skills/QuickCombatPistolMotion.h"
#include "../Skills/QuickCombatImpactShake.h"
#include "ColdSteelEnchantmentCombat.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

URuneSwordComponent::URuneSwordComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

bool URuneSwordComponent::TriggerHeavySkill()
{
    if(!IsEquipped()||IsBusy()||!CanUse())return false;
    BeginHeavyCharge();
    bAutoHeavyRelease=bCharging;
    return bCharging;
}

void URuneSwordComponent::FinishHeavyTraining()
{
    if(!bHeavyTrainingPending)return;
    bHeavyTrainingPending=false;
    if(GetWorld()&&GetWorld()->GetGameInstance())
        if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            Profile->TrainHeavyStrike(HeavyTrainingHits,HeavyTrainingKills);
}

void URuneSwordComponent::BeginPlay()
{
    Super::BeginPlay();
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner()); Character=Pawn;
    auto* World=GetWorld();
    auto* GameInstance=World?World->GetGameInstance():nullptr;
    // IsGameWorld includes GamePreview; visual rigs must not access inventory.
    if(!Pawn || !GameInstance || (World->WorldType!=EWorldType::Game && World->WorldType!=EWorldType::PIE) || Pawn->GetNetMode()!=NM_Standalone)
    {SetComponentTickEnabled(false);return;}
    Camera=Pawn->FindComponentByClass<UCameraComponent>();
    if(!Camera){SetComponentTickEnabled(false);return;}
    AddTickPrerequisiteActor(Pawn);
    Viewmodel=NewObject<URuneSwordMeshComponent>(Pawn,TEXT("RuneSwordViewmodel"));
    Pawn->AddInstanceComponent(Viewmodel);Viewmodel->SetupAttachment(Camera);
    Viewmodel->SetRelativeRotation(FRotator(0,90,0));
    Viewmodel->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Viewmodel->SetCanEverAffectNavigation(false);Viewmodel->SetOnlyOwnerSee(true);
    Viewmodel->SetCastShadow(false);Viewmodel->bReceivesDecals=false;
    Viewmodel->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Viewmodel->RegisterComponent();Viewmodel->SetVisibility(false,true);
    // A single animation clock supplies pose, hit window, and audio timing.
    Viewmodel->SetComponentTickEnabled(false);
    RiftVisual=NewObject<UStaticMeshComponent>(Pawn,TEXT("RuneSwordRift"));
    Pawn->AddInstanceComponent(RiftVisual);
    RiftVisual->SetMobility(EComponentMobility::Movable);
    RiftVisual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    RiftVisual->SetCanEverAffectNavigation(false);RiftVisual->SetOnlyOwnerSee(true);
    RiftVisual->SetCastShadow(false);RiftVisual->bReceivesDecals=false;
    RiftVisual->RegisterComponent();RiftVisual->SetVisibility(false);
    RiftVisual->SetComponentTickEnabled(false);
    RefreshEquipment(GameInstance->GetSubsystem<UColdSteelStatusModel>());
}

void URuneSwordComponent::RefreshEquipment(UColdSteelStatusModel* Profile)
{
    if(!Profile || !Viewmodel)return;
    const auto* Item=Profile->Equipped();
    const FString NewId=Item && !Profile->ActiveProductionTool() && ColdSteelInventory::IsTwoHandedSword(*Item) ? Item->InstanceId : FString();
    if(!NewId.IsEmpty())
    {
        const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);
        Damage=Stats.Damage;AttackRate=Stats.AttackRate;Reach=Stats.BaseReach;MeleeModifiers=Stats.Modifiers;
        // Timing belongs to the installed animation revision. Existing saved
        // instances can still contain earlier contact-window metadata.
    }
    const bool Modular=!NewId.IsEmpty()&&ColdSteelModularSword::Supports(*Item);
    const FString NewMeshPath=NewId.IsEmpty()?FString():(Modular?ColdSteelModularSword::ArmsMesh(*Item):ColdSteelMeleeGuard::Viewmodel(*Item));
    const FString NewAnimationFolder=NewId.IsEmpty()?FString():ColdSteelModularSword::AnimationFolder(*Item);
    const UAnimSequence* Idle=Animations.FindRef(TEXT("Idle")).Get();
    const bool bSameAnimationFolder=NewId.IsEmpty()||(Idle&&Idle->GetPathName().StartsWith(NewAnimationFolder+TEXT("/")));
    if(NewId==InstanceId&&NewMeshPath==EquippedMeshPath&&bSameAnimationFolder){RefreshModularSword(NewId.IsEmpty()?nullptr:Item);ColdSteelMeleeRune::Apply(Viewmodel,NewId.IsEmpty()||Modular?FString():ColdSteelMeleeRune::Selected(*Item));return;}
    CancelAction();InstanceId=NewId;EquippedMeshPath=NewMeshPath;NextSlash=0;
    Viewmodel->SetVisibility(false,true);
    if(NewId.IsEmpty()){RefreshModularSword(nullptr);return;}
    const FString Folder=NewAnimationFolder;
    const FString SoundFolder=ColdSteelInventory::Text(*Item,TEXT("animation_folder"));
    auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*EquippedMeshPath);
    Viewmodel->SetSkeletalMesh(Mesh);Animations.Reset();
    RefreshModularSword(Item);
    ColdSteelMeleeRune::Apply(Viewmodel,Modular?FString():ColdSteelMeleeRune::Selected(*Item));
    for(const TCHAR* Clip:{TEXT("Idle"),TEXT("Walk"),TEXT("Whirlwind"),TEXT("Equip"),TEXT("Inspect"),TEXT("Overhead"),TEXT("Slash1"),TEXT("Slash2"),TEXT("Thrust"),TEXT("PommelStrike"),TEXT("HeavyCharge"),TEXT("HeavyRelease"),TEXT("Guard"),TEXT("GuardHit"),TEXT("GuardBreak")})
        Animations.Add(FName(Clip),LoadObject<UAnimSequence>(nullptr,*(Folder+TEXT("/A_RuneSword_")+Clip+(FCString::Strcmp(Clip,TEXT("Whirlwind"))==0?TEXT("V4"):TEXT("")))));
    SwingSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("swing_sound")));
    AttackLayerSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Audio/SwordAttack20260914/S_Sword_Attack.S_Sword_Attack"));
    HitSound=LoadObject<USoundBase>(nullptr,*ColdSteelInventory::Text(*Item,TEXT("hit_sound")));
    // Only the fourth hit uses the counterweight impact cue; slash, thrust and the
    // heavy cuts keep the weapon's own hit_sound.
    PommelHitSound=LoadObject<USoundBase>(nullptr,TEXT("/Game/Audio/WeaponHit20260916/S_MeleeHit_Quick.S_MeleeHit_Quick"));
    BlockSound=LoadObject<USoundBase>(nullptr,*(SoundFolder+TEXT("/S_RuneSword_Block")));
    ParrySound=LoadObject<USoundBase>(nullptr,*(SoundFolder+TEXT("/S_RuneSword_Parry")));
    if(!RiftMaterial)
    {
        const FString FXFolder=TEXT("/Game/Weapons/AzureRunesword20260913/WristRiftV3/");
        auto* Material=LoadObject<UMaterialInterface>(nullptr,*(FXFolder+TEXT("M_RuneRift")));
        if(Material){RiftMaterial=UMaterialInstanceDynamic::Create(Material,this);RiftVisual->SetMaterial(0,RiftMaterial);}
        RiftMeshes.Reset();
        RiftMeshes.Add(LoadObject<UStaticMesh>(nullptr,*(FXFolder+TEXT("SM_RuneRift_Slash1"))));
        RiftMeshes.Add(LoadObject<UStaticMesh>(nullptr,*(FXFolder+TEXT("SM_RuneRift_Slash2"))));
        RiftMeshes.Add(LoadObject<UStaticMesh>(nullptr,*(FXFolder+TEXT("SM_RuneRift_Heavy"))));
        RiftMeshes.Add(LoadObject<UStaticMesh>(nullptr,*(FXFolder+TEXT("SM_RuneRift_Thrust"))));
        RiftMeshes.Add(LoadObject<UStaticMesh>(nullptr,*(FXFolder+TEXT("SM_RuneRift_Pommel"))));
        RiftMeshes.Add(LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/AzureRunesword20260913/SprintOverhead20260920/SM_RuneRift_Overhead")));
    }
    if(!Mesh || !Animations.FindRef(TEXT("Idle")) || !Animations.FindRef(TEXT("Slash1")) || !Animations.FindRef(TEXT("Slash2")) || !Animations.FindRef(TEXT("Thrust")))
    {UE_LOG(LogTemp,Error,TEXT("Two-handed sword assets are missing for %s (animation folder %s)."),*Item->Definition,*Folder);return;}
    bEquipping=true;SetClip(TEXT("Equip"),false);
    if(!CurrentAnimation){bEquipping=false;SetClip(TEXT("Idle"),true);}
    Viewmodel->SetVisibility(CanUse(),true);
}

void URuneSwordComponent::RefreshModularSword(const FColdSteelItem* Item)
{
    if(!Item||!ColdSteelModularSword::Supports(*Item))
    {
        if(ModularSword){ColdSteelModularSword::Clear(ModularSword);Character->RemoveInstanceComponent(ModularSword);ModularSword->DestroyComponent();ModularSword=nullptr;}
        return;
    }
    if(!ModularSword)
    {
        ModularSword=NewObject<UStaticMeshComponent>(Character.Get(),TEXT("ModularSwordBlade"));
        Character->AddInstanceComponent(ModularSword);ModularSword->SetupAttachment(Viewmodel,TEXT("WPN_root"));
        ModularSword->SetMobility(EComponentMobility::Movable);ModularSword->SetOnlyOwnerSee(true);
        ModularSword->SetCollisionEnabled(ECollisionEnabled::NoCollision);ModularSword->SetCanEverAffectNavigation(false);
        ModularSword->SetCastShadow(false);ModularSword->bReceivesDecals=false;
        ModularSword->SetVisibility(Viewmodel->IsVisible());ModularSword->RegisterComponent();
    }
    ModularSword->SetRelativeTransform(ColdSteelModularSword::BoneMount(*Item));
    ColdSteelModularSword::Apply(ModularSword,*Item);
    ModularBladeBase=ColdSteelModularSword::BladePoint(*Item,false);ModularBladeTip=ColdSteelModularSword::BladePoint(*Item,true);
}

bool URuneSwordComponent::CanUse() const
{
    auto* Pawn=Character.Get();const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Build=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    return !AFPSGAMEPlayerController::BlocksOngoingActions(PC) &&
        !Pawn->IsTraversing() && (!Health || !Health->IsDead()) && (!Build || !Build->IsBuilding());
}

void URuneSwordComponent::SetClip(FName Name,bool bLoop)
{
    CurrentClip=Name;CurrentAnimation=Animations.FindRef(Name);Elapsed=0;
    if(!CurrentAnimation || !Viewmodel)return;
    Viewmodel->PlayAnimation(CurrentAnimation,bLoop);Viewmodel->SetPlayRate(0.f);SamplePose(0.f);
    if(Character.IsValid())PreviousAimFrame=Character->GetMeleeAimTransform();
}

void URuneSwordComponent::SamplePose(float Time)
{
    if(!Viewmodel || !CurrentAnimation)return;
    Viewmodel->SetPosition(Time,false);Viewmodel->TickAnimation(0.f,false);Viewmodel->RefreshBoneTransforms();
    ColdSteelMeleeRune::UpdatePose(ModularSword?static_cast<UMeshComponent*>(ModularSword.Get()):Viewmodel.Get());
}

void URuneSwordComponent::BeginInspect()
{
    if(!IsEquipped() || IsBusy() || bGuardHeld || !CanUse() || !Viewmodel || !Viewmodel->GetSkeletalMeshAsset())return;
    if(Character->IsCastBlockingLeftHandAction() || !Animations.FindRef(TEXT("Inspect")))return;
    // Cosmetic action: its own real-time clock, no attack rate, stamina or hit window.
    bInspecting=true;bQueuedAttack=false;StopRift();
    SetClip(TEXT("Inspect"),false);
}

void URuneSwordComponent::BeginAttack()
{
    if(bWhirlwind)return;
    if(bGuardHeld || bGuarding || bReturningGuard || bGuardReacting || bGuardBreakPose)return;
    // Let the current swing finish; only reject a new swing or queued combo.
    if(Character.IsValid() && Character->IsCastBlockingLeftHandAction()){bQueuedAttack=false;return;}
    if(!IsEquipped() || !CanUse() || !Viewmodel || !Viewmodel->GetSkeletalMeshAsset())return;
    if(bInspecting)CancelAction();
    if(bCharging || bReturningCharge)return;
    if(bEquipping){bQueuedAttack=true;return;}
    if(bAttacking){if(Elapsed>=ContactEnd)bQueuedAttack=true;return;}
    if(GetWorld()->GetTimeSeconds()-LastAttackEnd>.85)NextSlash=0;
    // Repeat the three-stage loop: right-to-left slash, left-to-right slash, thrust.
    NextSlash%=3;
    const FName Clip=NextSlash==0?TEXT("Slash1"):(NextSlash==1?TEXT("Slash2"):TEXT("Thrust"));
    if(StartSwing(Clip,false))NextSlash=(NextSlash+1)%3;
}

void URuneSwordComponent::BeginOverhead()
{
    if(bWhirlwind)return;
    // Sprint attack: same guards and same swing path as the ordinary slash, only
    // a different clip and its own contact window.  Damage, reach, stamina and
    // the combo stage are whatever the item already gives the normal attack.
    if(bGuardHeld || bGuarding || bReturningGuard || bGuardReacting || bGuardBreakPose)return;
    if(Character.IsValid() && Character->IsCastBlockingLeftHandAction()){bQueuedAttack=false;return;}
    if(!IsEquipped() || !CanUse() || !Viewmodel || !Viewmodel->GetSkeletalMeshAsset())return;
    if(!Animations.FindRef(TEXT("Overhead")))
    {
        // Loud on purpose: a missing clip silently falling back to the ordinary
        // slash is indistinguishable from "the sprint attack does nothing".
        UE_LOG(LogTemp,Warning,TEXT("RuneSword: Overhead clip is missing for %s; sprint attack falls back to the slash."),*InstanceId);
        BeginAttack();return;
    }
    if(bInspecting)CancelAction();
    if(bCharging || bReturningCharge)return;
    if(bEquipping || bAttacking){bQueuedAttack=true;return;}
    StartSwing(TEXT("Overhead"),false);
}

void URuneSwordComponent::BeginPrimaryAttack()
{
    if(bWhirlwind)return;
    if(bInspecting)CancelAction();
    if(bGuardHeld || bGuarding || bReturningGuard || bGuardReacting || bGuardBreakPose)return;
    // Preserve the ordinary equip/recovery click buffer. This press belongs to
    // that combo, so its release must not start a second attack or a charge.
    if(bAttacking || bEquipping){BeginAttack();return;}
    BeginHeavyCharge();
}

void URuneSwordComponent::ReleasePrimaryAttack()
{
    if(!bCharging)return;
    if(!CanUse() || Character->IsCastBlockingLeftHandAction()){CancelAction();return;}
    const double HeldSeconds=GetWorld()->GetTimeSeconds()-ChargeStartedAt;
    if(HeldSeconds<=.20)
    {
        // A tap uses the full normal attack and advances the three-part combo.
        // The two-second charge clock always starts at the original press.
        bCharging=false;BeginAttack();
        if(!bAttacking)ReturnFromCharge();
        return;
    }
    ReleaseHeavyCharge();
}

bool URuneSwordComponent::StartSwing(FName Clip,bool Heavy)
{
    if(!Animations.FindRef(Clip))return false;
    bQueuedQuickCombat=false;bQuickCombatStrike=false;bQuickCombatContactDone=false;
    if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
    {
        if(const auto* Item=Profile->Equipped())
        {
            const auto Stats=ColdSteelMelee::Evaluate(*Item,Profile);
            Damage=Stats.Damage;AttackRate=Stats.AttackRate;Reach=Stats.BaseReach;MeleeModifiers=Stats.Modifiers;
            SwingKnockbackCM=Stats.KnockbackCM;
        }
        if(!Profile->SpendStamina(ColdSteelMelee::AttackStamina(Profile->Equipped(),Profile))){bQueuedAttack=false;return false;}
    }
    bAttacking=true;bQueuedAttack=bCharging=bReturningCharge=false;bHeavyAttack=Heavy;
    bThrustAttack=Clip==TEXT("Thrust");bPommelAttack=Clip==TEXT("PommelStrike");
    bOverheadAttack=Clip==TEXT("Overhead");
    bLungeStarted=bLungeBlocked=false;
    // The counterweight sits behind the guard on the hilt axis: each sword keeps
    // its own pommel length instead of borrowing the rune sword's number.
    PommelDepthCM=ModularSword?FMath::Clamp(-ColdSteelModularSword::LocalBounds(ModularSword).Min.Z,RuneSwordPommelRhythm::BladeBaseCM+6.f,40.f)
        :RuneSwordPommelRhythm::CounterweightCM;
    LungeDirection=FVector::ZeroVector;
    // Snapshot the current action's combo bonus once, not the number of targets hit.
    // The independent quick-combat strike supplies its own skill damage below.
    const int32 ComboStage=Clip==TEXT("Slash2")?2:Clip==TEXT("Thrust")?3:1;
    HitActors.Reset();SwingDamage=Damage*(Heavy?MeleeModifiers.HeavyMultiplier(ChargedMultiplier):MeleeModifiers.ComboMultiplier(ComboStage));
    bHeavyTrainingPending=Heavy;HeavyTrainingHits=HeavyTrainingKills=0;bAutoHeavyRelease=false;
    SwingRate=AttackRate;SwingReach=RuneSwordCombatTuning::ScaledReach(Reach,bThrustAttack?RuneSwordThrustRhythm::ReachBonus:0.f)*MeleeModifiers.Range;
    SwingRangeMultiplier=RuneSwordCombatTuning::RangeMultiplier*MeleeModifiers.Range;
    SwingHitReactionMultiplier=MeleeModifiers.HitReaction;
    SwingRuneVulnerability=MeleeModifiers.RuneVulnerability;SwingRuneVulnerabilitySeconds=MeleeModifiers.RuneVulnerabilitySeconds;
    ContactStart=bOverheadAttack?RuneSwordOverheadRhythm::ContactStart:(Heavy?RuneSwordHeavyRhythm::ContactStart:(bThrustAttack?RuneSwordThrustRhythm::ContactStart:(bPommelAttack?RuneSwordPommelRhythm::ContactStart:RuneSwordRhythm::ContactStart)));
    ContactEnd=bOverheadAttack?RuneSwordOverheadRhythm::ContactEnd:(Heavy?RuneSwordHeavyRhythm::ContactEnd:(bThrustAttack?RuneSwordThrustRhythm::ContactEnd:(bPommelAttack?RuneSwordPommelRhythm::ContactEnd:RuneSwordRhythm::ContactEnd)));
    bImpactFeedbackPlayed=bSwingCuePlayed=false;
    SwingTrainingHits=0;
    SwingPoison=ColdSteelCombat::Snapshot(Character.Get()).Poison;
    SwingSkills=ColdSteelSkills::Snapshot(Character.Get());
    SwingSkills.bRifle=false;SwingSkills.bPistol=false;SwingSkills.WeakpointPercent=0;
    SetClip(Clip,false);return true;
}

bool URuneSwordComponent::BeginQuickCombatStrike()
{
    if(bWhirlwind)return false;
    // 快速进战：只换动作来源与结算参数，不推进普通连击计数；占用与守卫同普通攻击。
    if(bGuardHeld || bGuarding || bReturningGuard || bGuardReacting || bGuardBreakPose)return false;
    if(Character.IsValid() && Character->IsCastBlockingLeftHandAction())return false;
    if(!IsEquipped() || !CanUse() || !Viewmodel || !Viewmodel->GetSkeletalMeshAsset())return false;
    if(bInspecting)CancelAction();
    if(bCharging || bReturningCharge || bEquipping)return false;
    if(bAttacking)
    {
        // 沿用普通攻击的排队窗口：接触段结束后排队补一记，接触段内丢弃。
        if(Elapsed>=ContactEnd){bQueuedQuickCombat=true;return true;}
        return false;
    }
    return StartQuickCombatStrike();
}

bool URuneSwordComponent::StartQuickCombatStrike()
{
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile || !Animations.FindRef(TEXT("PommelStrike")))return false;
    if(!StartSwing(TEXT("PommelStrike"),false))return false;
    bQuickCombatStrike=true;
    const auto Cast=Profile->QuickCombatStats();
    SwingDamage=Cast.Damage;
    // 击退与眩晕合并进 ReceiveStun 的一次提交，普通推退在此关闭。
    SwingKnockbackCM=0.f;
    QuickCombatStunSeconds=Cast.StunSeconds;
    QuickCombatKnockbackCM=Cast.KnockbackCM;
    // 判定距离用技能自己的 rangeCM：普通挥击的 SwingReach（刀长×2）与技能范围
    // 是两套口径，此前 Max() 混用让快速进战的 reach 门控跑到了 360cm。
    QuickCombatRangeCM=Cast.RangeCM;
    Profile->CommitQuickCombatCast();
    Profile->TrainQuickCombat(Profile->QuickCombatDefinition().UseExperience);
    return true;
}

void URuneSwordComponent::QuickCombatContractHit()
{
    // 快速进战合同判定（2026-09-19 与手枪版对齐）：接触时刻一次确定性扫射——
    // 起点=配重打击端（画面同源，读不到退眼位），方向=玩家瞄准，长度=技能 rangeCM，
    // Ø32 球、ECC_Pawn 最近阻挡者。前向走廊/眼位遮挡/沿动画路径采样都不参与：
    // 三个武器类别共用同一份命中合同，动作本体只负责观感。
    // 调用方须先 SamplePose 到接触帧（ReadBlade 读的是当前骨姿态）。
    auto* Pawn=Character.Get();
    if(!Pawn||!GetWorld())return;
    const auto Aim=Pawn->GetMeleeAimTransform();
    const FVector Direction=Aim.GetUnitAxis(EAxis::X);
    FVector Start=Aim.GetLocation();
    bool bFromPommel=false;
    if(Viewmodel)
    {
        // bPommelAttack 下 ReadBlade 的 Base/Tip 已换成配重打击面（护手后 PommelDepthCM）。
        const auto Sample=ReadBlade(Aim);
        if((Sample.Tip-Start).SizeSquared()>1.f){Start=Sample.Tip;bFromPommel=true;}
    }
    const FVector End=Start+Direction*QuickCombatRangeCM;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(QuickCombatPommel),false,Pawn);
    const bool bHit=GetWorld()->SweepSingleByChannel(Hit,Start,End,FQuat::Identity,ECC_Pawn,
        FCollisionShape::MakeSphere(QuickCombatPistolMotion::QueryRadiusCM),Params);
    // Quick-melee shake belongs to this once-only query, including a miss.
    // Damage, stun, training and confirmation cues still require a real hit.
    bImpactFeedbackPlayed=true;ImpactAge=0.f;
    Pawn->RefreshQuickCombatCamera();
    AActor* Target=bHit?Hit.GetActor():nullptr;
    UE_LOG(LogTemp,Log,TEXT("[QuickCombat] 接触 武器=剑 射线=%s 起点=%s 方向=%s 距离=%.0f 目标=%s"),
        bFromPommel?TEXT("配重端"):TEXT("眼位回退"),*Start.ToCompactString(),*Direction.ToCompactString(),
        QuickCombatRangeCM,Target?*Target->GetName():TEXT("无"));
    auto* Combat=Target?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Combat||Combat->IsDead())return;
    const bool Eligible=!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
    auto HitSkills=SwingSkills;
    FWeaponDamageResult DamageResult;
    const float Applied=Combat->ApplyHitWithReactionScale(SwingHitReactionMultiplier,
        [&](){return ColdSteelSkills::ApplyHit(Pawn,Hit,SwingDamage,Direction,HitSkills,&DamageResult);});
    const bool bKilled=Combat->IsDead();
    if(Applied<=0.f&&!bKilled)return;
    // 击退与眩晕合并进 ReceiveStun 一次提交（与手枪版同一口径）。
    Combat->ReceiveStun(Pawn,QuickCombatStunSeconds,QuickCombatKnockbackCM);
    if(Eligible&&bKilled)QuickCombatKillPending=true;
    if(!Combat->IsDead()&&SwingRuneVulnerability>0)
        if(auto* Status=UCombatStatusFormula::GetOrAdd(Target))Status->AddRuneMagicVulnerability(SwingRuneVulnerability,SwingRuneVulnerabilitySeconds);
    if(!Combat->IsDead()&&Eligible)++SwingTrainingHits;
    Pawn->NotifyConfirmedWeaponHit(Target,Applied,&DamageResult);
    ColdSteelCombat::OnHit(Target,Pawn,SwingPoison);
}

FVector URuneSwordComponent::AdvanceThrustLunge(float FromTime,float ToTime)
{
    // The thrust strides a metre; the counterweight strike only steps in far enough
    // to reach with a striking end that sits one pommel-length past the hands.
    if(!bThrustAttack && !bPommelAttack)return FVector::ZeroVector;
    const float Distance=bThrustAttack?
        RuneSwordThrustRhythm::LungeDistance*(RuneSwordThrustRhythm::LungeAlpha(ToTime)-RuneSwordThrustRhythm::LungeAlpha(FromTime)):
        RuneSwordPommelRhythm::LungeDistance*(RuneSwordPommelRhythm::LungeAlpha(ToTime)-RuneSwordPommelRhythm::LungeAlpha(FromTime));
    if(bLungeBlocked || Distance<=0.f)return FVector::ZeroVector;
    auto* Pawn=Character.Get();
    auto* Movement=Pawn?Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()):nullptr;
    if(!Movement || Pawn->IsSliding() || Pawn->IsTraversing() || !Movement->IsMovingOnGround() || Movement->IsDodging())
    {bLungeBlocked=true;return FVector::ZeroVector;}
    if(!bLungeStarted)
    {
        LungeDirection=Pawn->GetMeleeAimTransform().GetUnitAxis(EAxis::X).GetSafeNormal2D();
        bLungeStarted=true;
    }
    const FVector Moved=Movement->ApplyMeleeLungeStep(LungeDirection,Distance);
    if(FVector::DotProduct(Moved,LungeDirection)+.01f<Distance)bLungeBlocked=true;
    return Moved;
}

void URuneSwordComponent::BeginHeavyCharge()
{
    if(bWhirlwind)return;
    if(bInspecting)CancelAction();
    if(!IsEquipped() || IsBusy() || !CanUse() || !Viewmodel || !Viewmodel->GetSkeletalMeshAsset())return;
    if(Character->IsCastBlockingLeftHandAction())return;
    if(!Animations.FindRef(TEXT("HeavyCharge")) || !Animations.FindRef(TEXT("HeavyRelease")))return;
    if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        if(!Profile->CanSpendStamina(ColdSteelMelee::AttackStamina(Profile->Equipped(),Profile)))return;
    const auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile||Profile->MasteryProgress(TEXT("heavyStrike")).Level<1||Profile->ActiveProductionTool())return;
    const auto Skill=Profile->MasteryEffect(TEXT("heavyStrike"));RequiredChargeSeconds=Skill.HeavyChargeSeconds;ChargedMultiplier=Skill.HeavyMultiplier;
    bAutoHeavyRelease=false;
    bCharging=true;bQueuedAttack=false;bHeavyAttack=false;HitActors.Reset();
    ChargeStartedAt=GetWorld()->GetTimeSeconds();
    SetClip(TEXT("HeavyCharge"),false);
}

void URuneSwordComponent::ReleaseHeavyCharge()
{
    if(!bCharging)return;
    if(!CanUse() || Character->IsCastBlockingLeftHandAction()){CancelAction();return;}
    // Input is dispatched before the component tick: decide from the input's
    // gameplay timestamp, so an exact two-second hold does not lose one frame.
    const double HeldSeconds=GetWorld()->GetTimeSeconds()-ChargeStartedAt;
    const bool Heavy=HeldSeconds>=RequiredChargeSeconds;
    const float ChargePoseTime=Elapsed;
    // Charging always loads the right shoulder. Continue with Slash1, then
    // allow the existing left-click combo to mirror into Slash2.
    if(StartSwing(Heavy?TEXT("HeavyRelease"):TEXT("Slash1"),Heavy))
    {
        if(!Heavy)
        {
            // HeavyCharge reaches V6's raised pose at .65 s and its ordinary
            // load pose at 1.60 s. Resume the matching point in the V8 windup
            // instead of resetting the hands to idle and lifting a second time.
            const float SourceTime=ChargePoseTime<.65f ? .17f*ChargePoseTime/.65f :
                FMath::Lerp(.17f,.40f,FMath::Clamp((ChargePoseTime-.65f)/.95f,0.f,1.f));
            float Low=0.f,High=RuneSwordRhythm::WindupEnd;
            for(int32 I=0;I<16;++I)
            {
                const float Mid=(Low+High)*.5f;
                if(RuneSwordRhythm::SourceTime(Mid)<SourceTime)Low=Mid;else High=Mid;
            }
            Elapsed=(Low+High)*.5f;SamplePose(Elapsed);
        }
        NextSlash=1;return;
    }
    // A failed stamina/asset gate still returns safely without dealing damage.
    ReturnFromCharge();
}

void URuneSwordComponent::ReturnFromCharge()
{
    bCharging=false;bReturningCharge=true;bQueuedAttack=false;
    CancelChargeFrom=Elapsed;CancelChargeAge=0.f;
    CancelChargeDuration=FMath::Clamp(Elapsed*.25f,.1f,.45f);
}

void URuneSwordComponent::CancelAction()
{
    FinishWhirlwind();
    FinishHeavyTraining();bAutoHeavyRelease=false;
    ClearGuard();
    bAttacking=bEquipping=bInspecting=bQueuedAttack=bCharging=bReturningCharge=bHeavyAttack=false;HitActors.Reset();
    bThrustAttack=bPommelAttack=bLungeStarted=bLungeBlocked=false;LungeDirection=FVector::ZeroVector;
    bOverheadAttack=false;bQuickCombatStrike=bQueuedQuickCombat=false;bQuickCombatContactDone=false;QuickCombatStunSeconds=0.f;QuickCombatKnockbackCM=0.f;
    // 取消（死亡/换装/不可用）同样解除冷却预留并保留已提交的冷却，与火球口径一致。
    if(auto* Profile=GetWorld()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr)
    {
        Profile->FinishQuickCombatCast();
        if(QuickCombatKillPending)Profile->TrainQuickCombat(Profile->QuickCombatDefinition().KillExperience);
    }
    QuickCombatKillPending=false;
    ImpactAge=1.f;bImpactFeedbackPlayed=bThrustImpact=false;
    StopRift();
    if(Viewmodel && Animations.FindRef(TEXT("Idle")))SetClip(TEXT("Idle"),true);
}

void URuneSwordComponent::GetCameraMotion(FVector& Location,FRotator& Rotation) const
{
    Location=FVector::ZeroVector;Rotation=FRotator::ZeroRotator;
    if(!IsEquipped())return;
    if(bWhirlwind)return;
    if(GetGuardCameraMotion(Location,Rotation))return;
    if(!CanUse())return;
    if(bCharging || bReturningCharge)
    {
        const float Gather=FMath::SmoothStep(0.f,RuneSwordHeavyRhythm::ChargeSeconds,Elapsed);
        Location=FVector(-13.f,7.8f,3.12f)*Gather;
        Rotation=FRotator(7.8f,9.1f,6.5f)*Gather;
    }
    else if(bAttacking && bOverheadAttack)
    {
        RuneSwordOverheadFeel::Camera(Elapsed,bImpactFeedbackPlayed,ImpactAge,ImpactStrength,Location,Rotation);
    }
    else if(bAttacking && bThrustAttack)
    {
        const float ExtensionEnd=RuneSwordThrustRhythm::ExtensionEnd;
        const FVector LoadLocation(-8.f,1.5f,1.2f),FollowLocation(13.f,-.6f,-3.5f);
        const FRotator LoadRotation(3.f,1.2f,.8f),FollowRotation(-4.5f,-.7f,-.6f);
        if(Elapsed<=ContactStart)
        {
            const float Gather=FMath::SmoothStep(0.f,RuneSwordThrustRhythm::LoadEnd,Elapsed);
            Location=LoadLocation*Gather;Rotation=LoadRotation*Gather;
        }
        else if(Elapsed<=ExtensionEnd)
        {
            const float U=(Elapsed-ContactStart)/(ExtensionEnd-ContactStart);
            const float Push=FMath::SmoothStep(0.f,1.f,U),Burst=FMath::Square(FMath::Sin(PI*U));
            Location=FMath::Lerp(LoadLocation,FollowLocation,Push);Location.X+=5.f*Burst;
            Rotation=FMath::Lerp(LoadRotation,FollowRotation,Push);
            Rotation.Pitch+=1.8f*Burst*FMath::Sin(U*PI*4.f);
        }
        else
        {
            float Weight;
            if(Elapsed<=RuneSwordThrustRhythm::ArrestEnd)
                Weight=1.f+.08f*FMath::Sin(PI*(Elapsed-ExtensionEnd)/(RuneSwordThrustRhythm::ArrestEnd-ExtensionEnd));
            else if(Elapsed<=RuneSwordThrustRhythm::ReturnCorner)
                Weight=FMath::Lerp(1.f,.18f,FMath::SmoothStep(RuneSwordThrustRhythm::ArrestEnd,RuneSwordThrustRhythm::ReturnCorner,Elapsed));
            else
                Weight=.18f*(1.f-FMath::SmoothStep(RuneSwordThrustRhythm::ReturnCorner,RuneSwordThrustRhythm::AttackEnd,Elapsed));
            Location=FollowLocation*Weight;Rotation=FollowRotation*Weight;
        }
        if(bLungeStarted)
        {
            // One weight shift and one foot plant accompany the real stride.
            // The actor supplies the metre of forward travel; this is local bob.
            const float Step=FMath::Clamp((Elapsed-RuneSwordThrustRhythm::LungeStart)/
                (RuneSwordThrustRhythm::LungeEnd-RuneSwordThrustRhythm::LungeStart),0.f,1.f);
            const float Lower=FMath::Square(FMath::Sin(PI*Step));
            Location.Z-=3.5f*Lower;Rotation.Pitch+=1.2f*Lower;
            const float Landing=FMath::Clamp((Elapsed-RuneSwordThrustRhythm::LungeEnd)/.16f,0.f,1.f);
            const float Plant=FMath::Square(FMath::Sin(PI*Landing))*(1.f-Landing);
            Location.Z-=2.4f*Plant;Rotation.Pitch+=.8f*Plant;
        }
    }
    else if(bAttacking && bPommelAttack)
    {
        // Slow load, one fast drive, hard stop, then the weight draws back. The
        // strike uses the same fast-start curve as the pose, so camera and weapon
        // spend the 0.29 m of counterweight travel together.
        const FVector LoadLocation(-10.f,3.2f,2.1f),FollowLocation(15.f,-.8f,-4.2f);
        const FRotator LoadRotation(3.2f,-2.4f,-3.1f),FollowRotation(-4.6f,2.6f,4.2f);
        if(Elapsed<=ContactStart)
        {
            const float Gather=FMath::SmoothStep(0.f,RuneSwordPommelRhythm::RaiseEnd,Elapsed);
            Location=LoadLocation*Gather;Rotation=LoadRotation*Gather;
        }
        else if(Elapsed<=RuneSwordPommelRhythm::ExtensionEnd)
        {
            const float U=(Elapsed-ContactStart)/(RuneSwordPommelRhythm::ExtensionEnd-ContactStart);
            const float Push=1.f-FMath::Pow(1.f-U,2.2f),Burst=FMath::Square(FMath::Sin(PI*U));
            Location=FMath::Lerp(LoadLocation,FollowLocation,Push);Location.X+=7.f*Burst;
            Rotation=FMath::Lerp(LoadRotation,FollowRotation,Push);
            Rotation.Pitch+=2.2f*Burst*FMath::Sin(U*PI*4.f);
            Rotation.Roll+=1.6f*Burst*FMath::Sin(U*PI*5.f);
        }
        else
        {
            float Weight;
            if(Elapsed<=RuneSwordPommelRhythm::ArrestEnd)
                Weight=1.f+.12f*FMath::Sin(PI*(Elapsed-RuneSwordPommelRhythm::ExtensionEnd)/(RuneSwordPommelRhythm::ArrestEnd-RuneSwordPommelRhythm::ExtensionEnd));
            else if(Elapsed<=RuneSwordPommelRhythm::ReturnCorner)
                Weight=FMath::Lerp(1.f,.22f,FMath::SmoothStep(RuneSwordPommelRhythm::ArrestEnd,RuneSwordPommelRhythm::ReturnCorner,Elapsed));
            else
                Weight=.22f*(1.f-FMath::SmoothStep(RuneSwordPommelRhythm::ReturnCorner,RuneSwordPommelRhythm::AttackEnd,Elapsed));
            Location=FollowLocation*Weight;Rotation=FollowRotation*Weight;
        }
        if(bLungeStarted)
        {
            // Same weight shift and foot plant as the thrust, scaled to the short step.
            const float Step=FMath::Clamp((Elapsed-RuneSwordPommelRhythm::LungeStart)/
                (RuneSwordPommelRhythm::LungeEnd-RuneSwordPommelRhythm::LungeStart),0.f,1.f);
            const float Lower=FMath::Square(FMath::Sin(PI*Step));
            Location.Z-=2.4f*Lower;Rotation.Pitch+=.9f*Lower;
            const float Landing=FMath::Clamp((Elapsed-RuneSwordPommelRhythm::LungeEnd)/.14f,0.f,1.f);
            const float Plant=FMath::Square(FMath::Sin(PI*Landing))*(1.f-Landing);
            Location.Z-=1.8f*Plant;Rotation.Pitch+=.6f*Plant;
        }
    }
    else if(bAttacking)
    {
        const float Direction=CurrentClip==TEXT("Slash2")?1.f:-1.f;
        const float SourceTime=bHeavyAttack?RuneSwordHeavyRhythm::CameraSourceTime(Elapsed):RuneSwordRhythm::SourceTime(Elapsed);
        // Authored centimeters/degrees: a committed body turn before the
        // character's existing camera presentation scale is applied.
        const float LoadStrength=bHeavyAttack?1.3f:1.f, ReleaseStrength=bHeavyAttack?1.5f:1.f;
        const FVector LoadLocation=FVector(-10.f,-Direction*6.f,2.4f)*LoadStrength;
        const FRotator LoadRotation=FRotator(6.f,-Direction*7.f,-Direction*5.f)*LoadStrength;
        const FVector FollowLocation=FVector(16.f,Direction*11.f,-9.f)*ReleaseStrength;
        const FRotator FollowRotation=FRotator(-9.f,Direction*12.f,Direction*10.f)*ReleaseStrength;
        if(Elapsed<=ContactStart)
        {
            const float Gather=FMath::SmoothStep(0.f,.40f,SourceTime);
            Location=LoadLocation*Gather;Rotation=LoadRotation*Gather;
        }
        else if(Elapsed<=ContactEnd)
        {
            const float U=(Elapsed-ContactStart)/(ContactEnd-ContactStart);
            const float Across=U*U*(2.f-U);
            const float Burst=FMath::Square(FMath::Sin(PI*U));
            Location=FMath::Lerp(LoadLocation,FollowLocation,Across);
            Location.X+=10.f*Burst*ReleaseStrength;
            Rotation=FMath::Lerp(LoadRotation,FollowRotation,Across);
            // A brief directional vibration rides the release; it is silent
            // during the held load pose and vanishes at the phase boundary.
            Rotation.Pitch+=1.7f*Burst*FMath::Sin(U*PI*6.f)*ReleaseStrength;
            Rotation.Roll+=Direction*2.2f*Burst*FMath::Sin(U*PI*4.f)*ReleaseStrength;
        }
        else
        {
            // Follow the cut, arrest its weight, then draw back with the hands.
            // A sign-changing spring here fought the accepted diagonal path.
            float Weight;
            if(SourceTime<=1.115f)
                Weight=1.f+.10f*FMath::SmoothStep(1.015f,1.115f,SourceTime);
            else if(SourceTime<=1.34f)
                Weight=FMath::Lerp(1.10f,.30f,FMath::SmoothStep(1.115f,1.34f,SourceTime));
            else
                Weight=.30f*(1.f-FMath::SmoothStep(1.34f,1.65f,SourceTime));
            Location=FollowLocation*Weight;Rotation=FollowRotation*Weight;
        }
    }
    // Confirmed contact gives one damped impulse per slash. Multi-target
    // sweeps keep their damage but cannot stack camera shake indefinitely.
    const float ImpactSpan=bPommelAttack?.30f:.20f;
    if(!bOverheadAttack&&!bQuickCombatContactDone&&ImpactAge<ImpactSpan)
    {
        // A counterweight lands heavier than a blade pass: longer shake, bigger
        // axial recoil and a pitch punch on top of it.
        const float Envelope=1.f-FMath::SmoothStep(0.f,ImpactSpan,ImpactAge);
        const float Kick=FMath::Exp(-(bPommelAttack?13.f:17.f)*ImpactAge)*FMath::Sin((bPommelAttack?48.f:55.f)*ImpactAge)*Envelope;
        if(bPommelAttack)
        {
            Location+=FVector(-18.f,0.f,2.8f)*Kick*ImpactStrength;
            Rotation+=FRotator(10.5f,0.f,1.6f)*Kick*ImpactStrength;
        }
        else
        {
            Location+=(bThrustImpact?FVector(-12.f,0.f,1.4f):FVector(-8.f,ImpactDirection*3.f,2.f))*Kick*ImpactStrength;
            Rotation+=(bThrustImpact?FRotator(7.f,0.f,.8f):FRotator(6.f,ImpactDirection*2.8f,-ImpactDirection*4.4f))*Kick*ImpactStrength;
        }
    }
    // Scale the sword's directional travel and impact vibration together.
    // Other camera effects keep their own existing amplitude.
    constexpr float SwordCameraStrength=1.5f;
    Location*=SwordCameraStrength;
    Rotation*=SwordCameraStrength;
    // Add after the sword-only multiplier so all weapon categories receive
    // the same impulse, with the shared character comfort scale applied once.
    if(bQuickCombatContactDone)QuickCombatImpactShake::Add(ImpactAge,Location,Rotation);
}

void URuneSwordComponent::StartRift(float SourceAge)
{
    const int32 Index=bOverheadAttack?5:(bThrustAttack?3:(bPommelAttack?4:(bHeavyAttack?2:(CurrentClip==TEXT("Slash2")?1:0))));
    // Existing live instances may still have the five original slash ribbons.
    if(bOverheadAttack && (!RiftMeshes.IsValidIndex(Index) || !RiftMeshes[Index]))
    {
        RiftMeshes.SetNum(6);
        RiftMeshes[Index]=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/AzureRunesword20260913/SprintOverhead20260920/SM_RuneRift_Overhead"));
    }
    if(!RiftVisual || !RiftMaterial || !RiftMeshes.IsValidIndex(Index) || !RiftMeshes[Index])return;
    RiftVisual->SetStaticMesh(RiftMeshes[Index]);
    // The crescent is authored from the same blade trajectory as the contact
    // animation. Freeze its launch transform in world space so it can drift out.
    RiftOrigin=Viewmodel->GetComponentTransform();RiftDirection=Camera->GetForwardVector();
    if(bOverheadAttack)
    {
        // Reveal top-to-bottom in the stable aiming plane. Camera kick and the
        // sprint viewmodel's residual roll must not tilt this into a side slash.
        const FTransform Aim=Character->GetMeleeAimTransform();
        RiftOrigin=FTransform(Aim.GetRotation()*FRotator(0,90,0).Quaternion(),Aim.GetLocation());
        RiftDirection=-Aim.GetUnitAxis(EAxis::Z);
    }
    const float FastEnd=bOverheadAttack?RuneSwordOverheadFeel::ImpactTime:(bThrustAttack?RuneSwordThrustRhythm::ExtensionEnd:(bPommelAttack?RuneSwordPommelRhythm::ExtensionEnd:ContactEnd));
    RiftFastSeconds=(FastEnd-ContactStart)/SwingRate;
    RiftDissolveSeconds=bOverheadAttack?.26f:(bThrustAttack?.16f:(bPommelAttack?.14f:(bHeavyAttack?.28f:.20f)));
    RiftDriftSpeed=bOverheadAttack?95.f:(bThrustAttack?50.f:(bPommelAttack?42.f:(bHeavyAttack?120.f:85.f)));
    RiftMaterial->SetScalarParameterValue(TEXT("RiftStrength"),bOverheadAttack?.16f:(bThrustAttack?.10f:(bPommelAttack?.075f:(bHeavyAttack?.14f:.085f))));
    RiftAge=FMath::Max(0.f,SourceAge/SwingRate);bRiftActive=true;
    RiftVisual->SetVisibility(true);TickRift(0.f);
}

void URuneSwordComponent::TickRift(float Delta)
{
    if(!bRiftActive || !RiftVisual || !RiftMaterial)return;
    RiftAge+=Delta;
    if(RiftAge>=RiftFastSeconds+RiftDissolveSeconds){StopRift();return;}
    const float Recovery=FMath::Clamp((RiftAge-RiftFastSeconds)/RiftDissolveSeconds,0.f,1.f);
    const float Fade=1.f-Recovery*Recovery*(3.f-2.f*Recovery);
    RiftMaterial->SetScalarParameterValue(TEXT("SweepProgress"),FMath::Clamp(RiftAge/RiftFastSeconds,0.f,1.f)*1.06f);
    RiftMaterial->SetScalarParameterValue(TEXT("RiftFade"),Fade);
    FTransform Pose=RiftOrigin;Pose.AddToTranslation(RiftDirection*(RiftAge*RiftDriftSpeed));
    RiftVisual->SetWorldTransform(Pose);
}

void URuneSwordComponent::StopRift()
{
    bRiftActive=false;RiftAge=0.f;
    if(RiftVisual)RiftVisual->SetVisibility(false);
}

FRuneSwordBladeSample URuneSwordComponent::ReadBlade(const FTransform& AimFrame) const
{
    const FQuat ImportBasis=FRotator(0,90,0).Quaternion();
    FRuneSwordBladeSample Sample;
    // The rune sword already animates its Blade_Base/Tip tracks at the accepted
    // 80 percent size. Preserve those tracks when only splitting its surface.
    if(ModularSword&&!ModularSword->ComponentHasTag(TEXT("SwordTraceFromAnimation")))
    {
        const FTransform Frame=ModularSword->GetRelativeTransform()*Viewmodel->GetSocketTransform(TEXT("WPN_root"),RTS_Component);
        const auto Point=[&](FVector P){return AimFrame.TransformPosition(ImportBasis.RotateVector(Frame.TransformPosition(P)));};
        Sample={Point(ModularBladeBase),Point(ModularBladeTip),AimFrame.GetLocation(),AimFrame.GetUnitAxis(EAxis::X)};
    }
    else
    {
        const auto Point=[&](FName Bone){return AimFrame.TransformPosition(ImportBasis.RotateVector(
            Viewmodel->GetSocketTransform(Bone,RTS_Component).GetLocation()));};
        Sample={Point(TEXT("Blade_Base")),Point(TEXT("Blade_Tip")),AimFrame.GetLocation(),AimFrame.GetUnitAxis(EAxis::X)};
    }
    if(bPommelAttack)
    {
        // The fourth hit strikes with the counterweight, which sits behind the
        // guard: sample that end of the hilt instead of the blade, so the swept
        // volume is the striking face rather than a blade that is out of view.
        const FVector Axis=(Sample.Tip-Sample.Base).GetSafeNormal(SMALL_NUMBER,Sample.Forward);
        const FVector Guard=Sample.Base-Axis*RuneSwordPommelRhythm::BladeBaseCM;
        Sample.Base=Guard;
        Sample.Tip=Guard-Axis*PommelDepthCM;
    }
    return Sample;
}

void URuneSwordComponent::SweepBlade(const FRuneSwordBladeSample& From,const FRuneSwordBladeSample& To)
{
    if(bThrustAttack && !HitActors.IsEmpty())return;
    FRuneSwordTraceSettings Trace;
    Trace.Radius=RuneSwordCombat::BladeRadius*SwingRangeMultiplier;
    if(bPommelAttack)
    {
        // Blunt head, narrow forward corridor, one target: the counterweight does
        // not cleave like a blade pass and gets no thrust reach bonus.
        Trace.Radius=RuneSwordPommelRhythm::HeadRadius*SwingRangeMultiplier;
        Trace.ForwardCorridorRadius=RuneSwordPommelRhythm::CorridorRadius*SwingRangeMultiplier;
        Trace.bCleavePawns=false;
    }
    if(bThrustAttack)
    {
        Trace.Radius=RuneSwordThrustRhythm::BladeRadius*SwingRangeMultiplier;
        Trace.ForwardCorridorRadius=RuneSwordThrustRhythm::CorridorRadius*SwingRangeMultiplier;
        Trace.bCleavePawns=false;
    }
    auto* Pawn=Character.Get();
    auto Hits=RuneSwordCombat::Query(GetWorld(),Pawn,From,To,SwingReach,HitActors,Trace);
    if(SwingRangeMultiplier>1.f)
    {
        // Extend the tip's distance from the stable eye, retaining the hilt.
        // Keep the original blade pass as well so close contacts are not lost
        // when the expanded segment changes its angle around the hilt.
        auto ExtendedFrom=From,ExtendedTo=To;
        ExtendedFrom.Tip=From.Origin+(From.Tip-From.Origin)*SwingRangeMultiplier;
        ExtendedTo.Tip=To.Origin+(To.Tip-To.Origin)*SwingRangeMultiplier;
        Hits.Append(RuneSwordCombat::Query(GetWorld(),Pawn,ExtendedFrom,ExtendedTo,SwingReach,HitActors,Trace));
    }
    if((bThrustAttack || bPommelAttack) && Hits.Num()>1)
    {
        Hits.Sort([&](const FHitResult& A,const FHitResult& B)
        {
            return FVector::DotProduct(A.ImpactPoint-To.Origin,To.Forward)<
                FVector::DotProduct(B.ImpactPoint-To.Origin,To.Forward);
        });
        Hits.SetNum(1);
    }
    for(const FHitResult& Hit:Hits)
    {
            AActor* Target=Hit.GetActor();
            if(!IsValid(Target) || HitActors.Contains(Target))continue;
            HitActors.Add(Target);
            const FVector Direction=((To.Base+To.Tip)-(From.Base+From.Tip)).GetSafeNormal(SMALL_NUMBER,To.Forward);
            auto HitSkills=SwingSkills;
            if(SwingTrainingHits==1)if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())HitSkills.ExtraMasteryExperience=Profile->MasteryDefinition(TEXT("swordMastery")).MultiHitExperience;
            auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
            const bool Eligible=Combat&&!Combat->IsDead()&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
            FWeaponDamageResult DamageResult;
            auto ApplyDamage=[&](){return ColdSteelSkills::ApplyHit(Pawn,Hit,SwingDamage,Direction,HitSkills,&DamageResult);};
            const float Applied=Combat?Combat->ApplyHitWithReactionScale(SwingHitReactionMultiplier,ApplyDamage):ApplyDamage();
            // The contact cue belongs to the contact, not to the damage number: a
            // blow that kills still has to sound like a hit, and the damage pipeline
            // can report nothing once the victim dies to this very hit.
            const bool bKilled=Combat&&Combat->IsDead();
            // The fourth hit already sounded when its strike was released; every other
            // attack reports at the impact point, including a blow that kills.
            USoundBase* ImpactCue=bPommelAttack?nullptr:HitSound;
            if((Applied>0.f || bKilled) && ImpactCue)
                UGameplayStatics::PlaySoundAtLocation(this,ImpactCue,Hit.ImpactPoint,bOverheadAttack?.95f:(bHeavyAttack?.90f:.65f),
                    bOverheadAttack?.86f:(bHeavyAttack?.85f:(bThrustAttack?1.1f:(bPommelAttack?.9f:1.f))));
            if((Applied>0.f || (bOverheadAttack && bKilled)) && !bImpactFeedbackPlayed)
            {
                bImpactFeedbackPlayed=true;ImpactAge=0.f;
                bThrustImpact=bThrustAttack||bPommelAttack;
                ImpactDirection=CurrentClip==TEXT("Slash2")?1.f:-1.f;
                ImpactStrength=bOverheadAttack?1.25f:(bHeavyAttack?1.5f:(bPommelAttack?1.75f:1.f));
            }
            if(Applied>0)
            {
                // 快速进战：击退与眩晕由 ReceiveStun 一次提交；普通攻击只推退。
                if(Combat){if(bQuickCombatStrike)Combat->ReceiveStun(Pawn,QuickCombatStunSeconds,QuickCombatKnockbackCM);
                    else Combat->ReceiveMeleeKnockback(Pawn,SwingKnockbackCM);}
                // 快速进战击杀修炼：可修炼目标被本次打击直接击杀，挥击结束统一提交。
                if(bQuickCombatStrike&&Eligible&&bKilled)QuickCombatKillPending=true;
                if(Combat&&!Combat->IsDead()&&SwingRuneVulnerability>0)
                    if(auto* Status=UCombatStatusFormula::GetOrAdd(Target))Status->AddRuneMagicVulnerability(SwingRuneVulnerability,SwingRuneVulnerabilitySeconds);
                if(bHeavyTrainingPending&&Eligible){++HeavyTrainingHits;if(!IsValid(Target)||Combat->IsDead())++HeavyTrainingKills;}
                if(Target->FindComponentByClass<UMonsterCombatComponent>()&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining")))++SwingTrainingHits;
                Pawn->NotifyConfirmedWeaponHit(Target,Applied,&DamageResult);ColdSteelCombat::OnHit(Target,Pawn,SwingPoison);
            }
    }
}

void URuneSwordComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    if(!Viewmodel || !IsEquipped())return;
    if(TickGuardBreak(Delta))return;
    const bool Usable=CanUse();Viewmodel->SetVisibility(Usable && Viewmodel->GetSkeletalMeshAsset(),true);
    if(!Usable){if(IsBusy())CancelAction();ImpactAge=1.f;StopRift();return;}
    if((bCharging || bReturningCharge || bInspecting) && Character->IsCastBlockingLeftHandAction()){CancelAction();return;}
    ImpactAge=FMath::Min(1.f,ImpactAge+Delta);
    TickRift(Delta);
    if(bWhirlwind){TickWhirlwind(Delta);return;}
    if(TickGuard(Delta))return;
    if(!CurrentAnimation)return;
    const float End=CurrentAnimation->GetPlayLength();
    if(bAttacking)
    {
        const float Next=FMath::Min(End,Elapsed+Delta*SwingRate);
        const FTransform AimBeforeLunge=Character->GetMeleeAimTransform();
        const FVector LungeMoved=AdvanceThrustLunge(Elapsed,Next);
        const FTransform AimNow=Character->GetMeleeAimTransform();
        if((bThrustAttack || bPommelAttack) && bRiftActive)
        {
            // Carry the narrow rift with the actual step, including collision stops.
            RiftOrigin.AddToTranslation(LungeMoved);TickRift(0.f);
        }
        if(!bSwingCuePlayed && Next>=ContactStart)
        {
            bSwingCuePlayed=true;
            if(bPommelAttack && PommelHitSound)
            {
                // The fourth hit carries its own cue and replaces the shared sword swing
                // for this clip, so the counterweight reads as the striking end whether
                // or not the swing connects.
                UGameplayStatics::PlaySound2D(this,PommelHitSound,1.f,1.f);
            }
            else
            {
                if(AttackLayerSound)UGameplayStatics::PlaySound2D(this,AttackLayerSound,1.f,1.f);
                if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,bOverheadAttack?.90f:(bHeavyAttack?.95f:.72f),FMath::Clamp(SwingRate*(bOverheadAttack?.95f:(bHeavyAttack?.95f:(bThrustAttack?1.25f:1.1f))),.7f,1.4f));
            }
            StartRift(Next-ContactStart);
        }
        const auto FrameAt=[&](float Time)
        {
            // A hitch may run past the clip end. Aim still spans the full real
            // frame, rather than compressing all player movement into the clip.
            FTransform Frame;Frame.Blend(PreviousAimFrame,AimBeforeLunge,(Time-Elapsed)/FMath::Max(UE_SMALL_NUMBER,Delta*SwingRate));
            // Attribute real capsule displacement to the thrust's phase curve.
            // When blocked, the trace stops travelling with the blocked capsule.
            const float ForwardMoved=FVector::DotProduct(LungeMoved,LungeDirection);
            if(ForwardMoved>UE_SMALL_NUMBER)
            {
                const float Requested=bThrustAttack?
                    RuneSwordThrustRhythm::LungeDistance*(RuneSwordThrustRhythm::LungeAlpha(Time)-RuneSwordThrustRhythm::LungeAlpha(Elapsed)):
                    RuneSwordPommelRhythm::LungeDistance*(RuneSwordPommelRhythm::LungeAlpha(Time)-RuneSwordPommelRhythm::LungeAlpha(Elapsed));
                Frame.AddToTranslation(LungeMoved*FMath::Clamp(Requested/ForwardMoved,0.f,1.f));
            }
            return Frame;
        };
        const float HitStart=FMath::Max(Elapsed,ContactStart),HitEnd=FMath::Min(Next,ContactEnd);
        if(bQuickCombatStrike)
        {
            // 快速进战不走动画路径采样：配重接触帧（ExtensionEnd）只做一次
            // 手枪同款合同判定；走廊/遮挡/沿挥击弧线的旧闸门全部不再参与。
            if(!bQuickCombatContactDone&&Next>=RuneSwordPommelRhythm::ExtensionEnd)
            {
                bQuickCombatContactDone=true;
                SamplePose(RuneSwordPommelRhythm::ExtensionEnd);
                QuickCombatContractHit();
            }
        }
        else if(HitEnd>HitStart)
        {
            const FTransform StartFrame=FrameAt(HitStart),EndFrame=FrameAt(HitEnd);
            const float AimTravel=FVector::Distance(StartFrame.GetLocation(),EndFrame.GetLocation())+
                SwingReach*StartFrame.GetRotation().AngularDistance(EndFrame.GetRotation());
            const float SampleRate=bOverheadAttack?RuneSwordOverheadRhythm::SampleRate:(bThrustAttack?RuneSwordThrustRhythm::SampleRate:(bPommelAttack?RuneSwordPommelRhythm::SampleRate:(bHeavyAttack?RuneSwordHeavyRhythm::SampleRate:240.f)));
            const float TraceRadius=(bThrustAttack?RuneSwordThrustRhythm::BladeRadius:(bPommelAttack?RuneSwordPommelRhythm::HeadRadius:RuneSwordCombat::BladeRadius))*SwingRangeMultiplier;
            const int32 Steps=FMath::Max(1,FMath::Max(FMath::CeilToInt((HitEnd-HitStart)*SampleRate),FMath::CeilToInt(AimTravel/TraceRadius)));
            SamplePose(HitStart);FRuneSwordBladeSample Previous=ReadBlade(StartFrame);
            for(int32 Step=1;Step<=Steps;++Step)
            {
                const float T=FMath::Lerp(HitStart,HitEnd,float(Step)/Steps);
                SamplePose(T);const auto Current=ReadBlade(FrameAt(T));SweepBlade(Previous,Current);Previous=Current;
            }
        }
        if(bHeavyTrainingPending&&Next>=ContactEnd)FinishHeavyTraining();
        SamplePose(Next);PreviousAimFrame=AimNow;
        Elapsed=Next;
        if(Elapsed>=End)
        {
            const bool Queued=bQueuedAttack;const bool QueuedSkill=bQueuedQuickCombat;
            bAttacking=bQueuedAttack=bHeavyAttack=bThrustAttack=bPommelAttack=bOverheadAttack=bQuickCombatStrike=false;
            bQueuedQuickCombat=false;
            // Keep the completed query marker for the short camera tail.
            // StartSwing and CancelAction reset it before another action.
            bLungeStarted=bLungeBlocked=false;LastAttackEnd=GetWorld()->GetTimeSeconds();
            if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
            {
                // 冷却在挥击结束后才起跳；击杀修炼随挥击统一提交。
                Profile->FinishQuickCombatCast();
                if(QuickCombatKillPending)Profile->TrainQuickCombat(Profile->QuickCombatDefinition().KillExperience);
            }
            QuickCombatKillPending=false;
            SetClip(TEXT("Idle"),true);
            if(QueuedSkill)BeginQuickCombatStrike();else if(Queued)BeginAttack();
        }
    }
    else if(bCharging)
    {
        Elapsed=FMath::Min(float(GetWorld()->GetTimeSeconds()-ChargeStartedAt)/RequiredChargeSeconds,1.f)*RuneSwordHeavyRhythm::ChargeSeconds;
        SamplePose(Elapsed); // Retiming keeps the authored charge pose synchronized with the skill clock.
        if(bAutoHeavyRelease&&GetWorld()->GetTimeSeconds()-ChargeStartedAt>=RequiredChargeSeconds)ReleaseHeavyCharge();
    }
    else if(bReturningCharge)
    {
        CancelChargeAge=FMath::Min(CancelChargeDuration,CancelChargeAge+Delta);
        Elapsed=CancelChargeFrom*(1.f-FMath::SmoothStep(0.f,CancelChargeDuration,CancelChargeAge));
        SamplePose(Elapsed); // Reverse the same supported two-hand path, without damage.
        if(CancelChargeAge>=CancelChargeDuration){bReturningCharge=false;SetClip(TEXT("Idle"),true);}
    }
    else if(bInspecting)
    {
        Elapsed=FMath::Min(End,Elapsed+Delta);SamplePose(Elapsed);
        if(Elapsed>=End){bInspecting=false;SetClip(TEXT("Idle"),true);}
    }
    else if(bEquipping)
    {
        Elapsed=FMath::Min(End,Elapsed+Delta);SamplePose(Elapsed);
        if(Elapsed>=End){const bool Queued=bQueuedAttack;bEquipping=bQueuedAttack=false;SetClip(TEXT("Idle"),true);if(Queued)BeginAttack();}
    }
    else
    {
        const FName Clip=Character->GetVelocity().SizeSquared2D()>400?TEXT("Walk"):TEXT("Idle");
        if(Clip!=CurrentClip)SetClip(Clip,true);
        if(CurrentAnimation){Elapsed=FMath::Fmod(Elapsed+Delta*(Character->IsSprinting()?1.45f:1.f),FMath::Max(.01f,CurrentAnimation->GetPlayLength()));SamplePose(Elapsed);}
    }
    const bool Sprint=Character->IsSprinting() && !IsBusy();
    Viewmodel->SetRelativeLocation(FMath::VInterpTo(Viewmodel->GetRelativeLocation(),Sprint?FVector(-4,0,-9):FVector::ZeroVector,Delta,9.f));
    Viewmodel->SetRelativeRotation(FMath::RInterpTo(Viewmodel->GetRelativeRotation(),FRotator(0,90,Sprint?22:0),Delta,9.f));
}

void URuneSwordComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    FinishWhirlwind();
    FinishHeavyTraining();
    // Release a cast that ended with teardown instead of a finished swing, so the
    // cooldown starts and the reserved flag is not left set for the next session.
    if(auto* Profile=GetWorld()?GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr)Profile->FinishQuickCombatCast();
    ClearGuard();
    bAttacking=bEquipping=bInspecting=bQueuedAttack=bCharging=bReturningCharge=bHeavyAttack=false;HitActors.Reset();
    bThrustAttack=bPommelAttack=bOverheadAttack=bLungeStarted=bLungeBlocked=false;
    ImpactAge=1.f;
    if(ModularSword){ColdSteelModularSword::Clear(ModularSword);ModularSword->DestroyComponent();ModularSword=nullptr;}
    if(Viewmodel)Viewmodel->DestroyComponent();
    if(RiftVisual)RiftVisual->DestroyComponent();
    Super::EndPlay(Reason);
}
