#include "ProductionToolComponent.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "ProductionToolAppearance.h"
#include "ProductionPickaxeImpactMotion.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "ProductionHarvestSubsystem.h"
#include "ProductionTreeHealth.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelPickup.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "HAL/IConsoleManager.h"
#include "Camera/CameraComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "Particles/ParticleSystem.h"
#include "Sound/SoundBase.h"

namespace
{
    // The shovel digs where the crosshair points; the heightfield keeps its 20 cm
    // layer rule, so one swing is one whole layer instead of a melee poke.
    // The shovel is an aiming tool, not a melee reach: without this it could only hit
    // ground inside 3.2 m, i.e. straight down at the player's feet.
    static TAutoConsoleVariable<float> ToolDigReach(
        TEXT("fps.Tool.DigReach"), 1000.f,
        TEXT("Shovel aim trace length in cm; the shovel digs where the crosshair points."));
    FSoftObjectPath HarvestMotionPath(const FString& Prefix,const TCHAR* Clip)
    {
        const FString Package=Prefix+Clip;
        return FSoftObjectPath(Package+TEXT(".")+FPackageName::GetLongPackageAssetName(Package));
    }
}

UProductionToolComponent::UProductionToolComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}

void UProductionToolComponent::BeginPlay()
{
    Super::BeginPlay();LoadEnchantmentAnchors();
    auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner()); Character=Pawn;
    auto* World=GetWorld();
    auto* GameInstance=World?World->GetGameInstance():nullptr;
    // Preview worlds also report standalone. They have no player inventory and
    // can receive BeginPlay while a different world's pawn is being spawned.
    if (!Pawn || !GameInstance || (World->WorldType!=EWorldType::Game && World->WorldType!=EWorldType::PIE) || Pawn->GetNetMode()!=NM_Standalone)
    { SetComponentTickEnabled(false); return; }
    AddTickPrerequisiteActor(Pawn);
    AxeMotion.Load();
    Camera=Pawn->FindComponentByClass<UCameraComponent>();
    Pivot=NewObject<USceneComponent>(Pawn,TEXT("ProductionToolPivot"));
    Pawn->AddInstanceComponent(Pivot); Pivot->SetupAttachment(Camera); Pivot->RegisterComponent();
    Pivot->SetRelativeLocation(FVector(55,24,-35));
    ToolMesh=NewObject<UStaticMeshComponent>(Pawn,TEXT("ProductionToolMesh"));
    Pawn->AddInstanceComponent(ToolMesh); ToolMesh->SetupAttachment(Pivot);
    ToolMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision); ToolMesh->SetCanEverAffectNavigation(false);
    ToolMesh->SetCastShadow(false); ToolMesh->SetOnlyOwnerSee(true); ToolMesh->SetVisibility(false); ToolMesh->RegisterComponent();
    Viewmodel=NewObject<UFPSCastingMeshComponent>(Pawn,TEXT("ProductionToolHands"));
    Pawn->AddInstanceComponent(Viewmodel); Viewmodel->SetupAttachment(Camera);
    Viewmodel->SetRelativeRotation(FRotator(0,90,0));
    Viewmodel->SetCollisionEnabled(ECollisionEnabled::NoCollision); Viewmodel->SetCanEverAffectNavigation(false);
    Viewmodel->SetCastShadow(false); Viewmodel->SetOnlyOwnerSee(true); Viewmodel->bReceivesDecals=false;
    Viewmodel->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Viewmodel->RegisterComponent(); Viewmodel->SetVisibility(false);
    // Sample once from the harvest clock; hidden tools do not evaluate animation.
    Viewmodel->SetComponentTickEnabled(false);
    if (auto* Profile=GameInstance->GetSubsystem<UColdSteelStatusModel>()) Profile->GrantProductionTools();
    RefreshHeldTool();
}

/**
 * 采集工具改造实值落地：距离与宽容半径供射线判定使用，RateScale 供作者节奏换算使用。
 * 铁铲没有目录条目，Evaluate 返回出厂倍率，行为与改造前一致。
 *
 * 强化外观也挂在这里：`RefreshHeldTool` 的路径 ②（同实例只改数据）与路径 ③（换实例）
 * 都会走到本函数，而等级写在物品 Data 里、改等级必然改 `DataHash`，必然落到路径 ②。
 * 若把 `ApplyLevel` 只挂在路径 ③ 的资源加载完成回调之后，「应用强化」后手上工具不换材质。
 * 资源未加载完时两处调用都是安全的空操作（空组件／空资产＝找不到槽，保持现状）。
 */
void UProductionToolComponent::ApplyToolStats(const FColdSteelItem* Item,UColdSteelStatusModel* Profile)
{
    ToolStats=Item?ColdSteelTool::Evaluate(*Item,Profile):FProductionToolStats{};
    RateScale=float(FMath::Clamp(ToolStats.RateScale,.25,4.));
    if(Kind==TEXT("axe") || Kind==TEXT("pickaxe"))
    {
        AxeHarvestReach=float(ToolStats.HarvestReachCM);
        AxeCombatReach=float(ToolStats.CombatReachCM);
        AxeHarvestRadius=float(ToolStats.HarvestRadiusCM);
        AxeCombatRadius=float(ToolStats.CombatRadiusCM);
    }
    // 世界网格与第一人称视模各一次；用实例等级，不传 override。
    if(Item)
    {
        ProductionToolAppearance::ApplyLevel(ToolMesh,*Item);
        ProductionToolAppearance::ApplyLevel(Viewmodel,*Item);
    }
}

void UProductionToolComponent::RefreshHeldTool()
{
    if (!ToolMesh) return;
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* Item=Profile?Profile->ActiveProductionTool():nullptr;
    const FString Id=Item?Item->InstanceId:FString();
    // 改造应用会改写物品 Data：同一实例改了配件也要重新取数值，但资源不必重新请求。
    const uint32 DataHash=Item?GetTypeHash(Item->Data):0u;
    if (Id==EquippedId && DataHash==EquippedDataHash) return;
    // 同一实例只是改造数据变了：保留已加载的视模与动作，只重算数值，手上工具不闪帧。
    if (Id==EquippedId && Item) { EquippedDataHash=DataHash; ApplyToolStats(Item,Profile); return; }
    CancelUse(); EquippedId=Id; EquippedDataHash=DataHash; Kind.Reset(); Feedback.Reset();
    ToolMesh->SetVisibility(false); ToolMesh->SetStaticMesh(nullptr); HitSound=nullptr; SwingSound=nullptr;
    Viewmodel->SetVisibility(false); Viewmodel->SetSkeletalMesh(nullptr);
    CurrentMotion=nullptr; Motions.Reset(); bUsesArms=false; VisualTime=0; SprintBlend=0;
    AxeStridePhase=0; AxeLocomotionOffset=FVector::ZeroVector; AxeLocomotionRotation=FQuat::Identity;
    Viewmodel->SetRelativeLocationAndRotation(FVector::ZeroVector,FRotator(0,90,0));
    if (LoadHandle) { LoadHandle->CancelHandle(); LoadHandle.Reset(); }
    if (!Item) { ToolStats=FProductionToolStats{}; RateScale=1.f; return; }
    Kind=ColdSteelInventory::Text(*Item,TEXT("tool_kind")); ToolName=ColdSteelInventory::Text(*Item,TEXT("name"));
    if(Kind==TEXT("axe")||Kind==TEXT("pickaxe"))
        if(auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>())Harvest->Prepare(Kind==TEXT("axe"));
    ApplyToolStats(Item,Profile);
    SwingSeconds=FMath::Max(.4f,float(ColdSteelInventory::Number(*Item,TEXT("swing_seconds"),.68)));
    ContactSeconds=FMath::Clamp(float(ColdSteelInventory::Number(*Item,TEXT("contact_seconds"),.24)),.1f,SwingSeconds-.1f);
    if(Kind==TEXT("axe"))
    {
        SwingSeconds=AxeMotion.SwingSeconds;
        ContactSeconds=AxeMotion.ContactSeconds;
    }
    const float Scale=ColdSteelInventory::Number(*Item,TEXT("tool_scale"),.65);
    ToolMesh->SetRelativeScale3D(FVector(Scale));
    ToolMesh->SetRelativeRotation(FRotator(ColdSteelInventory::Number(*Item,TEXT("mount_pitch")),
        ColdSteelInventory::Number(*Item,TEXT("mount_yaw")),ColdSteelInventory::Number(*Item,TEXT("mount_roll"))));
    const FSoftObjectPath MeshPath(ColdSteelInventory::Text(*Item,TEXT("tool_mesh")));
    const FSoftObjectPath SoundPath(ColdSteelInventory::Text(*Item,TEXT("tool_sound")));
    const FSoftObjectPath DustPath(TEXT("/Game/EasyBuildingSystem/Effects/PS_Dust.PS_Dust"));
    const FSoftObjectPath ViewmodelPath(ColdSteelInventory::Text(*Item,TEXT("tool_viewmodel")));
    const FSoftObjectPath SwingPath(ColdSteelInventory::Text(*Item,TEXT("tool_swing_sound")));
    const FString MotionPrefix=ColdSteelInventory::Text(*Item,TEXT("tool_animation_prefix"));
    bUsesArms=!ViewmodelPath.IsNull();
    TArray<FSoftObjectPath> Paths={SoundPath,DustPath};
    if(bUsesArms)
    {
        Paths.Add(ViewmodelPath);
        if(!SwingPath.IsNull())Paths.Add(SwingPath);
        for(const TCHAR* Clip:{TEXT("Idle"),TEXT("Walk"),TEXT("Equip"),TEXT("Swing"),TEXT("HitRecover")})
            if((Kind!=TEXT("axe") && Kind!=TEXT("pickaxe")) || FName(Clip)!=TEXT("Walk"))
                Paths.Add(HarvestMotionPath(MotionPrefix,Clip));
    }
    else Paths.Add(MeshPath);
    LoadHandle=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateWeakLambda(this,[this,Id,MeshPath,SoundPath,DustPath,ViewmodelPath,SwingPath,MotionPrefix]()
        {
            if (EquippedId!=Id || !ToolMesh) return;
            if(bUsesArms)
            {
                Viewmodel->SetSkeletalMesh(Cast<USkeletalMesh>(ViewmodelPath.ResolveObject()));
                for(const TCHAR* Clip:{TEXT("Idle"),TEXT("Walk"),TEXT("Equip"),TEXT("Swing"),TEXT("HitRecover")})
                    if((Kind!=TEXT("axe") && Kind!=TEXT("pickaxe")) || FName(Clip)!=TEXT("Walk"))
                        Motions.Add(FName(Clip),Cast<UAnimSequence>(HarvestMotionPath(MotionPrefix,Clip).ResolveObject()));
                SwingSound=Cast<USoundBase>(SwingPath.ResolveObject());
                if(HasReadyPresentation()){EquipElapsed=0; SampleMotion(TEXT("Equip"),0);}
            }
            else ToolMesh->SetStaticMesh(Cast<UStaticMesh>(MeshPath.ResolveObject()));
            // 资源是异步到位的：槽在 SetMesh 之前不存在，所以路径 ③ 必须在这里补一次。
            // 等级读当前物品 Data（与 EquippedId/DataHash 同步），重复设置同一 MI 幂等。
            auto* World=GetWorld(); auto* GameInstance=World?World->GetGameInstance():nullptr;
            auto* LiveProfile=GameInstance?GameInstance->GetSubsystem<UColdSteelStatusModel>():nullptr;
            if(const auto* Current=LiveProfile?LiveProfile->ActiveProductionTool():nullptr)
            {
                ProductionToolAppearance::ApplyLevel(ToolMesh,*Current);
                ProductionToolAppearance::ApplyLevel(Viewmodel,*Current);
            }
            HitSound=Cast<USoundBase>(SoundPath.ResolveObject()); ImpactDust=Cast<UParticleSystem>(DustPath.ResolveObject());
            Feedback=HasReadyPresentation()?((Kind==TEXT("axe") || Kind==TEXT("pickaxe"))?TEXT("双手工具 · 左键攻击 / 采集 · G / 滚轮切换武器"):TEXT("左键采集 · F7 收起工具")):TEXT("工具或手部动作加载失败，请重新装备");
            FeedbackSeconds=3.f;
        }));
}

bool UProductionToolComponent::CanUse() const
{
    auto* Pawn=Character.Get();
    const auto* PC=Pawn?Cast<APlayerController>(Pawn->GetController()):nullptr;
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    const auto* Building=PC?PC->FindComponentByClass<UVoxelBuildComponent>():nullptr;
    return !AFPSGAMEPlayerController::BlocksOngoingActions(PC) &&
        !Pawn->IsTraversing() && (!Health || !Health->IsDead()) && (!Building || !Building->IsBuilding());
}

void UProductionToolComponent::BeginUse()
{
    if(Character.IsValid() && Character->IsCastBlockingLeftHandAction())return;
    if (!IsEquipped() || !CanUse() || Elapsed>=0) return;
    if (!HasReadyPresentation()) { Feedback=TEXT("正在加载工具…"); FeedbackSeconds=1.f; return; }
    if(EquipElapsed>=0)return;
    AxeStrike={};
    if(auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
    {
        if(const auto* Item=Profile->ActiveProductionTool())
        {
            // 改造数值每次挥动重新求值：属性、配件与附魔变化都不能沿用上一次的快照。
            ApplyToolStats(Item,Profile);
            if(!Profile->SpendStamina(float(FMath::Max(0.,ToolStats.StaminaCost))))
            {Feedback=TEXT("体力不足，稍作休息再采集");FeedbackSeconds=1.5f;return;}
            if(Kind==TEXT("axe") || Kind==TEXT("pickaxe"))
            {
                // Capture after the stamina transaction, which can replace inventory data.
                AxeStrike=ColdSteelSkills::Snapshot(Character.Get(),Item);
                AxeStrike.bMelee=true;
                AxeStrike.DamagePanel=ToolStats.Damage;
                AxeStrike.ToughnessDamageMultiplier=float(ToolStats.ToughnessDamage);
                AxeStrike.CriticalChance=float(FMath::Clamp(double(AxeStrike.CriticalChance)+ToolStats.CriticalChanceAdd,0.,100.));
            }
        }
        else if(!Profile->SpendStamina(Profile->StaminaSettings().HarvestCost))
        {Feedback=TEXT("体力不足，稍作休息再采集");FeedbackSeconds=1.5f;return;}
    }
    Elapsed=0; bContacted=false; bHitConfirmed=false; bSwingSoundPlayed=false;
}

void UProductionToolComponent::CancelUse()
{
    if((Kind==TEXT("axe") || Kind==TEXT("pickaxe")) && (Elapsed>=0.f || EquipElapsed>=0.f))VisualTime=0.f;
    Elapsed=-1; EquipElapsed=-1; bContacted=false; bHitConfirmed=false; bSwingSoundPlayed=false;
    if (Pivot) Pivot->SetRelativeRotation(FRotator::ZeroRotator);
}

void UProductionToolComponent::ShowFeedback(const FString& Message)
{
    Feedback=Message; FeedbackSeconds=4.f;
}

bool UProductionToolComponent::TraceResource(FProductionResource& Resource,FHitResult& Hit,FString& Reason) const
{
    if(Kind==TEXT("axe") || Kind==TEXT("pickaxe"))
        return TraceAxeContact(Resource,Hit,Reason) && !Resource.Id.IsEmpty();
    if (!Camera || !Character.IsValid()) return false;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(ProductionTool),false,Character.Get());
    const FTransform Aim=Camera->GetComponentTransform();
    const FVector Start=Aim.GetLocation();
    const float Length=Kind==TEXT("shovel")?ToolDigReach.GetValueOnGameThread():Reach;
    if (!GetWorld()->LineTraceSingleByChannel(Hit,Start,Start+Aim.GetRotation().GetForwardVector()*Length,ECC_Visibility,Q))
    { Reason=TEXT("靠近树干、独立岩块或干燥地面（3.2 米内）"); return false; }
    for (TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
        if (It->ResolveProductionResource(Hit,Resource,Reason)) return true;
    if (Reason.IsEmpty()) Reason=TEXT("此物体不可采集，前往温带丘陵寻找资源");
    return false;
}

bool UProductionToolComponent::ResolveContact()
{
    FProductionResource Target; FHitResult Hit; FString Reason;
    const bool bCombatTool=Kind==TEXT("axe") || Kind==TEXT("pickaxe");
    const bool Found=bCombatTool?TraceAxeContact(Target,Hit,Reason):TraceResource(Target,Hit,Reason);
    // The shovel's trace still returns its blocking hit even when it is not soil.
    if(UWardBreakableGlass::BreakHit(Hit,(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal()))
    {Feedback=TEXT("玻璃已击碎");FeedbackSeconds=1.2f;return true;}
    if (!Found) { Feedback=Reason; FeedbackSeconds=2; return false; }
    if(bCombatTool && Target.Id.IsEmpty())return ResolveAxeEnemyContact(Hit);
    if (Kind!=Target.RequiredTool)
    {
        Feedback=Target.RequiredTool==TEXT("axe")?TEXT("砍树需要伐木斧：在背包右键装备到主手，再用 G / 滚轮切换"):
            Target.RequiredTool==TEXT("pickaxe")?TEXT("开采岩块需要矿镐：在背包右键装备到主手，再用 G / 滚轮切换"):TEXT("采集表土需要铁铲（8）");
        FeedbackSeconds=2; return false;
    }
    auto* Profile=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    bool Depleted=false;
    Target.Direction=(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal();
    if(Target.Layer==0 && !Target.bStump)
        if(auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>())Harvest->PrepareFall(Target);
    if (!Profile->CommitHarvestStrike(Target,Depleted)) { Feedback=Profile->ResultMessage(); FeedbackSeconds=3; return false; }
    Feedback=Profile->ResultMessage(); FeedbackSeconds=2;
    if (HitSound) UGameplayStatics::PlaySoundAtLocation(this,HitSound,Hit.ImpactPoint,.65f);
    if (ImpactDust&&(!Depleted||Target.Layer==2)) UGameplayStatics::SpawnEmitterAtLocation(GetWorld(),ImpactDust,Hit.ImpactPoint,Hit.ImpactNormal.Rotation(),FVector(.25f),true,EPSCPoolMethod::AutoRelease);
    if (Depleted && Target.World.IsValid()) Target.World->CompleteProductionHarvest(Target,Hit,Target.Direction);
    if (Depleted && Target.Layer==2)
    {
        // The world just removed one 20 cm layer; say so instead of only "collected".
        Feedback=TEXT("表土挖低 20 cm（继续左键下挖，右键回填）");
        FeedbackSeconds=3.f;
    }
    return true;
}

void UProductionToolComponent::BeginRefill()
{
    if(!IsEquipped()||IsBusy())return;
    if(Kind!=TEXT("shovel")){ShowFeedback(TEXT("回填地面需要铁铲（8）"));return;}
    if(!Camera||!Character.IsValid())return;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(ProductionTool),false,Character.Get());
    const FVector Start=Camera->GetComponentLocation();
    FHitResult Hit;
    if(!GetWorld()->LineTraceSingleByChannel(Hit,Start,Start+Camera->GetForwardVector()*ToolDigReach.GetValueOnGameThread(),ECC_Visibility,Q))
    {ShowFeedback(TEXT("瞄准地面再回填"));return;}
    FString Message;
    for(TActorIterator<ATemperateHillsWorld> It(GetWorld());It;++It)
        if(It->ApplySoilRefill(Hit.ImpactPoint,Message))break;
    if(Message.IsEmpty())Message=TEXT("这里不是可回填的地形");
    ShowFeedback(Message);
}

void UProductionToolComponent::AdvanceActionBeforeCamera(float Delta)
{
    // The owner calls this once, before its camera and before our presentation
    // tick. Contact audio, camera impulses and sampled arms see the same age.
    if(!Character.IsValid()||!Pivot)return;
    if(!IsEquipped()||!CanUse()){CancelUse();return;}
    if (Elapsed>=0)
    {
        Elapsed+=Delta;
        // 挥砍速度改造只压缩真实时钟：作者节奏与镜头关键帧按 RateScale 换算，
        // RateScale=1 时逐帧等于改造前。
        const float Contact=RealContactSeconds(), Swing=RealSwingSeconds();
        // The overhead pickaxe starts accelerating 100 ms before contact;
        // its whoosh belongs to that downstroke, after the raised hold.
        const float WhooshTime=(Kind==TEXT("axe")?AxeMotion.SwingSoundSeconds:
            (Kind==TEXT("pickaxe")?FMath::Max(0.f,ContactSeconds-.10f):ContactSeconds*.65f))/RateScale;
        if(bUsesArms && !bSwingSoundPlayed && Elapsed>=WhooshTime)
        {
            bSwingSoundPlayed=true;
            if(SwingSound)UGameplayStatics::PlaySound2D(this,SwingSound,.38f,Kind==TEXT("axe")?.86f:.76f);
        }
        // The shovel keeps its original procedural arc. Skeletal tools use the same
        // one-contact clock and resolve against the camera ray at the contact time.
        if(!bUsesArms)
        {
            float Angle;
            if (Elapsed<Contact) Angle=FMath::Lerp(-.45f,.95f,FMath::Square(Elapsed/FMath::Max(1e-3f,Contact)));
            else { const float T=FMath::Clamp((Elapsed-Contact)/FMath::Max(1e-3f,Swing-Contact),0.f,1.f); Angle=FMath::Lerp(.95f,0.f,T*T*(3-2*T)); }
            Pivot->SetRelativeRotation(FRotator(-FMath::RadiansToDegrees(Angle),0,FMath::RadiansToDegrees(Angle*.26f)));
        }
        if (!bContacted && Elapsed>=Contact)
        {
            bContacted=true; bHitConfirmed=ResolveContact();
            // Start the confirmed impact at zero age, even on a late frame, so
            // a hitch cannot skip the lodged pose and its first camera impulse.
            if(bHitConfirmed && (Kind==TEXT("axe") || Kind==TEXT("pickaxe")))Elapsed=Contact;
        }
        const float End=bHitConfirmed && Kind==TEXT("axe")?Contact+AxeMotion.HitRecoverSeconds/RateScale:
            bHitConfirmed && Kind==TEXT("pickaxe")?Contact+ProductionPickaxeImpact::HitRecoverSeconds/RateScale:Swing;
        if (Elapsed>=End) CancelUse();
    }
}

void UProductionToolComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    const bool Usable=IsEquipped() && CanUse();
    if (ToolMesh) ToolMesh->SetVisibility(Usable && !bUsesArms && ToolMesh->GetStaticMesh());
    if (Viewmodel) Viewmodel->SetVisibility(Usable && bUsesArms && HasReadyPresentation());
    if (!Usable) CancelUse();
    if(Usable && bUsesArms && HasReadyPresentation())UpdateHandPresentation(Delta);
    FeedbackSeconds=FMath::Max(0.f,FeedbackSeconds-Delta);
    HintCountdown-=Delta;
    if (HintCountdown<=0) { HintCountdown=.15f; UpdateHint(); }
}

void UProductionToolComponent::UpdateHint()
{
    // 2026-09-28 用户要求：使用采集工具时下方的白色提示字段全部删除——不再创建/显示
    // 提示控件（工具名与操作说明、瞄准详情、挥砍反馈都随之消失；采集结果仍走音效与
    // 画面表现）。保留空函数与 EndPlay 清理，回退时把旧实现搬回来即可。
    if (Prompt) Prompt->SetVisibility(ESlateVisibility::Collapsed);
}

void UProductionToolComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if (LoadHandle) { LoadHandle->CancelHandle(); LoadHandle.Reset(); }
    if (Prompt) { Prompt->RemoveFromParent(); Prompt=nullptr; }
    Super::EndPlay(Reason);
}
