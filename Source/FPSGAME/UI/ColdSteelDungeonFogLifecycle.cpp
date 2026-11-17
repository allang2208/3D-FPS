#include "ColdSteelDungeonFogCheckCommandlet.h"
#if WITH_EDITOR
#include "ColdSteelDungeonMap.h"
#include "ColdSteelWorldMapData.h"
#include "ColdSteelMapMarkers.h"
#include "ColdSteelHubMapRegistration.h"
#include "SColdSteelWorldMap.h"
#include "SColdSteelMapMarkerEditor.h"
#include "../Dungeons/AuthoredDungeonGenerator.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelMapMarkerSharing.h"
#include "../SceneTestPortal.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Engine/Level.h"
#include "Engine/Engine.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StreamableManager.h"
#include "Engine/Texture2D.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/GameStateBase.h"
#include "UObject/UnrealType.h"
#include "Framework/Application/SlateApplication.h"
#endif

int32 UColdSteelDungeonFogCheckCommandlet::CheckNetworkLifecycle()
{
#if WITH_EDITOR
    UWorld::InitializationValues Settings;
    Settings.AllowAudioPlayback(false).RequiresHitProxies(false).CreatePhysicsScene(true)
        .CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UPackage* HubPackage=CreatePackage(TEXT("/Temp/FogLifecycle/DayNight_Lighting"));
    UWorld* World=UWorld::CreateWorld(EWorldType::Editor,false,TEXT("DayNight_Lighting"),HubPackage,true,ERHIFeatureLevel::Num,&Settings);
    if (!World) return 1;
    World->WorldType=EWorldType::PIE;
    World->SetPlayInEditorInitialNetMode(NM_ListenServer);
    auto* Room=World->GetSubsystem<UDungeonRoomSubsystem>();
    auto* Run=World->GetSubsystem<UDungeonRunSubsystem>();
    if (!Room || !Run) { World->DestroyWorld(false); return 2; }
    int32 Checks=0,Failures=0;
    auto Expect=[&](bool Value,const TCHAR* Name)
    {
        ++Checks;
        if (!Value) { ++Failures; UE_LOG(LogTemp,Error,TEXT("DungeonFogLifecycle: %s"),Name); }
    };
    Expect(UDungeonRoomSubsystem::Supports(World),TEXT("fixture must use streamed multiplayer dungeon routing"));
    auto MakeLevel=[&](const TCHAR* Name)
    {
        auto* LevelWorld=UWorld::CreateWorld(EWorldType::Inactive,false,NAME_None,CreatePackage(Name),false,ERHIFeatureLevel::Num,&Settings,true);
        ULevel* Level=LevelWorld->PersistentLevel;
        Level->OwningWorld=World;
        Level->bIsVisible=true;
        World->AddLevel(Level);
        return Level;
    };
    ULevel* First=MakeLevel(TEXT("/Temp/SessionDungeon_FogFirst"));
    ULevel* Second=MakeLevel(TEXT("/Temp/SessionDungeon_FogSecond"));
    Room->RoomState=World->SpawnActor<ADungeonRoomState>();
    Room->Streaming=NewObject<ULevelStreamingDynamic>(World);
    auto* LoadedLevel=FindFProperty<FObjectPropertyBase>(ULevelStreaming::StaticClass(),TEXT("LoadedLevel"));
    if (!LoadedLevel || !Room->RoomState) { World->DestroyWorld(false); return 3; }
    auto Install=[&](ULevel* Level,const TCHAR* RunId)
    {
        FActorSpawnParameters Params;
        Params.OverrideLevel=Level;
        auto* Generator=World->SpawnActor<AAuthoredDungeonGenerator>(AAuthoredDungeonGenerator::StaticClass(),FTransform::Identity,Params);
        Generator->NetworkRunId=RunId;
        Generator->Tags.Add(TEXT("DungeonAssembly.Ready"));
        Run->Generator=Generator;
        Run->CurrentRunId=RunId;
        Run->bActive=true;
        Room->RoomState->Instance=FGuid::NewGuid();
        Room->LoadedInstance=Room->RoomState->Instance;
        LoadedLevel->SetObjectPropertyValue_InContainer(Room->Streaming,Level);
        Run->Nodes.Reset();
        auto& Node=Run->Nodes.AddDefaulted_GetRef();
        Node.Id=0; Node.Module=TEXT("FacilityReceptionHall");
        Node.Origin=UDungeonRoomSubsystem::DungeonOffset();
        Node.Volume=FBox(Node.Origin-FVector(1000,1000,5),Node.Origin+FVector(3000,1000,400));
        Node.WalkCells.Add(Node.Volume);
        Run->StartPosition=Node.Origin;
        return Generator;
    };
    Install(First,TEXT("FogRunA"));
    auto MakePlayer=[&](bool Local)
    {
        auto* PC=World->SpawnActor<APlayerController>();
        auto* Pawn=World->SpawnActor<ACharacter>();
        PC->Possess(Pawn);
        auto* PS=World->SpawnActor<AColdSteelPlayerState>();
        PS->SetOwner(PC);
        PC->SetPlayerState(PS);
        Pawn->SetPlayerState(PS);
        PS->bInDungeonRoom=true;
        if (Local)
        {
            PC->Player=NewObject<ULocalPlayer>(GEngine);PC->SetAsLocalPlayerController();
            // This fixture has no GameMode/BeginPlay to create the normal camera manager.
            if(!PC->PlayerCameraManager)
            {
                PC->PlayerCameraManager=World->SpawnActor<APlayerCameraManager>();
                if(PC->PlayerCameraManager)PC->PlayerCameraManager->InitializeFor(PC);
            }
        }
        Pawn->SetActorEnableCollision(false);
        return PC;
    };
    auto* Host=MakePlayer(true);
    auto* Guest=MakePlayer(true);
    auto* Remote=MakePlayer(false);
    auto Place=[&](APlayerController* PC,FVector XY)
    {
        auto* Pawn=CastChecked<ACharacter>(PC->GetPawn());
        Pawn->SetActorLocation(XY+FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()));
        Pawn->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    };
    const FVector A=Run->EntryPosition()+FVector(100,100,0), B=A+FVector(1400,0,0), C=B+FVector(800,0,0);
    Place(Host,A);Place(Guest,B);Place(Remote,C);
    FColdSteelDungeonMap HostFog,GuestFog,RemoteFog;
    Expect(HostFog.Update(Host)&&GuestFog.Update(Guest),TEXT("both local owners can chart their own positions"));
    for (auto* PC : {Host,Guest})
    {
        const auto& Fog=PC==Host?HostFog:GuestFog;
        const FVector Expected=PC==Host?A:B;
        UE_LOG(LogTemp,Display,TEXT("DungeonFogLifecycle: %s expected %s sampled %s floor %d footprint %d patches %d"),
            *PC->GetName(),*Expected.ToString(),*Fog.LastSample.ToString(),Fog.PlayerFloor,Fog.LastFootprint,
            Fog.Layers.Contains(0)?Fog.Layers.FindChecked(0).Patches.Num():0);
    }
    Expect(HostFog.IsKnown(FVector2D(A),0)&&!HostFog.IsKnown(FVector2D(B),0),TEXT("guest exploration leaked into host"));
    Expect(GuestFog.IsKnown(FVector2D(B),0)&&!GuestFog.IsKnown(FVector2D(A),0),TEXT("host exploration leaked into guest"));
    Expect(!RemoteFog.Update(Remote)&&RemoteFog.Layers.IsEmpty(),TEXT("remote server controller wrote a local map"));
    const uint32 HostRevision=HostFog.Revision;
    Expect(!HostFog.Update(Guest)&&HostFog.Revision==HostRevision,TEXT("foreign local owner overwrote host exploration"));
    auto* HostState=Host->GetPawn()->GetPlayerState<AColdSteelPlayerState>();
    auto* GuestState=Guest->GetPawn()->GetPlayerState<AColdSteelPlayerState>();

    auto HostMarkers=MakeUnique<FColdSteelMapMarkers>();
    auto GuestMarkers=MakeUnique<FColdSteelMapMarkers>();
    HostMarkers->Update(Host,HostFog,true);GuestMarkers->Update(Guest,GuestFog,true);
    FColdSteelMapMarker HostMark;
    HostMark.Region=TEXT("L_Dungeon_Randomized/FogRunA");HostMark.Area=TEXT("fixture");
    HostMark.Position=A;HostMark.bDungeon=true;HostMark.LayoutSerial=HostFog.LayoutSerial;
    HostMark.Label=TEXT("Host");HostMark.ColorIndex=2;
    FColdSteelMapMarker GuestMark=HostMark;
    GuestMark.Position=B;GuestMark.Label=TEXT("Guest");GuestMark.LayoutSerial=GuestFog.LayoutSerial;
    Expect(HostMarkers->Save(HostMark)&&GuestMarkers->Save(GuestMark),TEXT("owners could not create their own markers"));
    Expect(!HostMarkers->Find(GuestMark.Id)&&!GuestMarkers->Find(HostMark.Id),TEXT("personal markers crossed owner boundaries"));
    for(int32 I=1;I<FColdSteelMapMarkers::Limit;++I)
    {
        FColdSteelMapMarker Extra=HostMark;Extra.Id.Invalidate();
        Expect(HostMarkers->Save(Extra),TEXT("marker capacity rejected a free slot"));
    }
    FColdSteelMapMarker Overflow=HostMark;Overflow.Id.Invalidate();
    Expect(!HostMarkers->Save(Overflow)&&HostMarkers->All().Num()==10,TEXT("marker capacity exceeded ten"));
    HostMark.Label=TEXT("Updated");HostMark.ColorIndex=999;
    Expect(HostMarkers->Save(HostMark)&&HostMark.ColorIndex==FColdSteelMapMarkers::ColorCount-1,
        TEXT("editing at capacity or colour normalization failed"));
    Expect(FColdSteelMapMarkers::CleanLabel(TEXT("  A\nB\t  "))==TEXT("AB"),TEXT("marker labels retained controls"));
    Host->SetViewTarget(Host->GetPawn());Guest->SetViewTarget(Guest->GetPawn());
    HostMarkers->Update(Host,HostFog,true);GuestMarkers->Update(Guest,GuestFog,true);
    if(HostMarkers->BeamAssets)HostMarkers->BeamAssets->WaitUntilComplete();
    if(GuestMarkers->BeamAssets)GuestMarkers->BeamAssets->WaitUntilComplete();
    HostMarkers->Update(Host,HostFog,true);GuestMarkers->Update(Guest,GuestFog,true);
    auto HostBeam=HostMarkers->Beams.FindRef(HostMark.Id);
    auto GuestBeam=GuestMarkers->Beams.FindRef(GuestMark.Id);
    Expect(HostBeam.IsValid()&&GuestBeam.IsValid(),TEXT("marker beam assets did not create local actors"));
    Expect(HostBeam.IsValid()&&!HostBeam->GetIsReplicated()&&HostBeam->GetOwner()==Host->GetViewTarget(),
        TEXT("host beam replicated or used the controller instead of the view target"));
    HostMarkers->Update(Guest,GuestFog,true);
    Expect(HostMarkers->Owner.Get()==Host&&HostBeam.IsValid()&&HostBeam->GetOwner()==Host->GetViewTarget(),
        TEXT("foreign owner rebound the host marker beam"));
    APawn* OldPawn=Host->GetPawn();
    auto* NewPawn=World->SpawnActor<ACharacter>();NewPawn->SetActorEnableCollision(false);
    Host->Possess(NewPawn);NewPawn->SetPlayerState(HostState);Host->SetViewTarget(NewPawn);Place(Host,A);
    HostFog.Update(Host);HostMarkers->Update(Host,HostFog,true);
    UE_LOG(LogTemp,Display,TEXT("DungeonFogLifecycle: respawn known=%d marker=%d beam=%d owner=%s view=%s new=%s controlled=%s floor=%d"),
        HostFog.IsKnown(FVector2D(A),0),HostMarkers->Find(HostMark.Id)!=nullptr,HostBeam.IsValid(),
        HostBeam.IsValid()?*GetNameSafe(HostBeam->GetOwner()):TEXT("none"),*GetNameSafe(Host->GetViewTarget()),
        *GetNameSafe(NewPawn),*GetNameSafe(Host->GetPawn()),HostFog.PlayerFloor);
    Expect(HostFog.IsKnown(FVector2D(A),0)&&HostMarkers->Find(HostMark.Id)&&HostBeam.IsValid()&&HostBeam->GetOwner()==NewPawn,
        TEXT("respawn lost navigation or left the beam owned by the previous pawn"));
    OldPawn->Destroy();
    if(FSlateApplication::IsInitialized())
    {
        auto Session=MakeShared<FColdSteelWorldMapSession>();
        TSharedPtr<SColdSteelMapMarkerEditor> Editor=SNew(SColdSteelMapMarkerEditor,Host,Session);
        Host->SetIgnoreMoveInput(true);
        Editor->Begin(Overflow);Editor->Cancel();
        Expect(!Session->bEditingMarker&&Host->IsMoveInputIgnored(),TEXT("cancel removed another system's movement lock"));
        Host->SetIgnoreMoveInput(false);
        Editor->Begin(Overflow);
        Expect(Session->bEditingMarker&&Host->IsMoveInputIgnored(),TEXT("marker edit did not own a movement lock"));
        Editor.Reset();
        Expect(!Session->bEditingMarker&&!Host->IsMoveInputIgnored(),TEXT("closing an editing map left movement locked"));
    }
    else UE_LOG(LogTemp,Display,TEXT("DungeonFogLifecycle: Slate input checks skipped (no Slate application)"));
    HostState->bInDungeonRoom=false;
    Place(Host,FVector::ZeroVector);
    Expect(!HostFog.Update(Host)&&HostFog.IsKnown(FVector2D(A),0),TEXT("hub return erased surviving run exploration"));
    HostMarkers->Update(Host,HostFog,false);GuestMarkers->Update(Guest,GuestFog,true);
    Expect(HostMarkers->Find(HostMark.Id)&&!HostMarkers->IsActive(HostMark)&&HostBeam.IsValid()&&HostBeam->IsHidden(),
        TEXT("hub return erased a surviving marker or left its beam visible"));
    Expect(GuestMarkers->IsActive(GuestMark)&&GuestBeam.IsValid()&&!GuestBeam->IsHidden(),TEXT("host return hid the guest's marker"));
    HostMarkers->Remove(HostMarkers->All().Last().Id);
    FColdSteelMapMarker HubMark;HubMark.Region=TEXT("DayNight_Lighting");HubMark.Label=TEXT("Hub");
    Expect(HostMarkers->Save(HubMark)&&HostMarkers->IsActive(HubMark),TEXT("hub marker could not coexist with dungeon markers"));
    Place(Guest,C); GuestFog.Update(Guest);
    Expect(!HostFog.IsKnown(FVector2D(C),0)&&GuestFog.IsKnown(FVector2D(C),0),TEXT("remaining teammate shared discoveries with hub player"));
    FColdSteelWorldMapData Data;
    FColdSteelMapSurfaceCache Cache;
    Data.Open(Host->GetPawn(),Cache,HostFog);
    Expect(!Data.bDungeon && Data.RegionKey==TEXT("DayNight_Lighting"),TEXT("return displayed dungeon over the hub"));
    auto* HubPhoto=LoadObject<UTexture2D>(nullptr,UColdSteelHubMapRegistration::TexturePath);
    const auto* Registration=HubPhoto?Cast<UColdSteelHubMapRegistration>(HubPhoto->GetAssetUserDataOfClass(UColdSteelHubMapRegistration::StaticClass())):nullptr;
    UE_LOG(LogTemp,Display,TEXT("DungeonFogLifecycle: hub photo=%s width=%.1f platform=%dx%d source=%dx%d"),
        *GetNameSafe(HubPhoto),Registration?Registration->WidthCm:0.,HubPhoto?HubPhoto->GetSizeX():-1,HubPhoto?HubPhoto->GetSizeY():-1,
        HubPhoto?HubPhoto->Source.GetSizeX():-1,HubPhoto?HubPhoto->Source.GetSizeY():-1);
    // NullRHI intentionally omits GPU platform data; inspect the saved source pixels.
    Expect(Registration&&Registration->WidthCm>0.&&HubPhoto->Source.GetSizeX()==2048&&HubPhoto->Source.GetSizeY()==2048,
        TEXT("saved orthographic hub map or world registration is missing"));
    Data.Open(Host->GetPawn(),Cache,HostFog);
    Expect(Data.Surface.Get()==HubPhoto&&Data.Bounds.GetSize().X>0.,TEXT("hub map did not use its saved orthographic image"));
    HostState->RoomTransferToken=FGuid::NewGuid();
    HostState->bInDungeonRoom=true;
    Place(Host,C);
    Expect(!HostFog.Update(Host)&&!HostFog.IsKnown(FVector2D(C),0),TEXT("pending entry revealed destination"));
    HostMarkers->Update(Host,HostFog,false);
    Expect(!HostMarkers->IsActive(HostMark)&&HostBeam.IsValid()&&HostBeam->IsHidden(),TEXT("pending entry exposed marker navigation"));
    Data.Open(Host->GetPawn(),Cache,HostFog);
    Expect(Data.bWaitingForDungeon,TEXT("pending entry displayed a ready map"));
    HostState->RoomTransferToken.Invalidate();
    Place(Host,A);
    Expect(HostFog.Update(Host)&&HostFog.SamplingPawn.Get()==Host->GetPawn()&&HostFog.LastSample!=FVector(UE_DOUBLE_BIG_NUMBER),
        TEXT("same-position reentry skipped the first sample"));
    Expect(HostFog.IsKnown(FVector2D(A),0)&&!HostFog.IsKnown(FVector2D(B),0),TEXT("reentry lost or merged exploration"));
    HostMarkers->Update(Host,HostFog,true);
    Expect(HostMarkers->IsActive(HostMark)&&HostBeam.IsValid()&&!HostBeam->IsHidden(),TEXT("same-run reentry did not restore the personal marker"));

    World->SetPlayInEditorInitialNetMode(NM_Client);
    FDungeonSharedProgress Snapshot;
    Snapshot.RunId=Run->RunId();Snapshot.Revision=1;
    Snapshot.Explored.Add(Run->RoomKey(0));Snapshot.Cleared.Add(Run->RoomKey(0));
    Run->ApplySharedProgress(Snapshot);
    Expect(Run->IsRoomExplored(0),TEXT("client shared progress fixture did not apply"));
    HostFog.Update(Host); GuestFog.Update(Guest);
    Expect(!HostFog.IsKnown(FVector2D(B),0)&&!GuestFog.IsKnown(FVector2D(A),0),TEXT("replicated objective exploration unlocked personal fog"));

    HostState->bInDungeonRoom=false;GuestState->bInDungeonRoom=false;
    Room->RoomState->Instance.Invalidate(); // Run remains bound until the old level's later EndPlay.
    Expect(!Run->MapLevel(),TEXT("retired descriptor still exposes the old active run"));
    HostFog.Update(Host);GuestFog.Update(Guest);
    Expect(HostFog.Layers.IsEmpty()&&GuestFog.Layers.IsEmpty(),TEXT("last-player return kept retired exploration"));
    HostMarkers->Update(Host,HostFog,false);GuestMarkers->Update(Guest,GuestFog,false);
    Expect(HostMarkers->All().Num()==1&&HostMarkers->Find(HubMark.Id)&&!HostMarkers->Find(HostMark.Id)&&GuestMarkers->All().IsEmpty(),
        TEXT("retired run kept dungeon markers or deleted the hub marker"));
    Expect((!HostBeam.IsValid()||HostBeam->IsActorBeingDestroyed())&&(!GuestBeam.IsValid()||GuestBeam->IsActorBeingDestroyed()),
        TEXT("retired run left marker beam actors alive"));
    First->bIsVisible=false;
    auto* SecondGenerator=Install(Second,TEXT("FogRunB"));
    HostState->bInDungeonRoom=true;GuestState->bInDungeonRoom=true;
    Place(Host,B);Place(Guest,A);
    HostFog.Update(Host); GuestFog.Update(Guest);
    Expect(HostFog.IsKnown(FVector2D(B),0)&&!HostFog.IsKnown(FVector2D(A),0),TEXT("new run reused host's old footprint IDs"));
    Expect(GuestFog.IsKnown(FVector2D(A),0)&&!GuestFog.IsKnown(FVector2D(B),0),TEXT("new run reused guest's old exploration"));
    HostMarkers->Update(Host,HostFog,true);GuestMarkers->Update(Guest,GuestFog,true);
    Expect(!HostMarkers->Find(HostMark.Id)&&!GuestMarkers->Find(GuestMark.Id)&&HostMarkers->Find(HubMark.Id),
        TEXT("new run restored old dungeon markers or erased a different region"));
    Data.Open(Host->GetPawn(),Cache,HostFog);
    Expect(Data.RegionKey==TEXT("L_Dungeon_Randomized/FogRunB")&&!Data.bWaitingForDungeon,TEXT("new run retained old map key"));
    FActorSpawnParameters Params;
    Params.OverrideLevel=First;
    auto* OldPortal=World->SpawnActor<ASceneTestPortal>(ASceneTestPortal::StaticClass(),FTransform(A),Params);
    First->bIsVisible=true; // A late visibility/unload event must still fail exact-instance membership.
    Expect(OldPortal && !Data.TrackLandmark(OldPortal),TEXT("retiring instance's portal entered the new map"));
    Params.OverrideLevel=Second;
    auto* NewPortal=World->SpawnActor<ASceneTestPortal>(ASceneTestPortal::StaticClass(),FTransform(B),Params);
    Expect(NewPortal&&Data.TrackLandmark(NewPortal),TEXT("current instance portal was rejected"));
    Snapshot.Revision=2;Run->ApplySharedProgress(Snapshot);HostFog.Update(Host);
    Expect(!HostFog.IsKnown(FVector2D(A),0),TEXT("late prior-run progress restored old fog"));

    SecondGenerator->NetworkRunId=TEXT("FogRunC");
    SecondGenerator->Tags.Remove(TEXT("DungeonAssembly.Ready"));
    Data.Open(Host->GetPawn(),Cache,HostFog);
    Expect(Data.bWaitingForDungeon&&HostFog.Layers.IsEmpty(),TEXT("regeneration reused old ready layout"));
    SecondGenerator->Tags.Add(TEXT("DungeonAssembly.Ready"));
    Expect(!Run->MapLevel(),TEXT("different network RunId accepted before graph rebind"));
    Run->CurrentRunId=TEXT("FogRunC");Place(Host,A);
    Data.Open(Host->GetPawn(),Cache,HostFog);
    Expect(!Data.bWaitingForDungeon&&HostFog.IsKnown(FVector2D(A),0)&&!HostFog.IsKnown(FVector2D(B),0),
        TEXT("same-level regeneration failed to reset discovery"));

    // Shared pin snapshots carry navigation, never the receiver's exploration.
    World->SetPlayInEditorInitialNetMode(NM_ListenServer);
    auto* GameState=World->SpawnActor<AGameStateBase>();World->SetGameState(GameState);
    GameState->AddPlayerState(HostState);GameState->AddPlayerState(GuestState);
    Place(Guest,B);GuestFog.Update(Guest);HostFog.Update(Host);
    HostMarkers->Update(Host,HostFog,true);GuestMarkers->Update(Guest,GuestFog,true);
    FColdSteelMapMarker SharedMark;
    SharedMark.Region=TEXT("L_Dungeon_Randomized/FogRunC");SharedMark.Label=TEXT("Shared room");
    SharedMark.bDungeon=true;SharedMark.LayoutSerial=HostFog.LayoutSerial;SharedMark.Position=A;
    SharedMark.Visibility=EColdSteelMapMarkerVisibility::Team;
    auto* HostSharing=UColdSteelMapMarkerSharing::For(Host);
    auto* GuestSharing=UColdSteelMapMarkerSharing::For(Guest);
    Expect(HostSharing&&GuestSharing,TEXT("PlayerState did not own a sharing component"));
    Expect(HostMarkers->Save(SharedMark)&&HostSharing->Shared().Num()==1,TEXT("current-run shared marker was rejected"));
    HostMarkers->Update(Host,HostFog,true);GuestMarkers->Update(Guest,GuestFog,true);
    const auto* Received=GuestMarkers->Find(SharedMark.Id);
    Expect(Received&&Received->bReadOnly&&!GuestFog.IsKnown(FVector2D(A),0),TEXT("shared location missing or revealed receiver fog"));
    const int32 GuestOwn=GuestMarkers->OwnedCount();GuestMarkers->Remove(SharedMark.Id);
    Expect(GuestMarkers->Find(SharedMark.Id)&&GuestMarkers->OwnedCount()==GuestOwn,TEXT("teammate deleted an unowned shared pin"));
    HostState->bInDungeonRoom=false;Place(Host,FVector::ZeroVector);HostFog.Update(Host);
    HostSharing->TickComponent(.5f,LEVELTICK_All,nullptr);HostMarkers->Update(Host,HostFog,false);GuestMarkers->Update(Guest,GuestFog,true);
    Expect(HostSharing->Shared().Num()==1&&GuestMarkers->Find(SharedMark.Id)&&!HostMarkers->IsActive(SharedMark),
        TEXT("individual hub return erased a surviving run's shared marker"));
    HostState->bInDungeonRoom=true;Place(Host,A);HostFog.Update(Host);HostMarkers->Update(Host,HostFog,true);
    Expect(HostMarkers->Find(SharedMark.Id)&&HostMarkers->IsActive(SharedMark),TEXT("same-run reentry lost the shared marker"));
    HostState->bInDungeonRoom=false;GuestState->bInDungeonRoom=false;Room->RoomState->Instance.Invalidate();
    HostSharing->TickComponent(.5f,LEVELTICK_All,nullptr);GuestSharing->TickComponent(.5f,LEVELTICK_All,nullptr);
    HostFog.Update(Host);GuestFog.Update(Guest);HostMarkers->Update(Host,HostFog,false);GuestMarkers->Update(Guest,GuestFog,false);
    Expect(HostSharing->Shared().IsEmpty()&&!GuestMarkers->Find(SharedMark.Id),TEXT("retired run left a shared marker on a teammate"));
    Install(Second,TEXT("FogRunD"));HostState->bInDungeonRoom=true;GuestState->bInDungeonRoom=true;
    Place(Host,A);Place(Guest,B);HostFog.Update(Host);GuestFog.Update(Guest);
    HostMarkers->Update(Host,HostFog,true);GuestMarkers->Update(Guest,GuestFog,true);
    Expect(!HostMarkers->Find(SharedMark.Id)&&!GuestMarkers->Find(SharedMark.Id),TEXT("new run inherited a retired shared pin"));
    SharedMark.Id.Invalidate();SharedMark.LayoutSerial=HostFog.LayoutSerial; // Replay an old run key with a new local ID.
    Expect(HostMarkers->Save(SharedMark),TEXT("stale share did not reach the authority validation path"));
    HostMarkers->Update(Host,HostFog,true);GuestMarkers->Update(Guest,GuestFog,true);
    const auto* Rejected=HostMarkers->Find(SharedMark.Id);
    Expect(Rejected&&Rejected->Visibility==EColdSteelMapMarkerVisibility::Personal&&!HostMarkers->ShareError().IsEmpty()&&
        HostSharing->Shared().IsEmpty()&&!GuestMarkers->Find(SharedMark.Id),TEXT("rejected stale share leaked or lost the private fallback"));

    HostMarkers.Reset();GuestMarkers.Reset();
    Room->Streaming=nullptr;Room->RoomState=nullptr;Room->LoadedInstance.Invalidate();
    World->WorldType=EWorldType::Editor;
    World->DestroyWorld(false);
    UE_LOG(LogTemp,Display,TEXT("DungeonFogLifecycle: %d checks, %d failures (simulated listen/client roles, no sockets)"),Checks,Failures);
    return Failures?4:0;
#else
    return 1;
#endif
}
