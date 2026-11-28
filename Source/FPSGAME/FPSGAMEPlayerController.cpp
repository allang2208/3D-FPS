#include "FPSGAMEPlayerController.h"
#include "NPC/VillageMasterArtisan.h"
#include "Dungeons/DungeonRoomSubsystem.h"
#include "UI/ColdSteelWoodworkingWidget.h"
#include "Skills/FPSElementalArrowComponent.h"
#include "Movement/FPSFurnitureRestComponent.h"
#include "Movement/HorseRiderComponent.h"
#include "Movement/StableHorseMarket.h"
#include "Movement/StableRidingHorse.h"
#include "Production/ProductionToolComponent.h"
#include "UI/ColdSteelAlchemyWidget.h"
#include "UI/ColdSteelQuickBarTypes.h"
#include "UI/TransitLoadingSubsystem.h"
#include "Dungeons/DungeonRunSubsystem.h"
#include "Dungeons/HeQuePumpControl.h"
#include "SceneTestPortal.h"
#include "EngineUtils.h"
#include "FPSGAMECharacter.h"
#include "Building/VoxelBuildComponent.h"
#include "Building/VoxelBuildAudit.h"
#include "Building/ColdSteelDoorInteraction.h"
#include "Building/ApartmentDeviceControl.h"
#include "Movement/FPSDoorPushComponent.h"

#include "UI/ColdSteelHUDWidget.h"
#include "UI/ColdSteelGameMenuWidget.h"
#include "UI/LPVOScopeWidget.h"
#include "UI/ColdSteelStatusModel.h"
#include "UI/ColdSteelPickup.h"
#include "UI/ColdSteelDamageNumberSubsystem.h"
#include "Weapons/Bow/BowArrow.h"
#include "UI/ColdSteelWorldInteraction.h"
#include "WorldGeneration/HighVillageDefense.h"
#include "WorldGeneration/VillageDefenseCombat.h"
#include "Camera/PlayerCameraManager.h"
#include "Monsters/FPSCombatHealthComponent.h"
#include "NPC/ChapelNun.h"
#include "NPC/VillageArtisanMerchant.h"
#include "NPC/VillageHerbalist.h"
#include "NPC/VillageMillKeeper.h"
#include "WorldGeneration/VillageGunshopServices.h"
#include "NPC/ResidentConversation.h"
#include "NPC/ChapelDialogueComponent.h"
#include "UI/ColdSteelWarehouseChest.h"
#include "UI/ColdSteelSceneContainer.h"
#include "UI/ColdSteelCrateChest.h"
#include "Props/FPSPracticeTarget.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/GameInstance.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/GameViewportClient.h"
#include "EngineUtils.h"
#include "UI/WeatherControlWidget.h"
#include "UI/DevelopmentPanelWidget.h"
#include "Development/DevelopmentSpawnComponent.h"
#include "UI/WeatherPanelValidation.h"
#include "Components/InputComponent.h"
#include "Components/AudioComponent.h"
#include "Components/BoxComponent.h"
#include "Animation/SkeletalMeshActor.h"
#include "Animation/AnimSequence.h"
#include "GameFramework/PlayerStart.h"
#include "Sound/SoundBase.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"

namespace
{
    /** Z 键范围拾取半径；默认 5 m，可现场用控制台调整。 */
    TAutoConsoleVariable<float> AreaPickupRadiusCm(TEXT("fps.Pickup.AreaRadiusCm"),500.f,
        TEXT("Z 键一键拾取的作用半径（cm）。"));
}
#include "InputKeyEventArgs.h"
#include "WorldGeneration/VillageSiegeControl.h"
#include "WorldGeneration/VillageHotOil.h"
#include "WorldGeneration/VillageOilCarry.h"
#include "WorldGeneration/VillageSmartTurret.h"
#include "UI/SSmartTurretDrawer.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "TimerManager.h"
#include "UnrealClient.h"

void RunRetiredWeaponsAudit(AFPSGAMEPlayerController* PC);
void RunWeaponWheelAudit(AFPSGAMEPlayerController* PC);
void RunWorldInteractionAudit(AFPSGAMEPlayerController* PC);
void RunConsumablePickupAudit(AFPSGAMEPlayerController* PC);
void RunEnhancementMaterialPickupAudit(AFPSGAMEPlayerController* PC);
void RunMagicScrollAudit(AFPSGAMEPlayerController* PC);
void RunLootGlowAudit(AFPSGAMEPlayerController* PC);
void RunIncineratorUIAudit(AFPSGAMEPlayerController* PC);

void AFPSGAMEPlayerController::UpdateHiddenComponents(const FVector& ViewLocation,TSet<FPrimitiveComponentId>& HiddenComponents)
{
    Super::UpdateHiddenComponents(ViewLocation,HiddenComponents);
    if(const APawn* Viewer=GetPawn())
        if(const auto* Carry=Viewer->FindComponentByClass<UVillageOilCarry>())Carry->HideFirstPersonEquipment(GetViewTarget(),HiddenComponents);
    if(SiegeControl)SiegeControl->AddHiddenOperatorComponents(GetViewTarget(),HiddenComponents);
}

void AFPSGAMEPlayerController::UpdateRotation(float DeltaTime)
{
    FRotator RestLook;
    if(auto* Rest=GetPawn()?GetPawn()->FindComponentByClass<UFPSFurnitureRestComponent>():nullptr;
        Rest&&Rest->UpdateRestLook(RotationInput,RestLook))
    {
        // The supported body cannot turn with the controller. Neck-local input
        // also avoids the world's pitch clamp when lying face-up at the zenith.
        SetControlRotation(RestLook);
        return;
    }
    if(auto* Tool=GetPawn()?GetPawn()->FindComponentByClass<UProductionToolComponent>():nullptr)
    {
        const FRotator Current=GetControlRotation();
        FRotator Desired=Current+RotationInput;
        if(Tool->ClampLeapStrikeView(Desired))RotationInput=(Desired-Current).GetNormalized();
    }
    Super::UpdateRotation(DeltaTime);
}

AFPSGAMEPlayerController::AFPSGAMEPlayerController()
{
    SiegeControl=CreateDefaultSubobject<UVillageSiegeControl>(TEXT("SiegeControl"));
    ChapelDialogue=CreateDefaultSubobject<UChapelDialogueComponent>(TEXT("ChapelDialogue"));
    VoxelBuilder=CreateDefaultSubobject<UVoxelBuildComponent>(TEXT("VoxelBuilder"));
    DevelopmentSpawner=CreateDefaultSubobject<UDevelopmentSpawnComponent>(TEXT("DevelopmentSpawner"));
    bShowMouseCursor = false;
}

/** 主神空间测试宝箱（2026-10-02 用户指派）：出生点旁放一只地牢宝箱，实机验证仓库式取物面板。
 *  DungeonTreasure.HubTest＝无运行上下文也可 roll（Depth 0 档、按领取键固定种子）；
 *  DungeonChestClaim.HubTest＝稳定领取键；战利品被取空后下次开箱自动重新 roll。 */
void AFPSGAMEPlayerController::SpawnHubTestChest()
{
    for (TActorIterator<ASkeletalMeshActor> It(GetWorld()); It; ++It)
        if (It->ActorHasTag(TEXT("DungeonTreasure.HubTest"))) return; // 本局已生成过
    auto* Mesh = LoadObject<USkeletalMesh>(nullptr,
        TEXT("/Game/Props/GamedevTreasureChest20260922/SK_GamedevTreasureChest.SK_GamedevTreasureChest"));
    if (!Mesh) { UE_LOG(LogTemp, Warning, TEXT("HubTestChest: 宝箱网格缺失")); return; }

    // 出生点锚：与 GameMode 出生／仓库宝箱固定生成同一数据源（首个 PlayerStart），贴地后放右侧 220cm。
    FVector Base = FVector::ZeroVector; FRotator Facing = FRotator::ZeroRotator; bool bAnchor = false;
    for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
    {
        FCollisionQueryParams Query(SCENE_QUERY_STAT(HubTestChestFloor), false, *It);
        FHitResult Floor;
        const FVector Probe = It->GetActorLocation();
        if (GetWorld()->LineTraceSingleByChannel(Floor, Probe + FVector(0, 0, 300), Probe - FVector(0, 0, 2000), ECC_Visibility, Query)
            && Floor.bBlockingHit && !Floor.bStartPenetrating)
            Base = Floor.ImpactPoint;
        else Base = Probe;
        Facing = It->GetActorRotation(); bAnchor = true;
        break;
    }
    if (!bAnchor) return;

    const FVector Side = FRotationMatrix(Facing).GetUnitAxis(EAxis::Y);
    auto* Chest = GetWorld()->SpawnActor<ASkeletalMeshActor>(ASkeletalMeshActor::StaticClass(),
        Base + Side * 220.f, FRotator(0.f, Facing.Yaw + 180.f, 0.f));
    if (!Chest) return;
    Chest->Tags.Add(TEXT("DungeonTreasureChest"));
    Chest->Tags.Add(TEXT("DungeonTreasure.HubTest"));
    Chest->Tags.Add(TEXT("DungeonChestClaim.HubTest"));
    auto* Component = Chest->GetSkeletalMeshComponent();
    Component->SetSkeletalMeshAsset(Mesh);
    Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    if (auto* Closed = LoadObject<UAnimSequence>(nullptr,
        TEXT("/Game/Props/GamedevTreasureChest20260922/A_TreasureChest_ClosedPose.A_TreasureChest_ClosedPose")))
    {
        Component->PlayAnimation(Closed, false); Component->SetPosition(Closed->GetPlayLength(), false); Component->SetPlayRate(0.f);
        Component->TickAnimation(0.f, false); Component->RefreshBoneTransforms(); Component->SetComponentTickEnabled(false);
        Component->ComponentTags.Add(TEXT("DungeonClosedPoseFrozen"));
    }
    // 与地牢生成器同口径：骨骼网格不参与射线（NoCollision），交互命中靠 BlockAll 盒体（尺寸取 treasure_chest_assets.json）。
    auto* Box = NewObject<UBoxComponent>(Chest);
    Chest->AddInstanceComponent(Box);
    Box->SetupAttachment(Component);
    Box->SetBoxExtent(FVector(59.5f, 74.3f, 55.1f));
    Box->SetRelativeLocation(FVector(6.2f, 5.2f, 55.1f));
    Box->SetCollisionProfileName(TEXT("BlockAll"));
    Box->RegisterComponent();
}

/** 主神空间训练靶（2026-10-02 用户指派）：出生点前方下靶位生成圆环木架靶，承接全武器命中，
 *  浮出伤害数字并在头顶牌滚动 DPS。与 SpawnHubTestChest 同一出生点锚、同贴地方式。 */
void AFPSGAMEPlayerController::SpawnHubPracticeTarget()
{
    if(!HasAuthority())return; // 训练靶由服务器生成并复制；客户端本地生成会得到第二个无伤害的靶。
    for (TActorIterator<AFPSPracticeTarget> It(GetWorld()); It; ++It)
        if (It->ActorHasTag(TEXT("GodSpace.PracticeTarget"))) return; // 本局已生成过

    FVector Base = FVector::ZeroVector; FRotator Facing = FRotator::ZeroRotator; bool bAnchor = false;
    for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
    {
        Base = It->GetActorLocation();
        Facing = It->GetActorRotation(); bAnchor = true;
        break;
    }
    if (!bAnchor) return;

    const FVector Forward = FRotationMatrix(Facing).GetUnitAxis(EAxis::X);
    const FVector Spot = Base + Forward * 550.f;
    FHitResult Floor;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HubPracticeTargetFloor), false);
    FVector Position = Spot;
    if (GetWorld()->LineTraceSingleByChannel(Floor, Spot + FVector(0, 0, 200), Spot - FVector(0, 0, 1500), ECC_Visibility, Query)
        && Floor.bBlockingHit && !Floor.bStartPenetrating)
        Position = Floor.ImpactPoint;

    auto* Target = GetWorld()->SpawnActor<AFPSPracticeTarget>(Position, FRotator(0.f, Facing.Yaw + 180.f, 0.f));
    if (Target) Target->Tags.Add(TEXT("GodSpace.PracticeTarget"));
}

void AFPSGAMEPlayerController::ClientPracticeHit_Implementation(AActor* Target,FVector Point,float Damage,bool bBullseye,float MagicApplied)
{
    if(!Target||Damage<=0.f)return;
    if(auto* GI=GetGameInstance())
        if(auto* Numbers=GI->GetSubsystem<UColdSteelDamageNumberSubsystem>())
            Numbers->PushDamageNumber(Target,this,Point,Damage,bBullseye,false,bBullseye||Damage>=80.f,false,MagicApplied);
}

void AFPSGAMEPlayerController::ClientDefenseDamageNumber_Implementation(AActor* Target,FVector_NetQuantize WorldPoint,float AppliedDamage,float MagicDamage,bool bCritical,bool bKilled,bool bBig)
{
    if(!IsLocalController()||AppliedDamage<=0.f)return;
    const FVector Anchor=IsValid(Target)?UColdSteelDamageNumberSubsystem::TargetTopAnchor(Target):FVector(WorldPoint);
    const float MaxRangeCm=VillageDefenseCombat::DamageNumberMaxRangeCm();
    if(MaxRangeCm<=0.f)return;
    FVector ViewLoc=FVector::ZeroVector;
    if(PlayerCameraManager && PlayerCameraManager->GetCameraCacheTime()>0.f)
    {
        FRotator ViewRot=FRotator::ZeroRotator;
        GetPlayerViewPoint(ViewLoc,ViewRot);
    }
    else if(const APawn* P=GetPawn())
    {
        ViewLoc=P->GetActorLocation();
    }
    else
    {
        FRotator ViewRot=FRotator::ZeroRotator;
        GetPlayerViewPoint(ViewLoc,ViewRot);
    }
    if(FVector::DistSquared(ViewLoc,Anchor)>FMath::Square(MaxRangeCm))return;
    if(auto* GI=GetGameInstance())
        if(auto* Numbers=GI->GetSubsystem<UColdSteelDamageNumberSubsystem>())
            Numbers->PushDamageNumber(Target,this,Anchor,AppliedDamage,bCritical,bKilled,bBig,IsValid(Target),MagicDamage);
}

void AFPSGAMEPlayerController::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    CloseSmartTurretDrawer();
    Super::EndPlay(EndPlayReason);
}

void AFPSGAMEPlayerController::BeginPlay()
{
    Super::BeginPlay();
    RefreshRegionMusic();
    if(UGameplayStatics::GetCurrentLevelName(this,true)==TEXT("DayNight_Lighting"))
    {SpawnHubTestChest();SpawnHubPracticeTarget();}
    // 建筑系统验收：-VoxelBuildAudit（材质表 / 过载曲线 / 体素块目录 / 放置-撤销-拆除闭环 / 存档落盘）
    if(UVoxelBuildAudit::Requested())
    {
        VoxelBuildAudit=NewObject<UVoxelBuildAudit>(this);
        VoxelBuildAudit->Start(this);
        GetWorldTimerManager().SetTimer(VoxelBuildAuditTimer,
            FTimerDelegate::CreateWeakLambda(this,[this]()
            {
                if(VoxelBuildAudit&&VoxelBuildAudit->Tick())GetWorldTimerManager().ClearTimer(VoxelBuildAuditTimer);
            }),1.5f,true,8.f);
    }
    if(FParse::Param(FCommandLine::Get(),TEXT("LootGlowAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){RunLootGlowAudit(this);}),8.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("MagicScrollAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){RunMagicScrollAudit(this);}),8.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("DropHitchAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){if(ColdSteelHUD)ColdSteelHUD->RunDropHitchAudit();}),8.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("EnhancementMaterialPickupAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){RunEnhancementMaterialPickupAudit(this);}),8.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("ConsumablePickupAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){RunConsumablePickupAudit(this);}),8.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("WorldInteractionAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){RunWorldInteractionAudit(this);}),8.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("WeaponWheelAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[this](){RunWeaponWheelAudit(this);}),5.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("ColdSteelEnhancementAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunEnhancementAudit,12.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("GunsmithWorkbenchAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunGunsmithWorkbenchAudit,5.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("CantedForegripAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunCantedForegripAudit,5.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("VerticalForegripAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunVerticalForegripAudit,5.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("PrismHandstopAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunPrismHandstopAudit,5.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("M4DrumAudit")))
    {FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunM4DrumAudit,5.f,false);}
    if(FParse::Param(FCommandLine::Get(),TEXT("M4GunsmithAudit")))
    {
        FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,this,&ThisClass::RunM4GunsmithAudit,5.f,false);
    }
    if(FParse::Param(FCommandLine::Get(),TEXT("RetiredWeaponsAudit")))
        GetWorldTimerManager().SetTimerForNextTick([this](){RunRetiredWeaponsAudit(this);});

    if (!IsLocalController())
    {
        return;
    }

#if !UE_BUILD_SHIPPING
    WeatherPanel = CreateWidget<UDevelopmentPanelWidget>(this, UDevelopmentPanelWidget::StaticClass());
    // The unified panel owns the F6 input context. Its drawer now shares the backpack's
    // size, slide and HUD-yield rules, so it must sit above the HUD (20) to dim it the
    // same way; gunsmith/enhancement panels (60) and drag visuals (1000) stay on top.
    if (WeatherPanel) WeatherPanel->AddToPlayerScreen(30);
    StartWeatherPanelValidation(this, WeatherPanel);
#endif
    ColdSteelHUD = CreateWidget<UColdSteelHUDWidget>(this, UColdSteelHUDWidget::StaticClass());
    GameMenu = CreateWidget<UColdSteelGameMenuWidget>(this, UColdSteelGameMenuWidget::StaticClass());
    if (GameMenu) GameMenu->AddToPlayerScreen(90);
    ScopeOverlay=CreateWidget<ULPVOScopeWidget>(this,ULPVOScopeWidget::StaticClass());
    // All opaque scope surrounds stay below the combat HUD: damage numbers,
    // target health, player status, hotbar and weapon readouts remain readable.
    if(ScopeOverlay){ScopeOverlay->SetVisibility(ESlateVisibility::HitTestInvisible);ScopeOverlay->AddToPlayerScreen(10);}
    if (ColdSteelHUD)
    {
        ColdSteelHUD->AddToPlayerScreen(20);
        if(FParse::Param(FCommandLine::Get(),TEXT("IncineratorUIAudit"))){FTimerHandle AuditTimer;GetWorldTimerManager().SetTimer(AuditTimer,FTimerDelegate::CreateWeakLambda(this,[this](){RunIncineratorUIAudit(this);}),6.f,false);}
        if(FParse::Param(FCommandLine::Get(),TEXT("ColdSteelTopVitalsAudit"))){FTimerHandle VitalsAudit;GetWorldTimerManager().SetTimer(VitalsAudit,[this](){ColdSteelHUD->RunTopVitalsAudit();},10.f,false);}
        FTimerHandle WarehouseInit;
        GetWorldTimerManager().SetTimer(WarehouseInit,[this]()
        {
            // Collision is shared. A client must not place its own chest row.
            if(!HasAuthority())return;
            // The gunplay audit requires its original clear movement corridor.
            if(FParse::Param(FCommandLine::Get(),TEXT("GunplayAudit"))){UE_LOG(LogTemp,Display,TEXT("Gunplay audit: omit automatic chest from movement fixture"));return;}
            const bool Audit=FParse::Param(FCommandLine::Get(),TEXT("ColdSteelWarehouseAudit"));
            if(!GetPawn()||(!Audit&&UGameplayStatics::GetCurrentLevelName(this,true)!=TEXT("DayNight_Lighting")))return;
            bool Exists=false;for(TActorIterator<AColdSteelWarehouseChest> It(GetWorld());It;++It)if(!Cast<AColdSteelCrateChest>(*It)){Exists=true;break;}
            if(!Exists){
                // 固定生成：锚点取地图 PlayerStart（与 GameMode 出生同一数据源），位置由关卡与
                // Content/ColdSteelData/warehouse_assets.json 的 spawn 段决定。不再读取玩家当前
                // 站位与视角，所以每次进入游戏的落点一致；只有关卡没有 PlayerStart 时才退回旧口径。
                FVector Where;FRotator Facing;FString Source;
                if(AColdSteelWarehouseChest::ResolveFixedSpawn(GetWorld(),GetPawn(),Where,Facing,Source))
                {
                    GetWorld()->SpawnActor<AColdSteelWarehouseChest>(Where,Facing);
                    UE_LOG(LogTemp,Display,TEXT("WarehouseChest: fixed spawn %s facing %s (anchor=%s)"),*Where.ToString(),*Facing.ToString(),*Source);
                }
                else UE_LOG(LogTemp,Warning,TEXT("WarehouseChest: fixed spawn unresolved; chest not placed"));
            }
            // 五档储物箱：宝箱右侧成排固定生成（同朝向，间距 170cm），复用仓库面板与开合动画；
            // 仓库审计流程保持原有场景，不自动加箱子。
            if(!Audit){bool HasCrates=false;for(TActorIterator<AColdSteelCrateChest> It(GetWorld());It;++It){HasCrates=true;break;}
                if(!HasCrates)for(TActorIterator<AColdSteelWarehouseChest> It(GetWorld());It;++It)
                    if(auto* Anchor=*It;Anchor&&!Cast<AColdSteelCrateChest>(Anchor))
                    {
                        int32 Placed=0;
                        for(int32 Slot=0;Slot<5;++Slot)if(AColdSteelCrateChest::SpawnBeside(GetWorld(),Anchor,static_cast<EColdSteelCrateTier>(Slot),0.f,190.f+170.f*Slot))++Placed;
                        UE_LOG(LogTemp,Display,TEXT("CrateChest: storage row beside %s placed %d/5"),*Anchor->GetName(),Placed);
                        break;
                    }
            }
            if(Audit)ColdSteelHUD->RunWarehouseAudit();
        },3.f,false);
        // The persistent HUD is display-only until the inventory is opened.
        // Activating a focusable CommonUI root here steals keyboard and mouse
        // input from the possessed character at PIE startup.
        SetInputMode(FInputModeGameOnly());
        bShowMouseCursor = false;

        // Deterministic visual acceptance route. It is inert in normal play and
        // exercises the same PlayerController InputKey path as a physical Tab press.
        if (FParse::Param(FCommandLine::Get(), TEXT("ColdSteelUIAudit")))
        {
            GetWorldTimerManager().SetTimerForNextTick([this]()
            {
                InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::Tab, IE_Pressed, 1.0f));
                FTimerHandle CaptureTimer;
                GetWorldTimerManager().SetTimer(CaptureTimer, []()
                {
                    const FString Directory = FPaths::ProjectSavedDir() / TEXT("UIAudit/2026-09-09");
                    IFileManager::Get().MakeDirectory(*Directory, true);
                    FScreenshotRequest::RequestScreenshot(Directory / TEXT("ue-backpack-runtime.png"), true, false);
                }, 0.75f, false);
            });
        }

        if (FParse::Param(FCommandLine::Get(), TEXT("EventTimelineUIAudit")))
        {
            ColdSteelHUD->SetEventTimelineAuditState(0);
            FTimerHandle CompactTimer;
            GetWorldTimerManager().SetTimer(CompactTimer, [this]()
            {
                CaptureTimelineAudit(TEXT("ue-event-timeline-compact.png"), 0);
            }, 0.8f, false);
            FTimerHandle ExpandedTimer;
            GetWorldTimerManager().SetTimer(ExpandedTimer, [this]()
            {
                CaptureTimelineAudit(TEXT("ue-event-timeline-expanded.png"), 1);
            }, 1.6f, false);
            FTimerHandle DetailsTimer;
            GetWorldTimerManager().SetTimer(DetailsTimer, [this]()
            {
                CaptureTimelineAudit(TEXT("ue-event-timeline-forecast.png"), 2);
            }, 2.4f, false);
        }

        if (FParse::Param(FCommandLine::Get(), TEXT("AttributeEquipmentUIAudit")))
        {
            FTimerHandle StatusTimer;
            GetWorldTimerManager().SetTimer(StatusTimer, [this]()
            {
                CaptureInventoryAudit(TEXT("ue-attribute-panel-1280.png"), 0);
            }, 0.9f, false);
            FTimerHandle EquipmentTimer;
            GetWorldTimerManager().SetTimer(EquipmentTimer, [this]()
            {
                CaptureInventoryAudit(TEXT("ue-equipment-card-1280.png"), 1);
            }, 1.8f, false);
        }
        if (FParse::Param(FCommandLine::Get(), TEXT("ColdSteelUpgradeAudit")))
        {
            FTimerHandle UpgradeTimer;
            GetWorldTimerManager().SetTimer(UpgradeTimer, [this]() { ColdSteelHUD->RunUpgradeAudit(); }, 12.0f, false);
        }
        if(FParse::Param(FCommandLine::Get(),TEXT("ColdSteelInventoryAudit")))
        {
            FTimerHandle InventoryTimer;
            GetWorldTimerManager().SetTimer(InventoryTimer,[this](){ColdSteelHUD->RunInventoryAudit();},12.f,false);
        }
        if(FParse::Param(FCommandLine::Get(),TEXT("SmeltingVisualAudit")))
        {
            FTimerHandle SmeltingTimer;
            GetWorldTimerManager().SetTimer(SmeltingTimer,[this](){ColdSteelHUD->RunSmeltingVisualAudit();},12.f,false);
        }
        if(FParse::Param(FCommandLine::Get(),TEXT("ColdSteelItemTooltipAudit")))
        {
            FTimerHandle TooltipTimer;
            GetWorldTimerManager().SetTimer(TooltipTimer,[this](){ColdSteelHUD->RunItemTooltipAudit();},12.f,false);
        }
    }
    // Automation escape hatch: -ClearwaterNoMenu skips the startup mode menu, which otherwise
    // covers the viewport until a human clicks it. A headless capture run has nobody to click,
    // so every screenshot came back showing the menu+loading overlay rather than the scene --
    // which made a rendering investigation look like a scene that refused to draw.
    if (FParse::Param(FCommandLine::Get(), TEXT("ClearwaterNoMenu")))
    {
        if (auto* Loading = GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())
        {
            Loading->ReleaseToGameplay();
        }
        return;
    }
    if(auto* Loading=GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>())Loading->ShowStartupMenu(this);
}

void AFPSGAMEPlayerController::SetupInputComponent()
{
    // Bind at the controller layer so CommonUI and Enhanced Input cannot hide the drawer shortcut.
    Super::SetupInputComponent();
    if (InputComponent)
    {
        InputComponent->BindKey(EKeys::LeftAlt, IE_Pressed, this, &AFPSGAMEPlayerController::ToggleTimelineInteraction);
    }
}

bool AFPSGAMEPlayerController::InputKey(const FInputKeyEventArgs& Params)
{
    if(GetPawn())if(auto* Oil=GetPawn()->FindComponentByClass<UVillageOilCarry>();Oil && Oil->HandleInput(Params))return true;
    if(SiegeControl && SiegeControl->HandleInput(Params))return true;
    if(Params.Key==EKeys::E && Params.Event==IE_Released && GetPawn())
        if(auto* Ride=GetPawn()->FindComponentByClass<UHorseRiderComponent>();Ride&&Ride->ReleaseUse())return true;
    if(Params.Key==EKeys::E && Params.Event==IE_Released && ChapelDialogue && ChapelDialogue->ReleaseFirstAid())
        return true;
    if(ChapelDialogue&&ChapelDialogue->IsOpen())
        return Params.Event==IE_Released?Super::InputKey(Params):true;
    if (IsGameMenuOpen())
    {
        if (GameMenu->IsWorldMapOpen())
        {
            if (GameMenu->HandleMapShortcut(Params.Key,Params.Event==IE_Pressed)) return true;
            if (GameMenu->IsMapMovementKey(Params.Key) ||
                (Params.Event==IE_Released && IsInputKeyDown(Params.Key)))
                return Super::InputKey(Params);
        }
        else if (Params.Event==IE_Pressed && Params.Key==EKeys::Escape) GameMenu->GoBack();
        return true;
    }
    // Action handlers own inspection interruption. Raw keys and look/move axes
    // also describe ordinary locomotion, empty shortcuts and UI-only input.
    if(auto* Rest=GetPawn()?GetPawn()->FindComponentByClass<UFPSFurnitureRestComponent>():nullptr;
        Rest&&Rest->IsResting()&&!bShowMouseCursor)
    {
        if(Params.Event==IE_Pressed&&(Params.Key==EKeys::E||Params.Key==EKeys::SpaceBar||
            Params.Key==EKeys::W||Params.Key==EKeys::A||Params.Key==EKeys::S||Params.Key==EKeys::D))
        {Rest->RequestLeave();return true;}
        // UE marks MouseX/MouseY/Mouse2D as MouseButton too. Let look axes reach
        // Turn/LookUp while still consuming clicks, wheel input and quick slots.
        const bool bLookAxis=Params.Key==EKeys::MouseX||Params.Key==EKeys::MouseY||Params.Key==EKeys::Mouse2D;
        if((Params.Key.IsMouseButton()&&!bLookAxis)||Params.Key==EKeys::MouseScrollUp||Params.Key==EKeys::MouseScrollDown||
            ColdSteelQuickBar::KeyIndex(Params.Key)>=0)return true;
    }
    if(AlchemyPanel)
    {
        if(Params.Event==IE_Pressed&&(Params.Key==EKeys::Escape||Params.Key==EKeys::Tab))AlchemyPanel->RequestClose();
        return true;
    }
    if(WoodworkingPanel)
    {
        if(Params.Event==IE_Pressed&&(Params.Key==EKeys::Escape||Params.Key==EKeys::Tab))WoodworkingPanel->RequestClose();
        return true;
    }
    if(SmartTurretDrawer.IsValid())
    {
        if(Params.Event==IE_Pressed&&(Params.Key==EKeys::Escape||Params.Key==EKeys::Tab||Params.Key==EKeys::E))
            SmartTurretDrawer->RequestClose();
        return Params.Event==IE_Released?Super::InputKey(Params):true;
    }
    if(ColdSteelHUD&&ColdSteelHUD->HandleGunAssemblyInput(Params))return true;
    if(ColdSteelHUD&&ColdSteelHUD->HandleWorldForgeInput(Params))return true;
    if (ExpeditionPanel)
    {
        if(Params.Event==IE_Pressed)
        {
            if(bExpeditionEquipmentOpen&&ColdSteelHUD&&(Params.Key==EKeys::Escape||Params.Key==EKeys::Tab))ColdSteelHUD->ToggleInventory();
            else if(Params.Key==EKeys::Escape)CloseExpedition();
        }
        return true;
    }
    if(auto* E=GetPawn()?GetPawn()->FindComponentByClass<UFPSElementalArrowComponent>():nullptr)
    {
        const int32 Slot=ColdSteelQuickBar::KeyIndex(Params.Key);
        if(Params.Event==IE_Released&&E->KeyReleased(Slot))return true;
        if(Params.Event==IE_Repeat&&E->OwnsKey(Slot))return true;
        if(E->IsWheelOpen()&&Slot>=0)return true;
    }
    if(auto* AmmoPawn=Cast<AFPSGAMECharacter>(GetPawn());AmmoPawn&&AmmoPawn->IsAmmoWheelOpen())
    {
        if(Params.Key==EKeys::Escape){if(Params.Event==IE_Pressed)AmmoPawn->CancelAmmoSelection();return true;}
        if(Params.Key==EKeys::MouseScrollUp||Params.Key==EKeys::MouseScrollDown)AmmoPawn->CancelAmmoSelection();
        // 手别由鼠标所在圆盘决定（双持弹两个盘），点击只吞掉，避免选弹时开火。
        if(Params.Key==EKeys::LeftMouseButton||Params.Key==EKeys::RightMouseButton)return true;
        if(AmmoPawn->IsMagicWheelOpen()&&ColdSteelQuickBar::KeyIndex(Params.Key)>=0)return true;
    }
    if(ColdSteelHUD&&ColdSteelHUD->IsQuickDragging())
    {
        if(Params.Event==IE_Pressed&&Params.Key==EKeys::Escape)ColdSteelHUD->CancelQuickDrag();
        return Params.Event==IE_Released?Super::InputKey(Params):true;
    }
    // The survey cursor places into the world. Route it before the HUD's ordinary
    // visible-cursor filter, and leave unrelated keys with the builder while surveying.
    if(VoxelBuilder && VoxelBuilder->IsVillageCameraPlacing())
    {
        if(VoxelBuilder->HandleInput(Params,false))return true;
    }
    // UI has already received this event; do not forward unhandled cursor clicks to gameplay.
    if (bShowMouseCursor && Params.Key.IsMouseButton() && Params.Event != IE_Released) return true;
    if (Params.Event == IE_Pressed && Params.Key == EKeys::F6) { ToggleDevelopmentPanel(); return true; }
    if (WeatherPanel && WeatherPanel->IsPanelOpen())
    {
        if (Params.Event == IE_Pressed && Params.Key == EKeys::Escape) WeatherPanel->SetPanelOpen(false);
        return Params.Event == IE_Released ? Super::InputKey(Params) : true;
    }
    const bool BuildMenuOpen=GunsmithPanel||(WeatherPanel&&WeatherPanel->IsPanelOpen())||(ColdSteelHUD&&ColdSteelHUD->IsInventoryOpen());
    if(BuildMenuOpen&&Params.Event==IE_Pressed)
        UE_LOG(LogTemp,Display,TEXT("VOXEL_PANEL BuildMenuOpen 来源 gunsmith=%d devpanel=%d inventory=%d key=%s"),
            GunsmithPanel?1:0,(WeatherPanel&&WeatherPanel->IsPanelOpen())?1:0,
            (ColdSteelHUD&&ColdSteelHUD->IsInventoryOpen())?1:0,*Params.Key.ToString());
    if(VoxelBuilder&&VoxelBuilder->HandleInput(Params,BuildMenuOpen))return true;
    if(EnhancementPanel){if(Params.Event==IE_Pressed&&(Params.Key==EKeys::Escape||Params.Key==EKeys::K||Params.Key==EKeys::Tab))CloseEnhancement();return true;}
    if(Params.Event==IE_Pressed&&Params.Key==EKeys::K){OpenEnhancement();return true;}
    if(GunsmithPanel)
    {
        if(Params.Event==IE_Pressed&&(Params.Key==EKeys::Escape||Params.Key==EKeys::J||Params.Key==EKeys::Tab))CloseGunsmith();
        return true;
    }
    if(Params.Event==IE_Pressed&&Params.Key==EKeys::J){OpenGunsmith();return true;}
    if (Params.Key == EKeys::M)
    {
        if (Params.Event == IE_Pressed) OpenWorldMap();
        return true;
    }
    if ((Params.Event == IE_Pressed || Params.Event == IE_Repeat) && ColdSteelHUD &&
        ColdSteelHUD->HandlePanelShortcut(Params.Key, Params.Event == IE_Repeat))
    {
        return true;
    }
    if (Params.Event == IE_Pressed && Params.Key == EKeys::Escape && CanOpenGameMenu())
    {
        OpenGameMenu();
        return true;
    }
    // Magic hold-to-preview consumes its own release: pressing a bound slot while its
    // projectile hovers shows the red trajectory instead of firing, and letting go fires it.
    if(Params.Event==IE_Released&&(!ColdSteelHUD||!ColdSteelHUD->IsInventoryOpen()))
    {
        const int32 QuickIndex=ColdSteelQuickBar::KeyIndex(Params.Key);
        if(QuickIndex>=0)
        {
            auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
            if(Profile&&Profile->EndSpellAimPreview(QuickIndex))return true;
        }
        // 拖拽门松手冻结：E 按下时经 RequestDoorInteraction 记住了那扇门，这里只管松开。
        if(Params.Key==EKeys::E&&GetPawn())
            if(auto* Push=GetPawn()->FindComponentByClass<UFPSDoorPushComponent>())
                if(Push->HasPressedDoor())Push->ReleasePressedDoor();
    }
    if(Params.Event==IE_Pressed&&(!ColdSteelHUD||!ColdSteelHUD->IsInventoryOpen()))
    {
        if(Params.Key==EKeys::MouseScrollUp||Params.Key==EKeys::MouseScrollDown)
            if(auto* C=Cast<AFPSGAMECharacter>(GetPawn());C&&C->AdjustOpticMagnification(Params.Key==EKeys::MouseScrollUp?.5f:-.5f))return true;
        auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        const auto InterruptInspection=[this]()
        {
            if(auto* C=Cast<AFPSGAMECharacter>(GetPawn()))C->InterruptWeaponInspection();
        };
        // 铁铲 2026-10-17 与斧／镐同权：装备到主手武器槽后经滚轮/G 使用；
        // F7 召出与收起整组删除，背包覆盖选择由 NormalizeProductionState 清理。
        if(Params.Key==EKeys::F7)return false;
        // G 已让位给符文长剑·环绕飞剑（角色 BindAction "RuneBlades"），武器轮换只留滚轮。
        if(Params.Key==EKeys::MouseScrollUp || Params.Key==EKeys::MouseScrollDown)
        {Profile->CycleWeapon();return true;}
        if(Params.Key==EKeys::E&&GetPawn())
        {
            auto* Rest=GetPawn()->FindComponentByClass<UFPSFurnitureRestComponent>();
            if(Rest && UFPSFurnitureRestComponent::IsResting(GetPawn()) && Rest->Interact()) return true;
            const auto Focus=ColdSteelWorldInteraction::TraceUseTargets(this);
            auto* Target=Focus.Target;
            if(StableHorseMarket::IsSeller(Target) && ColdSteelHUD)
            {InterruptInspection();ColdSteelHUD->OpenStableShop(Target);return true;}
            if(auto* Ride=GetPawn()->FindComponentByClass<UHorseRiderComponent>();Ride&&Ride->PressUse(Cast<AStableRidingHorse>(Target)))return true;
            if(auto* Section=Focus.RepairTarget())
            {
                RequestVillageRepair(Section);
                return true;
            }
            if(auto* Kettle=Cast<AVillageOilKettle>(Target))
            {
                if(!IsInBuildMode())if(auto* Carry=GetPawn()->FindComponentByClass<UVillageOilCarry>())Carry->Take(Kettle);
                return true;
            }
            if(auto* Siege=Cast<AVillageSiegeEngine>(Target))
            {
                if(!IsInBuildMode() && Siege->CanOperate() && !Siege->IsOccupied())
                {
                    InterruptInspection();
                    SiegeControl->ServerEnter(Siege,GetPawn());
                }
                return true;
            }
            if(auto* Turret=Cast<AVillageSmartTurret>(Target))
            {
                if(!IsInBuildMode() && Turret->GetHealth()>0.f)
                {
                    InterruptInspection();
                    OpenSmartTurretDrawer(Turret);
                }
                return true;
            }
            if(Focus.GateUse==EHighGateUse::Repair ||
                (Focus.GateUse==EHighGateUse::Release && CastChecked<AHighVillageGate>(Target)->GetHealth()<=0.f))
                return true;
            if(auto* Artisan=Cast<AVillageArtisanMerchant>(Target); Artisan && ResidentConversation::IsSpeakerDowned(Artisan))
            {
                InterruptInspection();
                ChapelDialogue->BeginFirstAid(Artisan);
                return true;
            }
            if(auto* Master=Cast<AVillageMasterArtisan>(Target)){InterruptInspection();ChapelDialogue->OpenMerchant(Master);return true;}
            if(auto* Miller=Cast<AVillageMillKeeper>(Target)){InterruptInspection();ChapelDialogue->OpenMerchant(Miller);return true;}
            if(Rest&&Rest->Interact())return true;
            if(auto* Nun=Cast<AChapelNun>(Target)){InterruptInspection();ChapelDialogue->Open(Nun);return true;}
            if(auto* Herbalist=Cast<AVillageHerbalist>(Target)){InterruptInspection();ChapelDialogue->OpenHerbalist(Herbalist);return true;}
            if(auto* Artisan=Cast<AVillageArtisanMerchant>(Target)){InterruptInspection();ChapelDialogue->OpenArtisan(Artisan);return true;}
            if(auto* Counter=Cast<AVillageGunshopCounter>(Target);Counter && ColdSteelHUD)
            {InterruptInspection();ColdSteelHUD->OpenGunshop(Counter);return true;}
            if(auto* Pump=Cast<AHeQuePumpControl>(Target))
            {InterruptInspection();ServerUseHeQuePump(Pump);return true;}
            if(auto* Control=Cast<AApartmentDeviceControl>(Target))
            {InterruptInspection();ServerUseApartmentControl(Control);return true;}
            if(ColdSteelWorldInteraction::IsExpeditionAltar(Target)){OpenExpedition();return true;}
            if(ColdSteelWorldInteraction::IsBlessingFountain(Target)){InterruptInspection();ColdSteelWorldInteraction::DrinkFromFountain(this,Target);return true;}
            if(auto* Run=UDungeonRunSubsystem::Get(GetWorld());Run&&Run->IsShrine(Target)){InterruptInspection();Run->ClaimShrine(this,Target);return true;}
            if(ColdSteelWorldInteraction::IsTreasureChest(Target)){InterruptInspection();ColdSteelWorldInteraction::OpenTreasureChest(this,Target);return true;}
            if(auto* Container=ColdSteelWorldInteraction::FocusedSceneContainer(this)){InterruptInspection();Container->TrySearch(this);return true;}
            if(auto* Chest=Cast<AColdSteelWarehouseChest>(Target);Chest&&ColdSteelHUD){ColdSteelHUD->OpenWarehouse(Chest);return true;}
            if(auto* Pickup=Cast<AColdSteelPickup>(Target)){InterruptInspection();Profile->Pickup(Pickup->ItemId);return true;}
            if(auto* Arrow=Cast<ABowArrow>(Target)){InterruptInspection();Arrow->TryRecover(GetPawn());return true;}
            // 冶炼高炉：E 同时打开背包与独立冶炼面板（面板贴抽屉左侧，可被 Esc／× 单独关闭；炉内按真实时间继续冶炼）。
            // 放在门判定之前：高炉不是门，但两者都靠"命中 Actor 是什么"分派，先特异后泛化。
            if(ColdSteelWorldInteraction::IsForgingStation(Target)&&ColdSteelHUD)
            {ColdSteelHUD->OpenForging(Target);return true;}
            if(ColdSteelWorldInteraction::IsSmeltingFurnace(Target)&&ColdSteelHUD)
            {ColdSteelHUD->OpenSmelting(Target);return true;}
            // 工作台：E 同时打开背包与制作面板（格式复刻冶炼面板，制作内容后续设计；
            // Docs/UI/workbench-panel-plan-20260924.md）。与高炉判定并列、互斥同贴位。
            if(ColdSteelWorldInteraction::IsEnhancementBench(Target)){OpenEnhancement(Target);return true;}
            if(ColdSteelWorldInteraction::IsAlchemyBench(Target)){OpenAlchemy(Target);return true;}
            if(ColdSteelWorldInteraction::IsWoodworkingBench(Target)){OpenWoodworking(Target);return true;}
            if(ColdSteelWorldInteraction::IsWorkbench(Target)&&ColdSteelHUD)
            {ColdSteelHUD->OpenWorkbench(Target);return true;}
            // Door System 的门：准星命中后按门自己的交互入口开门／关门（隐藏玩家代理在子系统里维护）。
            if(Target&&UColdSteelDoorInteraction::IsDoor(Target))
            {
                if(auto* Doors=GetWorld()?GetWorld()->GetSubsystem<UColdSteelDoorInteraction>():nullptr)
                {
                    FString Entry;
                    InterruptInspection();
                    // 开关门保持安静：不占提示栏、也不触发提示栏的音效；入口名仍然写日志便于排查。
                    Doors->TryInteract(Target,GetPawn(),Entry);
                    return true;
                }
            }
            if (Focus.CounterResident && ChapelDialogue->CanStartConversation(Focus.CounterResident))
            {
                const auto* Guest = Cast<AFPSGAMECharacter>(GetPawn());
                if (Guest && !Guest->IsAmmoWheelOpen())
                {
                    InterruptInspection();
                    ChapelDialogue->OpenMerchant(Focus.CounterResident);
                    return true;
                }
            }
            // Proximity-only portals receive E once aimed interactions have had their turn.
            for(TActorIterator<ASceneTestPortal> It(GetWorld());It;++It)if(It->IsWithinInteractionRange(GetPawn())){InterruptInspection();return Super::InputKey(Params);}
        }
        // Z: one key picks up every drop around the player (blocks, equipment, materials). Ctrl+Z is
        // the build undo and is consumed by the building component before it reaches this branch.
        if(Params.Key==EKeys::Z&&GetPawn()&&!IsInputKeyDown(EKeys::LeftControl)&&!IsInputKeyDown(EKeys::RightControl))
        {Profile->PickupNearby(AreaPickupRadiusCm.GetValueOnGameThread());return true;}
        const int32 QuickIndex=ColdSteelQuickBar::KeyIndex(Params.Key);
        if(QuickIndex>=0)
        {
            const auto Binding=Profile->QuickBinding(QuickIndex);
            if(Binding.Skill==TEXT("elementalArrow"))
                if(auto* E=GetPawn()?GetPawn()->FindComponentByClass<UFPSElementalArrowComponent>():nullptr){InterruptInspection();E->KeyPressed(QuickIndex);return true;}
            // Dodge shares the locomotion policy even when triggered by a skill slot.
            if(!Binding.IsEmpty()&&Binding.Skill!=TEXT("dodge"))InterruptInspection();
            if(Profile->BeginSpellAimPreview(QuickIndex))return true;
            Profile->UseQuickBinding(QuickIndex);return true;
        }
    }
    return Super::InputKey(Params);
}

void AFPSGAMEPlayerController::PlayerTick(float DeltaTime)
{
    Super::PlayerTick(DeltaTime);
    if(SmartTurretDrawer.IsValid())
    {
        const AVillageSmartTurret* Turret=ActiveSmartTurret.Get();
        const APawn* P=GetPawn();
        if(!IsLocalController()||!IsValid(Turret)||Turret->GetHealth()<=0.f||!IsValid(P)
            ||FVector::DistSquared(P->GetActorLocation(),Turret->GetActorLocation())>FMath::Square(460.))
        {
            SmartTurretDrawer->RequestClose();
        }
    }
    if(IsLocalController()&&!(ChapelDialogue&&ChapelDialogue->IsOpen())&&!IsGameMenuOpen()&&!AlchemyPanel&&!WoodworkingPanel&&!ExpeditionPanel&&!GunsmithPanel&&!EnhancementPanel&&!SmartTurretDrawer.IsValid()
        &&(!ColdSteelHUD||(!ColdSteelHUD->IsWorldForging()&&!ColdSteelHUD->IsGunAssembly()))
        &&(!WeatherPanel||!WeatherPanel->IsPanelOpen())
        &&(!ColdSteelHUD||!ColdSteelHUD->IsInventoryOpen()))
    {
        auto* VP=GetWorld()?GetWorld()->GetGameViewport():nullptr;
        const bool bInputHeld=(VP&&VP->IgnoreInput())||IsMoveInputIgnored()||IsLookInputIgnored()
            ||(bShowMouseCursor&&!IsCursorOnlyInteraction());
        if(bInputHeld&&UGameplayStatics::GetCurrentLevelName(this,true)==TEXT("L_Dungeon_Randomized"))
        {
            bool bDungeonReady=false;
            for(TActorIterator<AActor> It(GetWorld());It;++It)
                if(It->ActorHasTag(TEXT("DungeonAssembly.Ready"))){bDungeonReady=true;break;}
            if(auto* Loading=GetGameInstance()?GetGameInstance()->GetSubsystem<UTransitLoadingSubsystem>():nullptr;
                bDungeonReady&&Loading&&!Loading->IsHoldingGameplayInput())
                Loading->ReleaseToGameplay();
        }
    }
    // ADS changes only the optical presentation. Each panel retains its own
    // visibility lifecycle (inventory, menus, death, wheel and loading states).
    // Never blanket-hide/restore top-level widgets when the scope changes.
}

void AFPSGAMEPlayerController::ToggleInventory()
{
    if (IsGameMenuOpen()) return;
    if(AlchemyPanel||WoodworkingPanel)return;
    if (WeatherPanel && WeatherPanel->IsPanelOpen()) WeatherPanel->SetPanelOpen(false);
    if (ColdSteelHUD)
    {
        ColdSteelHUD->ToggleInventory();
        UE_LOG(LogTemp, Display, TEXT("ColdSteelUI: inventory toggled, open=%s"),
            ColdSteelHUD->IsInventoryOpen() ? TEXT("true") : TEXT("false"));
    }
}

bool AFPSGAMEPlayerController::IsItemIconPanelOpen() const
{
    return (ColdSteelHUD && ColdSteelHUD->IsInventoryOpen()) || EnhancementPanel != nullptr;
}

bool AFPSGAMEPlayerController::IsCursorOnlyInteraction() const
{
    return bShowMouseCursor && !IsGameMenuOpen() && !IsMoveInputIgnored() && !IsLookInputIgnored() &&
        !AlchemyPanel && !WoodworkingPanel && !GunsmithPanel && !EnhancementPanel && !ExpeditionPanel && !SmartTurretDrawer.IsValid() && (!WeatherPanel || !WeatherPanel->IsPanelOpen()) &&
        ColdSteelHUD && !ColdSteelHUD->IsInventoryOpen() && (!VoxelBuilder || !VoxelBuilder->IsPanelOpen());
}

bool AFPSGAMEPlayerController::BlocksOngoingActions(const APlayerController* Player)
{
    if(!Player || Player->IsMoveInputIgnored() || Player->IsLookInputIgnored())return true;
    if(UFPSFurnitureRestComponent::IsResting(Player->GetPawn())||UHorseRiderComponent::UsesSaddleHands(Player->GetPawn()))return true;
    const auto* FPSPlayer=Cast<AFPSGAMEPlayerController>(Player);
    return (FPSPlayer && FPSPlayer->SiegeControl && FPSPlayer->SiegeControl->Active()) ||
        (Player->bShowMouseCursor && (!FPSPlayer || !FPSPlayer->IsCursorOnlyInteraction()));
}

bool AFPSGAMEPlayerController::IsActionPreservingPanelOpen() const
{
    if (GameMenu && GameMenu->IsWorldMapOpen()) return true;
    if(IsGameMenuOpen()||AlchemyPanel||WoodworkingPanel||SmartTurretDrawer.IsValid())return false;
    if(ColdSteelHUD&&(ColdSteelHUD->IsWorldForging()||ColdSteelHUD->IsGunAssembly()))return false;
    return (ColdSteelHUD&&(ColdSteelHUD->IsInventoryOpen()||ColdSteelHUD->IsSkillTreeOpen()))||GunsmithPanel||EnhancementPanel||ExpeditionPanel||
        (WeatherPanel&&WeatherPanel->IsPanelOpen());
}

bool AFPSGAMEPlayerController::BlocksActionContinuation(const APlayerController* Player)
{
    if(!Player||UFPSFurnitureRestComponent::IsResting(Player->GetPawn()))return true;
    const auto* FPSPlayer=Cast<AFPSGAMEPlayerController>(Player);
    if(FPSPlayer&&FPSPlayer->IsActionPreservingPanelOpen())return false;
    return BlocksOngoingActions(Player);
}

void AFPSGAMEPlayerController::ToggleTimelineInteraction()
{
    if (IsGameMenuOpen() || (ChapelDialogue && ChapelDialogue->IsOpen())) return;
    if(ColdSteelHUD&&(ColdSteelHUD->IsWorldForging()||ColdSteelHUD->IsGunAssembly()))return;
    if (AlchemyPanel || WoodworkingPanel || GunsmithPanel || EnhancementPanel || ExpeditionPanel || SmartTurretDrawer.IsValid()) return;
    if (WeatherPanel && WeatherPanel->IsPanelOpen()) return;
    if (!ColdSteelHUD || ColdSteelHUD->IsInventoryOpen()) return;
    if (bShowMouseCursor)
    {
        bShowMouseCursor = false;
        SetInputMode(FInputModeGameOnly());
        return;
    }
    bShowMouseCursor = true;
    FInputModeGameAndUI InputMode;
    // Keep keyboard focus in the viewport. Cursor clicks still reach the HUD,
    // without a focus transfer synthesizing releases of held combat inputs.
    InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    InputMode.SetHideCursorDuringCapture(false);
    SetInputMode(InputMode);
}

void AFPSGAMEPlayerController::ToggleWeatherPanel()
{
    ToggleDevelopmentPanel();
}

void AFPSGAMEPlayerController::ToggleDevelopmentPanel()
{
    if (IsGameMenuOpen()) return;
    if(AlchemyPanel||WoodworkingPanel)return;
    if (!WeatherPanel) return;
    CloseExpedition();
    if (GunsmithPanel) CloseGunsmith();
    if (EnhancementPanel) CloseEnhancement();
    if (ColdSteelHUD && ColdSteelHUD->IsInventoryOpen()) ColdSteelHUD->ToggleInventory();
    WeatherPanel->SetPanelOpen(!WeatherPanel->IsPanelOpen());
}

void AFPSGAMEPlayerController::CaptureTimelineAudit(const FString& Filename, int32 State)
{
    if (!ColdSteelHUD) return;
    ColdSteelHUD->SetEventTimelineAuditState(State);
    const FString Directory = FPaths::ProjectSavedDir() / TEXT("UIAudit/2026-09-09");
    IFileManager::Get().MakeDirectory(*Directory, true);
    FScreenshotRequest::RequestScreenshot(Directory / Filename, true, false);
}

void AFPSGAMEPlayerController::CaptureInventoryAudit(const FString& Filename, int32 State)
{
    if (!ColdSteelHUD) return;
    ColdSteelHUD->SetInventoryAuditState(State);
    const FString Directory = FPaths::ProjectSavedDir() / TEXT("UIAudit/2026-09-09");
    IFileManager::Get().MakeDirectory(*Directory, true);
    FScreenshotRequest::RequestScreenshot(Directory / Filename, true, false);
}

bool AFPSGAMEPlayerController::IsInBuildMode() const
{
    return VoxelBuilder && VoxelBuilder->IsBuilding();
}

void AFPSGAMEPlayerController::RequestVillageRepair(AVillageDefenseSection* Section)
{
    APawn* Payer=GetPawn();
    if (!IsValid(Section) || !Section->NeedsRepair() || !Payer || bShowMouseCursor || BlocksOngoingActions(this)) return;
    auto* RepairCharacter=Cast<AFPSGAMECharacter>(Payer);
    if (RepairCharacter && RepairCharacter->IsAmmoWheelOpen()) return;
    const auto* Health=Payer->FindComponentByClass<UFPSCombatHealthComponent>();
    if (Health && Health->IsDead()) return;
    if (VillageRepairPawn.Get()!=Payer)
    {
        PendingVillageRepairs.Reset();
        RecentlyRepairedSection.Reset();
        VillageRepairPawn=Payer;
    }
    if (PendingVillageRepairs.FindKey(Section) ||
        (RecentlyRepairedSection.Get()==Section && FPlatformTime::Seconds()<RepairedSectionRetryTime)) return;
    // The prompt's cached enemy sample can lag the server when a hostile dies or moves away.
    if (RepairCharacter && !Section->HasNearbyRepairEnemy(Payer)) RepairCharacter->InterruptWeaponInspection();
    const uint32 RequestId=++VillageRepairRequestId;
    PendingVillageRepairs.Add(RequestId,Section);
    ServerRepairVillageDefense(Section,Payer,RequestId);
}

void AFPSGAMEPlayerController::ServerRepairVillageDefense_Implementation(AVillageDefenseSection* Section,APawn* RequestPawn,uint32 RequestId)
{
    APawn* Payer=GetPawn();
    if (!IsValid(Section) || !IsValid(Payer) || Payer!=RequestPawn || Section->GetWorld()!=GetWorld() || BlocksOngoingActions(this))
    {
        ClientVillageRepairResult(RequestId,false,FText::GetEmpty());
        return;
    }
    if (const auto* Health=Payer->FindComponentByClass<UFPSCombatHealthComponent>(); Health && Health->IsDead())
    {
        ClientVillageRepairResult(RequestId,false,FText::GetEmpty());
        return;
    }
    if (!Section->NeedsRepair())
    {
        // Another player or an earlier request may have repaired it before replication arrived.
        ClientVillageRepairResult(RequestId,false,FText::GetEmpty());
        return;
    }
    if (ColdSteelWorldInteraction::TraceUseTargets(this).RepairTarget()!=Section)
    {
        ClientVillageRepairResult(RequestId,false,FText::FromString(TEXT("请靠近并对准尚未修复的缺口。")));
        return;
    }
    FText Reason;
    const bool bRepaired=Section->TryRepair(Payer,Reason);
    if (bRepaired)
        Reason=FText::Format(NSLOCTEXT("VillageDefense","RepairPaid","已消耗 {0} 灵魂。"),FText::AsNumber(Section->GetRepairSoulCost()));
    ClientVillageRepairResult(RequestId,bRepaired,Reason);
}

void AFPSGAMEPlayerController::ClientVillageRepairResult_Implementation(uint32 RequestId,bool bRepaired,const FText& Message)
{
    TWeakObjectPtr<AVillageDefenseSection> Section;
    if (!PendingVillageRepairs.RemoveAndCopyValue(RequestId,Section) || !Section.IsValid() ||
        Section->GetWorld()!=GetWorld() || !VillageRepairPawn.IsValid() || VillageRepairPawn.Get()!=GetPawn()) return;
    if (bRepaired && Section->NeedsRepair())
    {
        // The receipt can beat health replication. A fresh collapse can also coalesce with that update.
        RecentlyRepairedSection=Section;
        RepairedSectionRetryTime=FPlatformTime::Seconds()+0.75;
    }
    if (Message.IsEmpty()) return;
    if(auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        Model->PostNotice(bRepaired?TEXT("城防已修复"):TEXT("无法修复"),Message.ToString());
}

void AFPSGAMEPlayerController::ServerUseApartmentControl_Implementation(AApartmentDeviceControl* Control)
{
    if(IsValid(Control))Control->ToggleFrom(this);
}

void AFPSGAMEPlayerController::ServerUseHeQuePump_Implementation(AHeQuePumpControl* Control)
{if(IsValid(Control))Control->ActivateFrom(this);}

void AFPSGAMEPlayerController::OpenSmartTurretDrawer(AVillageSmartTurret* Turret)
{
    if(!IsLocalController()||GetNetMode()==NM_DedicatedServer||!IsValid(Turret)||Turret->GetHealth()<=0.f||IsInBuildMode())return;
    CloseSmartTurretDrawer();
    UGameViewportClient* VP=GetWorld()?GetWorld()->GetGameViewport():nullptr;
    if(!VP)return;
    UColdSteelStatusModel* Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    TWeakObjectPtr<AVillageSmartTurret> WeakTurret=Turret;
    SAssignNew(SmartTurretDrawer,SSmartTurretDrawer)
        .Turret(Turret)
        .Model(Model)
        .OnMount_Lambda([this,WeakTurret](const FString& InstanceId)
        {
            if(WeakTurret.IsValid())ServerSmartTurretMount(WeakTurret.Get(),InstanceId);
        })
        .OnUnmount_Lambda([this,WeakTurret]()
        {
            if(WeakTurret.IsValid())ServerSmartTurretUnmount(WeakTurret.Get());
        })
        .OnClose_Lambda([this]()
        {
            CloseSmartTurretDrawer();
        });
    ActiveSmartTurret=Turret;
    VP->AddViewportWidgetContent(SmartTurretDrawer.ToSharedRef(),45);
    FlushPressedKeys();
    SetIgnoreMoveInput(true);
    SetIgnoreLookInput(true);
    bShowMouseCursor=true;
    FInputModeGameAndUI Mode;
    Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
    Mode.SetHideCursorDuringCapture(false);
    SetInputMode(Mode);
}

void AFPSGAMEPlayerController::CloseSmartTurretDrawer()
{
    if(SmartTurretDrawer.IsValid())
    {
        if(UGameViewportClient* VP=GetWorld()?GetWorld()->GetGameViewport():nullptr)
            VP->RemoveViewportWidgetContent(SmartTurretDrawer.ToSharedRef());
        SmartTurretDrawer.Reset();
        ActiveSmartTurret.Reset();
        if(IsLocalController()&&GetNetMode()!=NM_DedicatedServer)
        {
            FlushPressedKeys();
            SetIgnoreMoveInput(false);
            SetIgnoreLookInput(false);
            bShowMouseCursor=false;
            SetInputMode(FInputModeGameOnly());
        }
    }
}

void AFPSGAMEPlayerController::ServerSmartTurretMount_Implementation(AVillageSmartTurret* Turret,const FString& ItemInstanceId)
{
    FString Message;
    const bool bOk=IsValid(Turret)&&Turret->GetWorld()==GetWorld()&&Turret->ServerMountFromPlayer(GetPawn(),ItemInstanceId,Message);
    if(!bOk && Message.IsEmpty())Message=TEXT("智能机枪塔状态异常，装载失败。");
    ClientSmartTurretResult(bOk,Message);
}

void AFPSGAMEPlayerController::ServerSmartTurretUnmount_Implementation(AVillageSmartTurret* Turret)
{
    FString Message;
    const bool bOk=IsValid(Turret)&&Turret->GetWorld()==GetWorld()&&Turret->ServerUnmountToPlayer(GetPawn(),Message);
    if(!bOk && Message.IsEmpty())Message=TEXT("智能机枪塔状态异常，卸下失败。");
    ClientSmartTurretResult(bOk,Message);
}

void AFPSGAMEPlayerController::ClientSmartTurretResult_Implementation(bool bSuccess,const FString& Message)
{
    if(SmartTurretDrawer.IsValid())
    {
        SmartTurretDrawer->SetFeedback(bSuccess,Message);
        SmartTurretDrawer->RefreshAll();
    }
    if(auto* Model=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr)
    {
        if(!Message.IsEmpty())Model->PostNotice(bSuccess?TEXT("智能机枪塔"):TEXT("操作失败"),Message);
    }
}


void AFPSGAMEPlayerController::RefreshRegionMusic()
{
    if(!IsLocalController()||GetNetMode()==NM_DedicatedServer)return;
    const FString Level=UGameplayStatics::GetCurrentLevelName(this,true);
    FString Path;
    if(UDungeonRoomSubsystem::IsDungeonPawn(GetPawn()) || Level==TEXT("L_Dungeon_Randomized"))
        Path=TEXT("/Game/Audio/DungeonBGM20261017/S_DungeonEcho.S_DungeonEcho");
    else if(Level==TEXT("L_TemperateHills_Initial") || Level==TEXT("L_ForestPathVillage"))
        Path=TEXT("/Game/Audio/HillsDesertBGM/S_HillsDesert.S_HillsDesert");
    else if(Level==TEXT("DayNight_Lighting"))
        Path=TEXT("/Game/Audio/GodSpaceBGM20261002/S_RomanCourtyard.S_RomanCourtyard");
    if(Path==RegionMusicPath)return;
    RegionMusicPath=Path;const uint32 Serial=++RegionMusicSerial;
    if(HubMusic)HubMusic->Stop();
    if(Path.IsEmpty())return;
    if(!HubMusic)
    {
        HubMusic=NewObject<UAudioComponent>(this);HubMusic->bAutoActivate=false;HubMusic->bAutoDestroy=false;
        HubMusic->bStopWhenOwnerDestroyed=true;HubMusic->bAllowSpatialization=false;HubMusic->RegisterComponent();
    }
    HubMusic->SetVolumeMultiplier(.6f*HubMusicUserVolume);
    const FSoftObjectPath MusicPath(Path);
    UAssetManager::GetStreamableManager().RequestAsyncLoad(MusicPath,FStreamableDelegate::CreateWeakLambda(this,[this,MusicPath,Serial]()
    {
        if(!HasActorBegunPlay()||RegionMusicSerial!=Serial||!IsValid(HubMusic))return;
        if(auto* Sound=Cast<USoundBase>(MusicPath.ResolveObject())){HubMusic->SetSound(Sound);HubMusic->FadeIn(1.5f,1.f);}
    }));
}
