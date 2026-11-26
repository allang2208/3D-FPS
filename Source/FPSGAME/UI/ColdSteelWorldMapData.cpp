#include "ColdSteelWorldMapData.h"
#include "../WorldGeneration/ForestVillageMap.h"
#include "ColdSteelStatusModel.h"
#include "../Tasks/BlacksmithApprenticeship.h"
#include "../WorldGeneration/HillsBlacksmith.h"
#include "Engine/GameInstance.h"
#include "ColdSteelDungeonMap.h"
#include "ColdSteelHillsMap.h"
#include "Engine/TextureRenderTarget2D.h"
#include "ColdSteelHubMapRegistration.h"
#include "ColdSteelWarehouseChest.h"
#include "ColdSteelWorldInteraction.h"
#include "../Building/ColdSteelFountain.h"
#include "../Dungeons/DungeonRoomSubsystem.h"
#include "../Dungeons/DungeonRunSubsystem.h"
#include "../SceneTestPortal.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerStart.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Misc/Paths.h"
#include "NavMesh/NavMeshBoundsVolume.h"

namespace ColdSteelCartography
{
    constexpr int32 ForestResolution = ForestVillageMap::SideMeters/2;
    constexpr float Missing = -FLT_MAX;

    FString RegionTitle(const FString& Map)
    {
        if (Map==ForestVillageMap::Name) return TEXT("林道村庄");
        if (Map==TEXT("DayNight_Lighting")) return TEXT("主神空间");
        if (Map==TEXT("L_Dungeon_Randomized")) return TEXT("废弃设施");
        if (Map==TEXT("L_TemperateHills_Initial")) return TEXT("温带丘陵");
        if (Map==TEXT("L_MilitaryTrench_FPS_Test")) return TEXT("战壕");
        if (Map==TEXT("L_Normandy_FPS_Test")) return TEXT("诺曼底村庄");
        if (Map==TEXT("L_CyberpunkApartment")) return TEXT("公寓");
        return Map;
    }
}

void FColdSteelWorldMapData::Open(APawn* Viewer, FColdSteelMapSurfaceCache& Cache, FColdSteelDungeonMap& Discovery)
{
    using namespace ColdSteelCartography;
    *this=FColdSteelWorldMapData();
    UWorld* World=Viewer->GetWorld();
    const FVector Player=Viewer->GetActorLocation();
    const FString Map=UDungeonRoomSubsystem::LogicalMap(Viewer);
    RegionKey=Map;
    Title=RegionTitle(Map);
    bForestMap=Map==ForestVillageMap::Name;
    Bounds+=FVector2D(Player);
    bDungeon=Map==TEXT("L_Dungeon_Randomized");
    const bool bDiscoveryReady=Discovery.Update(Cast<APlayerController>(Viewer->GetController()));

    if (bDungeon)
    {
        auto* Run=UDungeonRunSubsystem::Get(World);
        if (!bDiscoveryReady || !Run || !Run->MapLevel())
        {
            bWaitingForDungeon=true;
            Bounds=Bounds.ExpandBy(2000.);
            return;
        }
        DungeonLevel=Run->MapLevel();
        Fog=&Discovery;
        RegionKey+=TEXT("/") + Run->RunId();
        const FVector Entry=Run->EntryPosition();
        Landmarks.Add({FVector2D(Entry),TEXT("入口"),0,nullptr,FString(),Entry.Z});
    }
    else
    {
        for (TActorIterator<ATemperateHillsWorld> It(World);It;++It)
        {
            Hills=*It;
            const double Half=It->SizeMeters*50.;
            Bounds=It->IsForestVillage()?ForestVillageMap::Bounds():FBox2D(FVector2D(-Half,-Half),FVector2D(Half,Half));
            RegionKey+=FString::Printf(TEXT("/%d/%s"),It->Seed,*It->WorldId.ToString());
            if(It->IsForestVillage())
            {
                bWaitingForForest=!It->bReady;
                ForestSeed=It->Seed;
                ForestWorldId=It->WorldId;
                if(bWaitingForForest) return;
            }
            const FVector Start=It->GetStartLocation();
            auto& Pin=Landmarks.Add_GetRef({FVector2D(Start),TEXT("出发点"),0});
            Pin.ActorZ=Start.Z;
            Pin.bTerrainStart=true;
            RefreshSmithDestination();
            break;
        }
    }

    if (bDungeon)
    {
        for (TActorIterator<ASceneTestPortal> It(World);It;++It) TrackLandmark(*It);
        return;
    }
    if(Map==ForestVillageMap::Name && !Hills.IsValid())
    {
        bWaitingForForest=true;
        Bounds=ForestVillageMap::Bounds();
        return;
    }
    for (TActorIterator<AActor> It(World);It;++It)
    {
        if (TrackLandmark(*It) && !Hills.IsValid()) Bounds+=FVector2D(It->GetActorLocation());
    }

    if (Map==TEXT("DayNight_Lighting"))
    {
        const FSoftObjectPath PhotoPath(UColdSteelHubMapRegistration::TexturePath);
        if (UseHubPhoto(Cast<UTexture2D>(PhotoPath.ResolveObject()),World)) return;
        HubPhotoRequest=UAssetManager::GetStreamableManager().RequestAsyncLoad(PhotoPath);
        if (HubPhotoRequest) return;
    }
    BeginSampledSurface(Viewer,Cache);
}

bool FColdSteelWorldMapData::MarkerGround(APawn* Viewer,FVector2D XY,int32 Floor,FVector& Position) const
{
    if (!Viewer || bWaitingForForest || bWaitingForDungeon || IsLoadingHubPhoto()) return false;
    if (bDungeon) return Fog && Fog->MarkerGround(*Viewer,XY,Floor,Position);
    if (!Bounds.IsInsideOrOn(XY)) return false;
    if (const auto* Terrain=Hills.Get())
    {
        Position=FVector(XY,Terrain->Height(XY.X,XY.Y));
        return true;
    }
    const FCollisionObjectQueryParams Objects(ECC_WorldStatic);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(MapMarkerGround),false,Viewer);
    FHitResult Hit;
    const double Top=FMath::Max(TraceTop,Viewer->GetActorLocation().Z+10000.);
    const double Bottom=FMath::Min(TraceBottom,Viewer->GetActorLocation().Z-15000.);
    if (!Viewer->GetWorld()->LineTraceSingleByObjectType(Hit,FVector(XY,Top),FVector(XY,Bottom),Objects,Query)) return false;
    Position=Hit.ImpactPoint;
    return true;
}

bool FColdSteelWorldMapData::TrackLandmark(AActor* Actor)
{
    if (bWaitingForDungeon || !IsValid(Actor)) return false;
    if (bDungeon && (Actor->GetLevel()!=DungeonLevel.Get() || !Actor->GetLevel()->bIsVisible)) return false;
    const auto* Portal=Cast<ASceneTestPortal>(Actor);
    FString Name,Destination;
    if (Portal)
    {
        Destination=Portal->DestinationMap();
        if (!Destination.IsEmpty()) Name=TEXT("通往")+ColdSteelCartography::RegionTitle(FPaths::GetCleanFilename(Destination));
    }
    else if (bDungeon) return false;
    else if (ColdSteelWorldInteraction::IsExpeditionAltar(Actor)) Name=TEXT("出征祭坛");
    else if (Actor->IsA<AColdSteelFountain>()) Name=TEXT("泉水");
    else if (auto* Chest=Cast<AColdSteelWarehouseChest>(Actor); Chest && Chest->GetStorageKey().IsEmpty()) Name=TEXT("仓库");
    else if (!Hills.IsValid() && Actor->IsA<APlayerStart>()) Name=TEXT("出生点");
    else return false;

    if (UDungeonRoomSubsystem::IsDungeonActor(Actor)!=bDungeon ||
        Landmarks.ContainsByPredicate([Actor](const auto& Mark){return Mark.Actor.Get()==Actor;})) return false;
    const FVector At=Actor->GetActorLocation();
    Landmarks.Add({FVector2D(At),MoveTemp(Name),Fog?Fog->LandmarkFloor(At):0,Actor,MoveTemp(Destination),At.Z});
    return true;
}

bool FColdSteelWorldMapData::RefreshSmithDestination()
{
    auto* Terrain=Hills.Get();
    if (!Terrain || !Terrain->GetGameInstance()) return false;
    auto* Model=Terrain->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Model) return false;
    const auto Stage=BlacksmithApprenticeship::Stage(Model->ProfileView());
    const bool Return=Stage==BlacksmithApprenticeship::EStage::ReturnOre;
    if (!Return && (Terrain->IsForestVillage() || !BlacksmithApprenticeship::IsMining(Stage)))
    {
        SmithRock=0;
        IronSearch.Next=0;
        RetrySmithLocationAt=0.;
        return Landmarks.RemoveAll([](const auto& Mark){return Mark.bSmithLesson;})>0;
    }
    auto* Pin=Landmarks.FindByPredicate([](const auto& Mark){return Mark.bSmithLesson;});
    if (Pin && Return==bSmithReturn && (Return || !Terrain->IsProductionDepleted(1,SmithRock))) return false;
    const double Now=Terrain->GetWorld()->GetRealTimeSeconds();
    if (Return==bSmithReturn && Now<RetrySmithLocationAt) return false;
    bSmithReturn=Return;
    const auto& Village=Terrain->GetVillageSite();
    if (!Village.bPlaced) return false;
    // Resolve the place of issue even when its streamed shop actor has unloaded.
    const FVector2D Smith=Village.World(-3200.,-900.);
    FVector Target(Smith,Terrain->Height(Smith.X,Smith.Y));
    for (TActorIterator<AHillsBlacksmith> It(Terrain->GetWorld());It;++It){Target=It->GetActorLocation();break;}
    if (!Return && !Terrain->FindNearestIronOutcrop(FVector2D(Target),IronSearch,Target,SmithRock))
    {
        RetrySmithLocationAt=Now+(IronSearch.Next==INDEX_NONE ? 30. : .2);
        if (IronSearch.Next==INDEX_NONE) IronSearch.Next=0;
        return Landmarks.RemoveAll([](const auto& Mark){return Mark.bSmithLesson;})>0;
    }
    // The task caption gets the first free label position among nearby landmarks.
    if (!Pin)
    {
        Landmarks.InsertDefaulted(0);
        Pin=&Landmarks[0];
    }
    Pin->Point=FVector2D(Target);
    Pin->ActorZ=Target.Z;
    Pin->Floor=0;
    Pin->Label=Return?TEXT("铁匠 · 交付铁矿石"):TEXT("露天铁矿脉 · 铁匠修炼");
    Pin->bSmithLesson=true;
    RetrySmithLocationAt=0.;
    return true;
}

bool FColdSteelWorldMapData::RefreshLandmarks()
{
    bool bChanged=RefreshSmithDestination();
    for (int32 I=Landmarks.Num()-1; I>=0; --I)
    {
        auto& Mark=Landmarks[I];
        if (Mark.Actor.IsExplicitlyNull()) continue; // Layout landmark with no backing actor.
        AActor* Actor=Mark.Actor.Get();
        if (!Actor || Actor->IsActorBeingDestroyed() ||
            (bDungeon && (Actor->GetLevel()!=DungeonLevel.Get() || !Actor->GetLevel()->bIsVisible)))
        {
            Landmarks.RemoveAt(I);
            bChanged=true;
            continue;
        }
        const FVector At=Actor->GetActorLocation();
        if (!At.Equals(FVector(Mark.Point,Mark.ActorZ),1.))
        {
            Mark.Point=FVector2D(At);
            Mark.ActorZ=At.Z;
            Mark.Floor=Fog?Fog->LandmarkFloor(At):0;
            bChanged=true;
        }
        if (const auto* Portal=Cast<ASceneTestPortal>(Actor); Portal && Mark.PortalDestination!=Portal->DestinationMap())
        {
            Mark.PortalDestination=Portal->DestinationMap();
            Mark.Label=Mark.PortalDestination.IsEmpty()?FString():TEXT("通往")+ColdSteelCartography::RegionTitle(FPaths::GetCleanFilename(Mark.PortalDestination));
            bChanged=true;
        }
    }
    return bChanged;
}

bool FColdSteelWorldMapData::RemoveLevelLandmarks(ULevel* Level)
{
    return Landmarks.RemoveAll([Level](const FColdSteelMapLandmark& Mark)
    {
        return Mark.Actor.IsValid() && Mark.Actor->GetLevel()==Level;
    })>0;
}

bool FColdSteelWorldMapData::UseHubPhoto(UTexture2D* Photo, const UWorld* World)
{
    if (!Photo) return false;
    const auto* Registration=Cast<UColdSteelHubMapRegistration>(
        Photo->GetAssetUserDataOfClass(UColdSteelHubMapRegistration::StaticClass()));
    if (!Registration || Registration->WidthCm<=0.) return false;
    const FVector2D Origin(World->OriginLocation.X,World->OriginLocation.Y);
    const FVector2D Center=Registration->CenterCm-Origin;
    const FVector2D Half(Registration->WidthCm*.5);
    Bounds=FBox2D(Center-Half,Center+Half);
    Surface.Reset(Photo);
    return true;
}

bool FColdSteelWorldMapData::FinishLoadingHubPhoto(APawn* Viewer, FColdSteelMapSurfaceCache& Cache)
{
    if (!HubPhotoRequest || !HubPhotoRequest->HasLoadCompleted()) return false;
    const bool bLoaded=UseHubPhoto(Cast<UTexture2D>(HubPhotoRequest->GetLoadedAsset()),Viewer->GetWorld());
    HubPhotoRequest.Reset();
    if (!bLoaded) BeginSampledSurface(Viewer,Cache);
    return true;
}

void FColdSteelWorldMapData::BeginSampledSurface(APawn* Viewer, FColdSteelMapSurfaceCache& Cache)
{
    using namespace ColdSteelCartography;
    UWorld* World=Viewer->GetWorld();
    const FVector Player=Viewer->GetActorLocation();
    const auto* Terrain=Hills.Get();
    bUsesSampledSurface=true;
    bStreamChanged=false;
    SampledTerrainRevision=Terrain?Terrain->GetMapSurfaceRevision():0;
    GridSize=Terrain && Terrain->IsForestVillage()?ForestResolution:192;
    NextShade=0;
    ForestPixels.Reset();
    Heights.Reset();
    HillsMap.Reset();
    bPreparingHills=false;
    bSurfaceUnavailable=false;
    SampledLevels.Reset();
    FBox2D RequiredBounds=Bounds;
    double RequiredTop=Player.Z, RequiredBottom=Player.Z;
    if (!Terrain || bForestMap)
        for (ULevel* Level:World->GetLevels())
            if (Level && Level->bIsVisible) SampledLevels.Add(Level);
    if (!Hills.IsValid())
    {
        Bounds=FBox2D(ForceInit);
        Bounds+=FVector2D(Player);
        for(const auto& Mark:Landmarks) Bounds+=Mark.Point;
        // Navigation volumes define the authored play area even on clients with no local Recast mesh.
        FBox PlayBounds(ForceInit);
        for (TActorIterator<ANavMeshBoundsVolume> It(World);It;++It)
        {
            if (!UDungeonRoomSubsystem::IsDungeonActor(*It))
                PlayBounds+=It->GetBounds().GetBox();
        }
        TraceTop=Player.Z+10000.;
        TraceBottom=Player.Z-15000.;
        if (PlayBounds.IsValid)
        {
            Bounds+=FVector2D(PlayBounds.Min);
            Bounds+=FVector2D(PlayBounds.Max);
            RequiredTop=FMath::Max(RequiredTop,PlayBounds.Max.Z);
            RequiredBottom=FMath::Min(RequiredBottom,PlayBounds.Min.Z);
            TraceTop=FMath::Max(TraceTop,PlayBounds.Max.Z+2000.);
            TraceBottom=FMath::Min(TraceBottom,PlayBounds.Min.Z-2000.);
        }
        RequiredBounds=Bounds;
        Bounds=Bounds.ExpandBy(PlayBounds.IsValid?500.:2500.);
        // Use a square sampling grid so ridges, roofs and roads use the same metre scale on both axes.
        const FVector2D Half(FMath::Max(1500.,Bounds.GetExtent().GetMax()));
        const FVector2D Center=Bounds.GetCenter();
        Bounds=FBox2D(Center-Half,Center+Half);
    }
    if (Cache.Surface.IsValid() && Cache.World.Get()==World && Cache.Region==RegionKey &&
        Cache.Terrain==Hills && Cache.TerrainRevision==SampledTerrainRevision && Cache.Origin==World->OriginLocation &&
        Cache.VisibleLevels==SampledLevels && Cache.Bounds.IsInsideOrOn(RequiredBounds.Min) && Cache.Bounds.IsInsideOrOn(RequiredBounds.Max) &&
        (Terrain || (Cache.TraceTop>=RequiredTop && Cache.TraceBottom<=RequiredBottom)))
    {
        Bounds=Cache.Bounds;
        Surface.Reset(Cache.Surface.Get());
        ReliefOverlay.Reset(Cache.ReliefOverlay.Get());
        return;
    }
    if (Terrain && !Terrain->IsForestVillage()) { bPreparingHills=true; return; }
    if (Terrain) { TraceTop=Player.Z+20000.; TraceBottom=Player.Z-20000.; }
    NextSample=0;
    Heights.Init(Missing,GridSize*GridSize);
    if(Terrain && Terrain->IsForestVillage()) ForestPixels.SetNumUninitialized(Heights.Num());
}

bool FColdSteelWorldMapData::ForestIdentityChanged(APawn* Viewer) const
{
    if(!bForestMap) return false;
    if(const auto* Terrain=Hills.Get())
        return (bWaitingForForest==Terrain->bReady ||
            Terrain->Seed!=ForestSeed || Terrain->WorldId!=ForestWorldId);
    if(bWaitingForForest)
        for(TActorIterator<ATemperateHillsWorld> It(Viewer->GetWorld());It;++It)
            if(It->IsForestVillage() && It->bReady) return true;
    return !bWaitingForForest;
}

bool FColdSteelWorldMapData::RefreshTerrainIfChanged(APawn* Viewer, FColdSteelMapSurfaceCache& Cache)
{
    const auto* Terrain=Hills.Get();
    const bool Changed=Terrain && Terrain->GetMapSurfaceRevision()!=SampledTerrainRevision;
    const bool StreamAffectsGround=bStreamChanged && (!Terrain || bForestMap);
    bStreamChanged=false;
    if(bWaitingForForest || (!Changed && !StreamAffectsGround)) return false;
    if(Terrain && Terrain->IsForestVillage())
    {
        if(auto* Start=Landmarks.FindByPredicate([](const auto& Mark){return Mark.bTerrainStart;}))
        {
            const FVector Position=Terrain->GetStartLocation();
            Start->Point=FVector2D(Position);
            Start->ActorZ=Position.Z;
        }
        Landmarks.RemoveAll([](const auto& Mark){return Mark.bSmithLesson;});
        RetrySmithLocationAt=0.;
        RefreshSmithDestination();
    }
    BeginSampledSurface(Viewer,Cache);
    return true;
}

void FColdSteelWorldMapData::SampleSurface(APawn* Viewer, FColdSteelMapSurfaceCache& Cache)
{
    using namespace ColdSteelCartography;
    if (!IsSampling()) return;
    const double Deadline=FPlatformTime::Seconds()+.0014;
    RefreshTerrainIfChanged(Viewer,Cache);
    if (bPreparingHills)
    {
        auto* Terrain=Hills.Get();
        if (!Terrain) { HillsMap.Reset(); bPreparingHills=false; bSurfaceUnavailable=true; return; }
        if (!Terrain->GetMapGroundMaterial()) return;
        if (!HillsMap)
        {
            HillsMap=MakeShared<FColdSteelHillsMap>(*Terrain);
            return;
        }
        if (!HillsMap->IsReady()) return;
        UTextureRenderTarget2D* Photo=nullptr;
        UTexture2D* Lines=nullptr;
        const bool Captured=HillsMap->Finish(*Terrain,Photo,Lines);
        HillsMap.Reset();
        bPreparingHills=false;
        if (!Captured) { bSurfaceUnavailable=true; return; }
        Surface.Reset(Photo);
        ReliefOverlay.Reset(Lines);
    }
    else
    {
        if (Heights.IsEmpty()) return;
        const FCollisionObjectQueryParams Objects(ECC_WorldStatic);
        const FCollisionQueryParams Query(SCENE_QUERY_STAT(ColdSteelAreaMap),false,Viewer);
        const FVector2D Size=Bounds.GetSize();
        const auto* Forest=ForestPixels.IsEmpty()?nullptr:Hills.Get();
        do
        {
            const int32 End=FMath::Min(NextSample+16,Heights.Num());
            for (;NextSample<End;++NextSample)
            {
                const double X=Bounds.Max.X-(NextSample/GridSize+.5)*Size.X/GridSize;
                const double Y=Bounds.Min.Y+(NextSample%GridSize+.5)*Size.Y/GridSize;
                if(Forest)
                {
                    const double Z=Forest->Height(X,Y);
                    Heights[NextSample]=Z;
                    ForestPixels[NextSample]=Forest->ForestMapLayers(X,Y,Z);
                    continue;
                }
                FHitResult Hit;
                if (Viewer->GetWorld()->LineTraceSingleByObjectType(Hit,{X,Y,TraceTop},{X,Y,TraceBottom},Objects,Query))
                    Heights[NextSample]=Hit.ImpactPoint.Z;
            }
        } while (NextSample<Heights.Num() && FPlatformTime::Seconds()<Deadline);
        if (NextSample!=Heights.Num()) return;
        if(Forest)
        {
            // Shade in slices as well, so opening a full-size village map has a bounded CPU cost.
            const double Step=Size.X/GridSize;
            do
            {
                const int32 End=FMath::Min(NextShade+128,Heights.Num());
                for(;NextShade<End;++NextShade)
                {
                    const int32 I=NextShade;
                    const float Z=Heights[I], W=(I%GridSize)?Heights[I-1]:Z, N=(I>=GridSize)?Heights[I-GridSize]:Z;
                    const float E=(I%GridSize+1<GridSize)?Heights[I+1]:Z, S=(I/GridSize+1<GridSize)?Heights[I+GridSize]:Z;
                    const float Dx=(E-W)*.5f,Dy=(S-N)*.5f;
                    // Band centres stay at five-metre elevations; line width is measured in sampled pixels.
                    const float Gradient=FMath::Sqrt(Dx*Dx+Dy*Dy);
                    const float LevelDistance=FMath::Abs(Z-500.f*FMath::RoundToFloat(Z/500.f));
                    const float Width=FMath::Clamp(.85f*Gradient,2.f,160.f);
                    const float Ink=(1.f-FMath::SmoothStep(.18f*Width,Width,LevelDistance))*FMath::SmoothStep(1.f,7.f,Gradient);
                    const double Light=FMath::Clamp((-Dy-Dx)/Step,-.85,.85)*34.-12.*Ink;
                    const auto Layers=ForestPixels[I];
                    const double Dirt=Layers.R/255.,Town=Layers.A/255.;
                    auto Channel=[&](double ForestColor,double LoessColor,double RoadColor)
                    {
                        const double Ground=FMath::Lerp(ForestColor,LoessColor,Town);
                        return uint8(FMath::Clamp(FMath::Lerp(Ground,RoadColor,Dirt)+Light,0.,255.));
                    };
                    ForestPixels[I]=Layers.B?FColor(151,139,126):Layers.G?FColor(55,106,124):
                        FColor(Channel(78,151,164),Channel(96,122,137),Channel(69,78,95));
                }
            } while(NextShade<Heights.Num() && FPlatformTime::Seconds()<Deadline);
            if(NextShade<Heights.Num()) return;
            Surface.Reset(UTexture2D::CreateTransient(GridSize,GridSize,PF_B8G8R8A8,NAME_None,
                TConstArrayView64<uint8>(reinterpret_cast<const uint8*>(ForestPixels.GetData()),ForestPixels.Num()*sizeof(FColor))));
            Heights.Empty();
            ForestPixels.Empty();
        }
        else FinishSurface();
    }
    Cache.World=Viewer->GetWorld();
    Cache.Origin=Viewer->GetWorld()->OriginLocation;
    Cache.Region=RegionKey;
    Cache.Terrain=Hills;
    Cache.TerrainRevision=SampledTerrainRevision;
    Cache.VisibleLevels=SampledLevels;
    Cache.Bounds=Bounds;
    Cache.TraceTop=TraceTop;
    Cache.TraceBottom=TraceBottom;
    Cache.Surface.Reset(Surface.Get());
    Cache.ReliefOverlay.Reset(ReliefOverlay.Get());
}

void FColdSteelWorldMapData::FinishSurface()
{
    using namespace ColdSteelCartography;
    TArray<FColor> Pixels;
    Pixels.SetNumUninitialized(Heights.Num());
    const int32 Resolution=GridSize;
    const double Step=Bounds.GetSize().X/Resolution;
    for (int32 I=0;I<Heights.Num();++I)
    {
        const float Z=Heights[I];
        if (Z==Missing) { Pixels[I]=FColor(23,25,26); continue; }
        float Left=I%Resolution?Heights[I-1]:Z, Up=I>=Resolution?Heights[I-Resolution]:Z;
        if (Left==Missing) Left=Z;
        if (Up==Missing) Up=Z;
        const int32 Band=FMath::FloorToInt(Z/500.f);
        const bool Contour=Band!=FMath::FloorToInt(Left/500.f) || Band!=FMath::FloorToInt(Up/500.f);
        const float Relief=FMath::Clamp(float((2.*Z-Left-Up)/Step),-1.f,1.f);
        const int32 Shade=FMath::Clamp(FMath::RoundToInt(66+Relief*28+(Contour?16:0)+FMath::Clamp(Band,-12,12)),32,126);
        Pixels[I]=FColor(Shade-2,Shade,Shade+2);
    }
    Surface.Reset(UTexture2D::CreateTransient(Resolution,Resolution,PF_B8G8R8A8,NAME_None,
        TConstArrayView64<uint8>(reinterpret_cast<const uint8*>(Pixels.GetData()),Pixels.Num()*sizeof(FColor))));
    Heights.Empty();
}
