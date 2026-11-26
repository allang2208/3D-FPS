#include "FPSGAMEGameMode.h"
#include "Dungeons/DungeonRoomSubsystem.h"
#include "FPSGAMECharacter.h"
#include "FPSGAMEPlayerController.h"
#include "Multiplayer/ColdSteelPlayerState.h"
#include "FPSWeatherManager.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "SceneSpawnValidation.h"
#include "SceneTestPortal.h"
#include "Water/ClearwaterWater.h"
#include "GameFramework/PlayerStart.h"
#include "GameFramework/GameSession.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/Engine.h"
#include "Engine/TargetPoint.h"
#include "TimerManager.h"

AFPSGAMEGameMode::AFPSGAMEGameMode()
{
    DefaultPawnClass = AFPSGAMECharacter::StaticClass();
    PlayerControllerClass = AFPSGAMEPlayerController::StaticClass();
    // 联机玩家数据归属：所有继承本基类的 GameMode（含地图级 TemperateHills、联机 NetGameMode）
    // 统一产出 AColdSteelPlayerState——公开快照全员复制、私有档案仅拥有者、服务端影子档案。
    // 单机场景下它自然空转（NetMode==Standalone 时各 Tick 分支直接返回）。
    PlayerStateClass = AColdSteelPlayerState::StaticClass();
}

void AFPSGAMEGameMode::InitGame(const FString& MapName,const FString& Options,FString& ErrorMessage)
{
    Super::InitGame(MapName,Options,ErrorMessage);
    ServerPassword=UGameplayStatics::ParseOption(Options,TEXT("Password"));
    if(GameSession){GameSession->MaxPlayers=4;GameSession->MaxSpectators=0;}
}

void AFPSGAMEGameMode::PreLogin(const FString& Options,const FString& Address,const FUniqueNetIdRepl& UniqueId,FString& ErrorMessage)
{
    // The session may have been created after InitGame and before BeginPlay.
    if(GameSession){GameSession->MaxPlayers=4;GameSession->MaxSpectators=0;}
    if(!ServerPassword.IsEmpty())
    {
        const FString Supplied=UGameplayStatics::ParseOption(Options,TEXT("Password"));
        if(Supplied!=ServerPassword)
        {
            ErrorMessage=TEXT("房间口令错误");
            return;
        }
    }
    Super::PreLogin(Options,Address,UniqueId,ErrorMessage);
}

AActor* AFPSGAMEGameMode::ChoosePlayerStart_Implementation(AController* Player)
{
    AActor* Start = Super::ChoosePlayerStart_Implementation(Player);
    if (Start || UGameplayStatics::GetCurrentLevelName(this, true) != TEXT("L_ForestPathForest"))
    {
        return Start;
    }

    // The engine falls back to the world origin if its collision query rejects every start.
    // On this map the trail is over 250 metres away. Use a surveyed trail slot for that fallback.
    static const FName TrailTag(TEXT("ForestPathEntrance"));
    double BestClearance = -1.;
    for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
    {
        if (It->PlayerStartTag != TrailTag) continue;
        double Clearance = TNumericLimits<double>::Max();
        for (auto Controllers = GetWorld()->GetPlayerControllerIterator(); Controllers; ++Controllers)
        {
            const APlayerController* Other = Controllers->Get();
            if (Other && Other != Player && Other->GetPawn())
            {
                Clearance = FMath::Min(Clearance, FVector::DistSquared(It->GetActorLocation(), Other->GetPawn()->GetActorLocation()));
            }
        }
        if (Clearance > BestClearance)
        {
            Start = *It;
            BestClearance = Clearance;
        }
    }
    return Start;
}

void AFPSGAMEGameMode::RestartPlayer(AController* NewPlayer)
{
    const FString Map = UGameplayStatics::GetCurrentLevelName(this, true);
    if(auto* Room=UDungeonRoomSubsystem::Get(GetWorld()))
        if(auto* PS=NewPlayer?NewPlayer->GetPlayerState<AColdSteelPlayerState>():nullptr;PS&&PS->bInDungeonRoom)
        {
            if(NewPlayer->GetPawn())return;
            FTransform Spawn;
            if(Room->FindSpawn(true,nullptr,Spawn))RestartPlayerAtTransform(NewPlayer,Spawn);
            return;
        }
    // The dungeon is deliberately NOT on this list: FindSafeSpawn probes from +500 cm
    // above each PlayerStart, which starts inside the dungeon's floor-1 ceiling slab,
    // so every probe is rejected as initially penetrating and no pawn spawns.
    if (Map != TEXT("DayNight_Lighting") && Map != TEXT("L_Normandy_FPS_Test") && Map != TEXT("L_MilitaryTrench_FPS_Test"))
    {
        Super::RestartPlayer(NewPlayer);
        return;
    }
    if (!IsValid(NewPlayer) || NewPlayer->GetPawn()) return;
    if (PendingSceneSpawns.Contains(NewPlayer)) return;
    PendingSceneSpawns.Add(NewPlayer, 0);
    if (Map == TEXT("L_MilitaryTrench_FPS_Test"))
    {
        FTimerHandle Handle;
        GetWorldTimerManager().SetTimer(Handle, FTimerDelegate::CreateUObject(this,
            &AFPSGAMEGameMode::SpawnAfterStreaming, TWeakObjectPtr<AController>(NewPlayer)), .5f, false);
        return;
    }
    SpawnAfterStreaming(NewPlayer);
}

void AFPSGAMEGameMode::SpawnAfterStreaming(TWeakObjectPtr<AController> Player)
{
    AController* NewPlayer = Player.Get();
    if (!NewPlayer || NewPlayer->GetWorld() != GetWorld() || NewPlayer->GetPawn())
    {
        PendingSceneSpawns.Remove(Player);
        return;
    }
    GetWorld()->FlushLevelStreaming(EFlushLevelStreamingType::Full);
    const FString Map = UGameplayStatics::GetCurrentLevelName(this, true);
    for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
    {
        if(UDungeonRoomSubsystem::Supports(GetWorld())&&UDungeonRoomSubsystem::IsDungeonActor(*It))continue;
        FVector Safe;
        if (!USceneSpawnValidation::FindSafeSpawn(this, It->GetActorLocation(), Safe)) continue;
        // Evaluate after runtime collision is created, not just in the editor.
        RestartPlayerAtTransform(NewPlayer, FTransform(It->GetActorRotation(), Safe));
        if (NewPlayer->GetPawn())
        {
            PendingSceneSpawns.Remove(Player);
            UE_LOG(LogTemp, Display, TEXT("SceneSpawn: Runtime spawn %s at %s"), *Map, *Safe.ToString());
            return;
        }
    }
    // Seamless travel may restart the host before streamed runtime collision is
    // registered. Keep the controller pending and retry the same safe queries.
    // Never substitute an unchecked position or create duplicate retry chains.
    if (++PendingSceneSpawns.FindOrAdd(Player) < 20)
    {
        FTimerHandle Handle;
        GetWorldTimerManager().SetTimer(Handle, FTimerDelegate::CreateUObject(this,
            &AFPSGAMEGameMode::SpawnAfterStreaming, Player), .5f, false);
        return;
    }
    PendingSceneSpawns.Remove(Player);
    // Never let GameMode's no-start fallback place a character at world origin.
    UE_LOG(LogTemp, Error, TEXT("SceneSpawn: Spawn blocked in %s; no safe start. No pawn spawned."), *Map);
    if (GEngine) GEngine->AddOnScreenDebugMessage(-1, 20.f, FColor::Red, TEXT("未找到安全出生点，请检查 PlayerStart 和周围的碰撞。"));
}

void AFPSGAMEGameMode::BeginPlay()
{
    Super::BeginPlay();
    // The project is a four-player co-op listen server. AGameModeBase has no
    // MaxPlayers of its own, so pin the engine GameSession before any login.
    if(GameSession)
    {
        GameSession->MaxPlayers=4;
        GameSession->MaxSpectators=0;
    }
    TryInstallHillsPortal();

    // Keep the isolated UI acceptance route independent from world/weather work.
    if (FParse::Param(FCommandLine::Get(), TEXT("ColdSteelUIAudit")))
    {
        return;
    }

    for (TActorIterator<AFPSWeatherManager> It(GetWorld()); It; ++It)
    {
        return;
    }

    GetWorld()->SpawnActor<AFPSWeatherManager>();
}

void AFPSGAMEGameMode::TryInstallHillsPortal()
{
    UWorld* World = GetWorld();
    if (!World) return;
    // Preserve configuration of explicitly authored shared water actors.
    AClearwaterWater::Install(World);
    // Retry the retained two-way hills link until its pawn exists.
    const int32 HillsResult = ASceneTestPortal::InstallHillsLink(World);
    if (HillsResult != 0) return;
    TWeakObjectPtr<AFPSGAMEGameMode> Weak(this);
    FTimerHandle Handle;
    World->GetTimerManager().SetTimer(Handle, FTimerDelegate::CreateLambda([Weak]()
    {
        if (auto* Self = Weak.Get()) Self->TryInstallHillsPortal();
    }), .5f, false);
}
