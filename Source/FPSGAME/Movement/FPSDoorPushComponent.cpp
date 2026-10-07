#include "FPSDoorPushComponent.h"
#include "DoorPushAuthored20261002.h"
#include "DoorPushCameraShake.h"
#include "FPSCharacterMovementComponent.h"
#include "../Weapons/WeaponBipodDeploymentComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Building/ColdSteelDoor.h"
#include "../Building/ColdSteelDoubleDoor.h"
#include "../Building/ColdSteelSlidingDoor.h"
#include "../Building/ColdSteelRevolvingDoor.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowArrow.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/AssetManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Sound/SoundBase.h"

namespace
{
const FSoftObjectPath DoorPushArmsPath(TEXT("/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7.SK_M4_BareArmsV7"));
const FSoftObjectPath DoorPushImpactPath(TEXT("/Game/Audio/Interactions/DoorPush20261002/S_DoorPushImpact.S_DoorPushImpact"));
constexpr float DoorPushReachCm=210.f;
TAutoConsoleVariable<int32> CVarDoorPushDebug(
    TEXT("fps.DoorPush.Debug"),0,
    TEXT("撞门系统排查日志：1=在闸门链各节点输出原因（探测/起手/服务器复核/开门）。"));
bool DoorPushDebug(){return CVarDoorPushDebug.GetValueOnGameThread()!=0;}
bool IsClosedPushDoor(const AActor* Target)
{
    if(!IsValid(Target)||Target->ActorHasTag(TEXT("VoxelDetached")))return false;
    if(const auto* Single=Cast<AColdSteelDoor>(Target))return !Single->IsDoorOpen();
    if(const auto* Double=Cast<AColdSteelDoubleDoor>(Target))return !Double->IsWindowOpen();
    return false;
}
}

UFPSDoorPushComponent::UFPSDoorPushComponent()
{PrimaryComponentTick.bCanEverTick=false;SetIsReplicatedByDefault(true);}

void UFPSDoorPushComponent::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()==NM_DedicatedServer)return;
    auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    FallbackHands=NewObject<UFPSCastingMeshComponent>(GetOwner(),TEXT("DoorPushFallbackLeftArm"));
    GetOwner()->AddInstanceComponent(FallbackHands);FallbackHands->SetupAttachment(Camera);
    FallbackHands->SetCollisionEnabled(ECollisionEnabled::NoCollision);FallbackHands->SetCanEverAffectNavigation(false);
    FallbackHands->SetOnlyOwnerSee(true);FallbackHands->SetCastShadow(false);FallbackHands->bReceivesDecals=false;
    FallbackHands->SetVisibility(false);FallbackHands->RegisterComponent();FallbackHands->SetComponentTickEnabled(false);
    FallbackHands->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    FallbackHands->SetBoundsScale(2.f);
    FallbackHands->ComponentTags.AddUnique(TEXT("PreloadModularOutfit"));
    if(DoorPushArmsPath.ResolveObject())ApplyLoadedHands();
    // Keep both assets pinned for this component's lifetime, even if the arms
    // already arrived through an outfit preloader. Contact never loads from disk.
    const TArray<FSoftObjectPath> PreloadPaths{DoorPushArmsPath,DoorPushImpactPath};
    Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(PreloadPaths,
        FStreamableDelegate::CreateUObject(this,&UFPSDoorPushComponent::ApplyLoadedHands));
}

void UFPSDoorPushComponent::ApplyLoadedHands()
{
    auto* Asset=Cast<USkeletalMesh>(DoorPushArmsPath.ResolveObject());if(!Asset||!FallbackHands)return;
    FallbackHands->SetSkeletalMesh(Asset);
    if(const auto* Render=Asset->GetResourceForRendering())for(int32 L=0;L<Render->LODRenderData.Num();++L)
        for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
        {
            const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
            const FString Name=Asset->GetMaterials()[M].MaterialSlotName.ToString().ToLower();
            const bool Arm=!Name.Contains(TEXT("handguard"))&&(Name.Contains(TEXT("skin"))||Name.Contains(TEXT("manny"))||
                Name.Contains(TEXT("bare"))||Name.Contains(TEXT("glove"))||Name.Contains(TEXT("sleeve"))||
                Name==TEXT("hand")||Name==TEXT("hands")||Name.EndsWith(TEXT("_hands")));
            FallbackHands->ShowMaterialSection(M,S,Arm,L);
        }
    FallbackHands->HideBoneByName(TEXT("clavicle_r"),EPhysBodyOp::PBO_None);
    FallbackHands->HideBoneByName(TEXT("WPN_root"),EPhysBodyOp::PBO_None);
}

bool UFPSDoorPushComponent::CanStart(FString* OutReason) const
{
    auto Fail=[&](const TCHAR* Reason){if(OutReason)*OutReason=Reason;return false;};
    if(!FallbackHands)return Fail(TEXT("无FallbackHands"));
    if(!FallbackHands->GetSkeletalMeshAsset())return Fail(TEXT("裸臂资产未就绪"));
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Player)return Fail(TEXT("Owner非角色"));
    if(!Player->IsLocallyControlled())return Fail(TEXT("非本地控制"));
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC)return Fail(TEXT("无PlayerController"));
    if(PC->GetViewTarget()!=Player)return Fail(TEXT("视点非本角色"));
    if(AFPSGAMEPlayerController::BlocksOngoingActions(PC))return Fail(TEXT("操作被UI阻断"));
    if(Player->IsTraversing())return Fail(TEXT("翻越中"));
    if(Player->IsDodging())return Fail(TEXT("闪避中"));
    if(Player->IsSliding())return Fail(TEXT("滑铲中"));
    if(Player->IsSwitchingWeapon())return Fail(TEXT("切枪中"));
    // bIgnoreDoorPush=true：这里验证的就是"这次推"——同实例上 BeginPush 已置 bActive，
    // 含 DoorPush 项的谓词会把本次起手误当占用而恒拒（本机/主机必中）。并发已由
    // Advance 的 bActive 早退与服务端 ServerDoor 节流分管，不需要在这里再查一次。
    if(Player->IsLeftHandBusyForCast(true))
        return Fail(*FString::Printf(TEXT("左手施法占用[%s]"),*Player->DescribeLeftHandBusy(true)));
    if(Player->IsCastBlockingLeftHandAction(true))return Fail(TEXT("施法挡左手"));
    if(Player->IsSpellGestureBlocking(true))return Fail(TEXT("法术手势中"));
    if(const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return Fail(TEXT("死亡"));
    if(const auto* Bow=Player->FindComponentByClass<UBowWeaponComponent>();Bow&&Bow->IsEquipped()&&Bow->IsBusy())return Fail(TEXT("弓忙碌"));
    if(OutReason)*OutReason=TEXT("");
    return true;
}

bool UFPSDoorPushComponent::Probe(FHitResult& Hit) const
{
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    const auto* PC=Player?Cast<APlayerController>(Player->GetController()):nullptr;if(!PC)return false;
    FVector Eye;FRotator View;ColdSteelWorldInteraction::GetReachViewPoint(PC,Eye,View);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SprintDoorPush),false,Player);
    // Use the same first visible blocker and recoverable-arrow priority as E.
    TArray<FHitResult> TraceHits;
    GetWorld()->LineTraceMultiByChannel(TraceHits,Eye,Eye+View.Vector()*DoorPushReachCm,ECC_Visibility,Query);
    for(const auto& Result:TraceHits)
    {
        if(const auto* Arrow=Cast<ABowArrow>(Result.GetActor());Arrow&&Arrow->CanRecover())
        {if(DoorPushDebug())UE_LOG(LogTemp,Display,TEXT("[DoorPush] 探测：可回收箭矢优先，放弃"));return false;}
        if(Result.bBlockingHit)
        {
            const bool bDoor=IsClosedPushDoor(Result.GetActor());
            if(DoorPushDebug())UE_LOG(LogTemp,Display,TEXT("[DoorPush] 探测：首个遮挡=%s(%s) bBlocking=%d 是闭门=%d 距离=%.0fcm"),
                *GetNameSafe(Result.GetActor()),Result.GetActor()?*Result.GetActor()->GetClass()->GetName():TEXT("null"),
                Result.bBlockingHit?1:0,bDoor?1:0,float((Eye-Result.ImpactPoint).Size()));
            if(bDoor){Hit=Result;return true;}
            return false;
        }
    }
    if(DoorPushDebug())UE_LOG(LogTemp,Display,TEXT("[DoorPush] 探测：210cm 内无遮挡"));
    return false;
}

bool UFPSDoorPushComponent::BeginPush(const FHitResult& Hit)
{
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());if(!Player)return false;
    ActiveHands.Reset();USkeletalMeshComponent* Source=nullptr;
    const auto* Bow=Player->FindComponentByClass<UBowWeaponComponent>();
    if(!Bow||!Bow->IsEquipped())
    {
        TInlineComponentArray<UFPSCastingMeshComponent*> Meshes(Player);
        for(auto* Mesh:Meshes)if(Mesh!=FallbackHands&&Mesh->bApplyLeftHandCast&&Mesh->GetSkeletalMeshAsset()&&
            Mesh->IsVisible()&&!Mesh->bHiddenInGame&&Mesh->GetBoneIndex(TEXT("hand_l"))>=0)
        {ActiveHands=Mesh;Source=Mesh;break;}
    }
    else
    {
        TInlineComponentArray<USkeletalMeshComponent*> Meshes(Player);
        for(auto* Mesh:Meshes)if(Mesh!=FallbackHands&&Mesh->IsVisible()&&!Mesh->bHiddenInGame&&
            Mesh->GetName().Contains(TEXT("Bow"))&&Mesh->GetBoneIndex(TEXT("hand_l"))>=0)
        {Source=Mesh;break;}
        if(FallbackHands&&FallbackHands->GetSkeletalMeshAsset())ActiveHands=FallbackHands;
    }
    // Static tools have no native hand viewmodel. Enter/recover below the view
    // using the same canonical closed-fist idle example as the authored take.
    if(!Source&&FallbackHands&&FallbackHands->GetSkeletalMeshAsset())
    {
        ActiveHands=FallbackHands;Source=FallbackHands;
        FallbackHands->TickAnimation(0.f,false);FallbackHands->RefreshBoneTransforms();
    }
    if(!ActiveHands.IsValid()||!Source||!FallbackHands||!FallbackHands->GetSkeletalMeshAsset()||
        !PoseLayer.Capture(*ActiveHands.Get(),*Source,*FallbackHands->GetSkeletalMeshAsset(),
            Source==FallbackHands.Get()))
    {
        if(DoorPushDebug())UE_LOG(LogTemp,Display,TEXT("[DoorPush] 起手失败：姿态捕获不通过（ActiveHands=%s Source=%s）"),
            *GetNameSafe(ActiveHands.Get()),*GetNameSafe(Source));
        return false;
    }
    Door=LastDoor=Hit.GetActor();
    Age=0.f;bContactResolved=false;bActive=true;bAwaitingImpact=true;
    ++LocalSequence;ServerBeginPush(LocalSequence,Door.Get());
    return true;
}

float UFPSDoorPushComponent::GetPresentationWeight() const
{
    if(!bActive)return 0.f;
    namespace Motion=DoorPushAuthored20261002;
    if(Age>=Motion::RecoverStartSeconds)
        return 1.f-Motion::Ease((Age-Motion::RecoverStartSeconds)/Motion::RecoverySeconds);
    return Motion::Ease(Age/Motion::PrepareSeconds);
}

void UFPSDoorPushComponent::Advance(float Delta)
{
    if(GetOwner()->HasAuthority())AdvanceAuthority(Delta);
    auto* Player=Cast<AFPSGAMECharacter>(GetOwner());if(!Player||!Player->IsLocallyControlled()||Delta<=0.f)return;
    if(bActive)
    {
        const auto* PC=Cast<APlayerController>(Player->GetController());
        const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
        const auto* Body=Player->FindComponentByClass<UFPSPlayerBodyComponent>();
        if(!ActiveHands.IsValid()||!PC||PC->GetViewTarget()!=Player||Player->IsTraversing()||Player->IsDodging()||Player->IsSliding()||
            (Health&&Health->IsDead())||AFPSGAMEPlayerController::BlocksOngoingActions(PC))
        {Cancel();return;}
        Age+=Delta;
        if(Age>=DoorPushAuthored20261002::ContactSeconds&&!bContactResolved)
        {
            bContactResolved=true;
            ServerContactPush(LocalSequence);
        }
        if(Age>=DoorPushAuthored20261002::DurationSeconds)Cancel(true);
        return;
    }
    const auto* Movement=Player->GetCharacterMovement();
    // IsSprinting is refreshed from held Shift and forward input, not velocity.
    // A closed door can stop movement while the player still intends to sprint.
    const bool Sprint=Player->IsSprinting()&&Movement&&Movement->IsMovingOnGround();
    if(!Sprint)
    {
        if(DoorPushDebug()&&GetWorld()->GetTimeSeconds()-LastDebugAt>1.)
        {
            LastDebugAt=GetWorld()->GetTimeSeconds();
            FString Reason;
            const bool bCan=CanStart(&Reason);
            UE_LOG(LogTemp,Display,TEXT("[DoorPush] 未触发：IsSprinting=%d 移动中=%d CanStart=%d(%s)"),
                Player->IsSprinting()?1:0,Movement&&Movement->IsMovingOnGround()?1:0,
                bCan?1:0,*Reason);
        }
        SprintAge=ProbeAge=0.f;LastDoor.Reset();return;
    }
    SprintAge+=Delta;ProbeAge+=Delta;
    // The Shift tap remains a dodge. A sustained sprint alone can own this gesture.
    if(SprintAge<.21f||ProbeAge<1.f/30.f)return;
    FString StartReason;
    const bool bCan=CanStart(&StartReason);
    if(!bCan)
    {
        if(DoorPushDebug()&&GetWorld()->GetTimeSeconds()-LastDebugAt>1.)
        {
            LastDebugAt=GetWorld()->GetTimeSeconds();
            UE_LOG(LogTemp,Display,TEXT("[DoorPush] 冲刺中但CanStart拒绝：%s"),*StartReason);
        }
        return;
    }
    ProbeAge=0.f;FHitResult Hit;
    if(!Probe(Hit)){LastDoor.Reset();return;}
    // 一次起手被拒（服务端占用/LOS 复核）不能把这扇门锁死到冲刺结束：
    // Cancel 给 SameDoorRetryAt 一个短冷却，之后继续冲刺对着同一扇门允许重试。
    if(Hit.GetActor()==LastDoor.Get()&&GetWorld()->GetTimeSeconds()<SameDoorRetryAt)return;
    const FVector Forward=FRotator(0,Player->GetControlRotation().Yaw,0).Vector();
    const float Facing=FVector::DotProduct(Hit.ImpactNormal,Forward);
    if(Facing>-.55f)
    {
        if(DoorPushDebug())UE_LOG(LogTemp,Display,TEXT("[DoorPush] 朝向拒绝：法线点乘前向=%.2f（需≤-0.55）"),Facing);
        return;
    }
    // 尝试/拒绝类日志不进 cvar——"门没反应"类报告全靠它们定位；每帧探测类才走 fps.DoorPush.Debug。
    UE_LOG(LogTemp,Display,TEXT("[DoorPush] 触发起手：门=%s"),*GetNameSafe(Hit.GetActor()));
    // 锁存+冷却在触发点统一武装：BeginPush 早期失败（姿态捕获不过）不进入 Cancel 路径，
    // 不在这里兜底的话它会每个探测节拍（30Hz）重试并刷日志。
    LastDoor=Hit.GetActor();SameDoorRetryAt=GetWorld()->GetTimeSeconds()+.55f;
    if(!BeginPush(Hit))UE_LOG(LogTemp,Warning,TEXT("[DoorPush] BeginPush 返回失败"));
}

void UFPSDoorPushComponent::ApplyHandPose(UFPSCastingMeshComponent& Mesh)
{
    if(!bActive||ActiveHands.Get()!=&Mesh)return;
    PoseLayer.Apply(Mesh,Age);
}

void UFPSDoorPushComponent::UpdatePresentation()
{
    if(!FallbackHands)return;
    const bool Show=bActive&&ActiveHands.Get()==FallbackHands.Get();FallbackHands->SetVisibility(Show);
    if(Show){FallbackHands->TickAnimation(0.f,false);FallbackHands->RefreshBoneTransforms();}
}

void UFPSDoorPushComponent::Cancel(bool bCompleted)
{
    if(!bCompleted)bAwaitingImpact=false;
    // 失败/中止的一次尝试不该把 LastDoor 锁到冲刺结束：给同门重试一个短冷却。
    // 时长须大于服务器节流窗口 0.2s，否则重试会先撞上 LastServerRequest 拒收。
    if(!bCompleted&&LastDoor.IsValid()&&GetWorld())
        SameDoorRetryAt=GetWorld()->GetTimeSeconds()+.55f;
    if(!bCompleted&&bActive&&GetOwner()&&Cast<APawn>(GetOwner())->IsLocallyControlled())ServerCancelPush(LocalSequence);
    bActive=false;ActiveHands.Reset();Door.Reset();PoseLayer.Reset();
    if(FallbackHands)FallbackHands->SetVisibility(false);
}

void UFPSDoorPushComponent::EndPlay(const EEndPlayReason::Type Reason)
{Cancel();if(Load){Load->CancelHandle();Load.Reset();}Super::EndPlay(Reason);}

// RPCs travel on the owning pawn's component. Door actors remain server-owned.
bool UFPSDoorPushComponent::ServerCanInteract(AActor* Target,bool bSprint,FString* OutReason) const
{
    auto Fail=[&](const TCHAR* Reason){if(OutReason)*OutReason=Reason;return false;};
    const auto* Player=Cast<AFPSGAMECharacter>(GetOwner());
    if(!Player)return Fail(TEXT("Owner非角色"));
    if(!Player->HasAuthority())return Fail(TEXT("无权威"));
    if(!IsValid(Target)||Target->GetWorld()!=GetWorld())return Fail(TEXT("目标无效"));
    if(Target->ActorHasTag(TEXT("VoxelDetached")))return Fail(TEXT("门已脱筹"));
    if(!IsNativeDoor(Target))return Fail(TEXT("非本工程门/窗"));
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(!PC)return Fail(TEXT("无PlayerController"));
    if(AFPSGAMEPlayerController::BlocksOngoingActions(PC))return Fail(TEXT("操作被UI阻断"));
    if(const auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();Health&&Health->IsDead())return Fail(TEXT("死亡"));
    if(Player->IsTraversing())return Fail(TEXT("翻越中"));
    if(Player->IsDodging())return Fail(TEXT("闪避中"));
    if(Player->IsSliding())return Fail(TEXT("滑铲中"));
    if(Player->IsSwitchingWeapon())return Fail(TEXT("切枪中"));
    if(Player->IsLeftHandBusyForCast(true))
        return Fail(*FString::Printf(TEXT("左手施法占用[%s]"),*Player->DescribeLeftHandBusy(true)));
    if(Player->IsCastBlockingLeftHandAction(true))return Fail(TEXT("施法挡左手"));
    if(Player->IsSpellGestureBlocking(true))return Fail(TEXT("法术手势中"));
    if(Player->BipodDeployment&&Player->BipodDeployment->BlocksMovement())return Fail(TEXT("架枪限制移动"));
    const auto* Move=Cast<UFPSCharacterMovementComponent>(Player->GetCharacterMovement());
    if(bSprint)
    {
        if(!IsClosedPushDoor(Target))return Fail(TEXT("门非关闭态"));
        if(!Move)return Fail(TEXT("无移动组件"));
        if(!Move->IsMovingOnGround())return Fail(TEXT("不在地面"));
        if(Move->bWantsToSlide)return Fail(TEXT("滑铲意图"));
        const bool bSprintIntent=Player->IsLocallyControlled()?Player->IsSprinting():bool(Move->bWantsToSprint);
        if(!bSprintIntent)return Fail(TEXT("服务器侧无冲刺意图"));
    }
    FVector Eye=Player->GetMeleeAimTransform().GetLocation();FRotator Aim=Player->GetControlRotation();
    if(Player->IsLocallyControlled())ColdSteelWorldInteraction::GetReachViewPoint(PC,Eye,Aim);
    FCollisionQueryParams Params(SCENE_QUERY_STAT(NetDoorReach),false,Player);
    TArray<FHitResult> Hits;
    GetWorld()->LineTraceMultiByChannel(Hits,Eye,Eye+Aim.Vector()*(bSprint?DoorPushReachCm:250.f),ECC_Visibility,Params);
    for(const auto& Hit:Hits)
    {
        if(const auto* Arrow=Cast<ABowArrow>(Hit.GetActor());Arrow&&Arrow->CanRecover())return Fail(TEXT("可回收箭矢优先"));
        if(!Hit.bBlockingHit)continue;
        if(Hit.GetActor()!=Target)return Fail(TEXT("首个遮挡非目标门"));
        if(bSprint)
        {
            const float Facing=FVector::DotProduct(Hit.ImpactNormal,FRotator(0,Aim.Yaw,0).Vector());
            if(Facing>-.55f)return Fail(TEXT("服务器侧朝向拒绝"));
        }
        if(OutReason)*OutReason=TEXT("");
        return true;
    }
    return Fail(TEXT("服务器视线内无遮挡"));
}

void UFPSDoorPushComponent::ServerBeginPush_Implementation(uint16 Sequence,AActor* Target)
{
    const double Now=GetWorld()->GetTimeSeconds();
    FString Reason;
    const bool bOk=ServerCanInteract(Target,true,&Reason);
    // 拒收无条件进日志（稀有事件）；成功路径仍走 cvar。
    if(!bOk){UE_LOG(LogTemp,Warning,TEXT("[DoorPush] 服务器起手拒绝：目标=%s 序号=%d 原因=%s"),
        *GetNameSafe(Target),Sequence,*Reason);}
    else if(DoorPushDebug()){UE_LOG(LogTemp,Display,TEXT("[DoorPush] 服务器起手：目标=%s 序号=%d 结果=1"),
        *GetNameSafe(Target),Sequence);}
    if(ServerDoor.IsValid()||(LastServerRequest>=0.&&Now-LastServerRequest<.2)||!bOk)
    {
        if(bOk)UE_LOG(LogTemp,Warning,TEXT("[DoorPush] 服务器起手被节流拒绝：ServerDoor有效=%d 距上次=%.2fs"),
            ServerDoor.IsValid()?1:0,float(Now-LastServerRequest));
        ClientPushResult(Sequence,false);return;
    }
    LastServerRequest=Now;ServerSequence=Sequence;ServerDoor=Target;ServerAge=0.f;bServerContact=false;
}

void UFPSDoorPushComponent::ServerContactPush_Implementation(uint16 Sequence)
{
    if(Sequence==ServerSequence&&ServerDoor.IsValid())
    {bServerContact=true;AdvanceAuthority(0.f);}
}

void UFPSDoorPushComponent::ServerCancelPush_Implementation(uint16 Sequence)
{
    if(Sequence==ServerSequence){ServerDoor.Reset();bServerContact=false;}
}

void UFPSDoorPushComponent::AdvanceAuthority(float DeltaSeconds)
{
    if(!ServerDoor.IsValid())return;
    ServerAge+=DeltaSeconds;
    if(ServerAge>DoorPushAuthored20261002::DurationSeconds+.5f)
    {ServerDoor.Reset();ClientPushResult(ServerSequence,false);
     UE_LOG(LogTemp,Warning,TEXT("[DoorPush] 服务器超时未收到接触，回执失败"));return;}
    if(!bServerContact||ServerAge<DoorPushAuthored20261002::ContactSeconds)return;
    AActor* Target=ServerDoor.Get();ServerDoor.Reset();bServerContact=false;
    FString Reason;
    if(!ServerCanInteract(Target,true,&Reason))
    {ClientPushResult(ServerSequence,false);
     UE_LOG(LogTemp,Warning,TEXT("[DoorPush] 接触时刻服务器复核拒绝：%s"),*Reason);return;}
    const auto* Player=Cast<APawn>(GetOwner());
    bool bOpened=false;
    if(auto* Single=Cast<AColdSteelDoor>(Target))bOpened=Single->OpenDoorFrom(Player);
    else if(auto* Double=Cast<AColdSteelDoubleDoor>(Target))bOpened=Double->OpenWindowFrom(Player);
    if(!bOpened){UE_LOG(LogTemp,Warning,TEXT("[DoorPush] 接触时刻开门失败：门=%s（两侧摆动空间被挡）"),*GetNameSafe(Target));}
    else if(DoorPushDebug()){UE_LOG(LogTemp,Display,TEXT("[DoorPush] 接触时刻开门：门=%s"),*GetNameSafe(Target));}
    ClientPushResult(ServerSequence,bOpened);
    if(bOpened)MulticastPushImpact(Target->GetActorLocation()+FVector(0,0,100));
}

void UFPSDoorPushComponent::ClientPushResult_Implementation(uint16 Sequence,bool bOpened)
{
    if(Sequence!=LocalSequence||!bAwaitingImpact)return;
    bAwaitingImpact=false;
    if(!bOpened){UE_LOG(LogTemp,Warning,TEXT("[DoorPush] 客户端收到失败回执，取消动作"));Cancel();return;}
    if(DoorPushDebug())UE_LOG(LogTemp,Display,TEXT("[DoorPush] 成功回执：播放撞击"));
    PlayImpact();
}

void UFPSDoorPushComponent::PlayImpact()
{
    auto* Player=Cast<APawn>(GetOwner());if(!Player||!Player->IsLocallyControlled())return;
    if(auto* Sound=Cast<USoundBase>(DoorPushImpactPath.ResolveObject()))UGameplayStatics::PlaySound2D(this,Sound,.85f);
    const auto* PC=Cast<APlayerController>(Player->GetController());
    if(PC&&PC->PlayerCameraManager)
    {
        const auto* Setting=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Camera.Shake"));
        const float Scale=Setting?FMath::Max(0.f,Setting->GetFloat()):1.f;
        if(Scale>0.f)PC->PlayerCameraManager->StartCameraShake(UDoorPushCameraShake::StaticClass(),Scale,ECameraShakePlaySpace::CameraLocal);
    }
}

void UFPSDoorPushComponent::MulticastPushImpact_Implementation(FVector_NetQuantize Location)
{
    const auto* Player=Cast<APawn>(GetOwner());
    if(GetNetMode()==NM_DedicatedServer||!Player||Player->IsLocallyControlled())return;
    if(auto* Sound=Cast<USoundBase>(DoorPushImpactPath.ResolveObject()))UGameplayStatics::PlaySoundAtLocation(this,Sound,Location,.85f);
}

bool UFPSDoorPushComponent::IsNativeDoor(AActor* Target)
{
    // 原生门族：全部经服务器权威开关（E 键 RequestDoorInteraction / 松开 ReleasePressedDoor）。
    // Fab 包的门（BI_Interact 蓝图）不在此列，继续走各自的 OnInteraction 泛化路径。
    return Target&&(Cast<AColdSteelDoor>(Target)||Cast<AColdSteelWindow>(Target)||
        Cast<AColdSteelSlidingDoor>(Target)||Cast<AColdSteelRevolvingDoor>(Target));
}

bool UFPSDoorPushComponent::RequestDoorInteraction(AActor* Target)
{
    // 每次按键至多一条：目标非法或非原生门族时留痕（E 没反应的盲区）。
    if(!IsValid(Target)||!IsNativeDoor(Target))
    {UE_LOG(LogTemp,Warning,TEXT("[DoorPush] E键请求被拒：目标=%s 原生门族=%d"),
        *GetNameSafe(Target),IsNativeDoor(Target)?1:0);return false;}
    Cancel();PressedDoor=Target;ServerToggleDoor(Target);return true;
}

void UFPSDoorPushComponent::ReleasePressedDoor()
{
    // 拖拽门松手冻结：发到服务器，其他门族的 ReleaseDoor 是空操作，误发无害。
    if(!PressedDoor.IsValid())return;
    ServerReleaseDoor(PressedDoor.Get());
    PressedDoor.Reset();
}

void UFPSDoorPushComponent::ServerToggleDoor_Implementation(AActor* Target)
{
    const double Now=GetWorld()->GetTimeSeconds();
    FString Reason;
    const bool bOk=ServerCanInteract(Target,false,&Reason);
    if(!bOk){UE_LOG(LogTemp,Warning,TEXT("[DoorPush] E键开关门拒绝：目标=%s 原因=%s"),*GetNameSafe(Target),*Reason);}
    else if(DoorPushDebug()){UE_LOG(LogTemp,Display,TEXT("[DoorPush] E键开关门：目标=%s 结果=1"),*GetNameSafe(Target));}
    if((LastServerRequest>=0.&&Now-LastServerRequest<.15)||!bOk)return;
    LastServerRequest=Now;ServerDoor.Reset();bServerContact=false;
    if(auto* Single=Cast<AColdSteelDoor>(Target))Single->ToggleDoorFrom(Cast<APawn>(GetOwner()));
    else if(auto* Window=Cast<AColdSteelWindow>(Target))Window->ToggleWindowFrom(Cast<APawn>(GetOwner()));
    else if(auto* Slide=Cast<AColdSteelSlidingDoor>(Target))Slide->ToggleDoorFrom(Cast<APawn>(GetOwner()));
    else if(auto* Revolving=Cast<AColdSteelRevolvingDoor>(Target))Revolving->ToggleDoorFrom(Cast<APawn>(GetOwner()));
}

void UFPSDoorPushComponent::ServerReleaseDoor_Implementation(AActor* Target)
{
    // 拖拽门松手冻结；其他门族的 ReleaseDoor 为空操作。
    if(GetOwner()->HasAuthority()&&IsValid(Target)&&Target->GetWorld()==GetWorld())
        if(auto* ReleasedDoor=Cast<AColdSteelDoor>(Target))ReleasedDoor->ReleaseDoor();
}
