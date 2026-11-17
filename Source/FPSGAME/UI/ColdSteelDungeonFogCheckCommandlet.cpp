#include "ColdSteelDungeonFogCheckCommandlet.h"
#if WITH_EDITOR
#include "ColdSteelDungeonMap.h"
#include "../Dungeons/AuthoredDungeonGenerator.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Level.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshCompiler.h"
#include "Physics/Experimental/PhysScene_Chaos.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/Parse.h"
#endif

int32 UColdSteelDungeonFogCheckCommandlet::Main(const FString& Params)
{
#if WITH_EDITOR
    if (FParse::Param(*Params,TEXT("NetworkLifecycle"))) return CheckNetworkLifecycle();
    auto* Package=LoadPackage(nullptr,TEXT("/Game/GameMaps/L_Dungeon_Randomized"),LOAD_None);
    const auto* Map=Package?UWorld::FindWorldInPackage(Package):nullptr;
    const AAuthoredDungeonGenerator* Generator=nullptr;
    if (Map && Map->PersistentLevel) for (AActor* Actor : Map->PersistentLevel->Actors)
        if ((Generator=Cast<AAuthoredDungeonGenerator>(Actor))) break;
    TSharedPtr<FJsonObject> Catalog;
    if (!Generator || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Generator->ModuleCatalogJson),Catalog)) return 1;

    UWorld::InitializationValues Settings;
    Settings.AllowAudioPlayback(false).RequiresHitProxies(false).CreatePhysicsScene(true)
        .CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("DungeonFogCheck"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if (!World) return 2;
    ACharacter* Pawn=World->SpawnActor<ACharacter>();
    auto* Obstacle=World->SpawnActor<AActor>();
    if (!Pawn || !Obstacle) { World->DestroyWorld(false); return 3; }
    auto* Barrier=NewObject<UBoxComponent>(Obstacle);
    Obstacle->SetRootComponent(Barrier);
    Barrier->SetBoxExtent(FVector(3.,1000.,140.));
    Barrier->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Barrier->SetCollisionResponseToAllChannels(ECR_Ignore);
    Barrier->RegisterComponent();
    int32 Failures=0, Checks=0, Ramps=0;
    auto Expect=[&](bool Value,const FString& Name)
    {
        ++Checks;
        if (!Value) { ++Failures; UE_LOG(LogTemp,Error,TEXT("DungeonFogCheck: %s"),*Name); }
    };
    auto Footprint=[](FColdSteelDungeonMap& Fog,const FBox& Box,int32 Node,int32 Floor,double Z,bool Fallback)
    {
        return Fog.Footprints.Add({Box,Node,Floor,Z,false,Fallback,NAME_None});
    };
    auto Vec=[](const TArray<TSharedPtr<FJsonValue>>& XYZ)
    {
        return FVector(XYZ[0]->AsNumber(),XYZ[1]->AsNumber(),XYZ[2]->AsNumber());
    };
    for (const auto& ModuleValue : Catalog->GetArrayField(TEXT("modules")))
    {
        const auto Module=ModuleValue->AsObject();
        const FString Id=Module->GetStringField(TEXT("id"));
        bool bRamp=false;
        Module->TryGetBoolField(TEXT("split_level_ramp"),bRamp);
        if (Id!=TEXT("StairDrop1080") && !bRamp) continue;
        ++Ramps;
        TArray<FVector> Path;
        const FTransform Placement(FRotator(0,90,0),FVector(-16000,23000,5400));
        for (const auto& Point : Module->GetArrayField(TEXT("walk_polyline"))) Path.Add(Placement.TransformPosition(Vec(Point->AsArray())));
        if (Path.Num()<2) { Expect(false,Id+TEXT(" missing path")); continue; }
        FColdSteelDungeonMap Fog;
        const int32 Part=Footprint(Fog,FBox(ForceInit),3,0,0,true);
        auto& Ramp=Fog.Ramps.Add(3);
        const auto& Ports=Module->GetArrayField(TEXT("ports"));
        FVector Low=Placement.TransformPosition(Vec(Ports[0]->AsObject()->GetArrayField(TEXT("position"))));
        FVector High=Placement.TransformPosition(Vec(Ports[1]->AsObject()->GetArrayField(TEXT("position"))));
        if (Low.Z>High.Z) Swap(Low,High);
        Ramp.MiddleZ=(High.Z+Low.Z)*.5;
        Ramp.Lower=0;
        Ramp.Upper=FMath::RoundToInt((High.Z-Low.Z)/540.);
        Ramp.HalfWidth=150.;
        Ramp.SetPath(Path,Low,High);
        Expect(Ramp.Path.Num()==Path.Num(),Id+TEXT(" sockets and polyline disagree"));
        if (Ramp.Path.IsEmpty()) continue;
        const double Mid=Ramp.Distance.Last()*.5;
        for (int32 Dir : {1,-1})
        {
            int32 Changes=0, Previous=Dir==1?Ramp.Lower:Ramp.Upper;
            Fog.LastFootprint=INDEX_NONE;
            for (int32 Step=0; Step<=120; ++Step)
            {
                const double Along=Ramp.Distance.Last()*(Dir==1?Step:120-Step)/120.;
                int32 I=1;
                while (I+1<Ramp.Path.Num() && Ramp.Distance[I]<Along) ++I;
                FVector Point=FMath::Lerp(Ramp.Path[I-1],Ramp.Path[I],
                    (Along-Ramp.Distance[I-1])/(Ramp.Distance[I]-Ramp.Distance[I-1]));
                Point.Z+=(Step%2?2.3:-2.3);
                const int32 Floor=Fog.FloorFor(Part,Point,Barrier);
                if (Floor!=Previous) ++Changes;
                if (FMath::Abs(Along-Mid)>18.) Expect(Floor==(Along<Mid?Ramp.Lower:Ramp.Upper),Id+TEXT(" wrong flight"));
                Fog.LastFootprint=Part; Fog.PlayerFloor=Floor; Previous=Floor;
            }
            Expect(Changes==1,Id+TEXT(" switched floors more or less than once"));
        }
        UE_LOG(LogTemp,Display,TEXT("DungeonFogCheck: %s, both directions"),*Id);
    }
    Expect(Ramps>=4,TEXT("missing authored ramp variants"));

    // Two horizontal decks share XY and the lower mask extends through the upper one.
    FColdSteelDungeonMap Stack;
    const FBox Base(FVector(0,0,-5),FVector(1200,800,1000));
    int32 Ground=Footprint(Stack,Base,2,0,-5,false);
    int32 Upper=Footprint(Stack,FBox(FVector(0,0,475),FVector(1200,800,1000)),2,1,475,false);
    Stack.SpatialBins.Add({0,0},{Ground,Upper});
    Stack.RecordGround(*Pawn,{100,100,0},Barrier);
    Expect(Stack.IsKnown({100,100},0) && !Stack.IsKnown({100,100},1),TEXT("lower deck exposed upper"));
    Stack.RecordGround(*Pawn,{100,100,480},Barrier);
    Expect(Stack.PlayerFloor==1 && Stack.IsKnown({100,100},1),TEXT("upper deck at same XY unresolved"));
    Stack.RecordGround(*Pawn,{100,100,0},Barrier);
    Expect(Stack.PlayerFloor==0,TEXT("descending at same XY retained upper deck"));
    Stack.DeckAnchors.FindOrAdd(2).Add({FVector(1100,700,240),1});
    Expect(Stack.FloorFor(Ground,{100,100,240},Barrier)==0,TEXT("crate inherited distant deck height"));
    Expect(Stack.FloorFor(Ground,{100,100,240})==0,TEXT("distant anchor exposed a landmark on wrong deck"));
    auto* Deck=NewObject<UStaticMeshComponent>(Obstacle);
    for (const auto& Value : Catalog->GetArrayField(TEXT("modules")))
    {
        const auto Module=Value->AsObject();
        if (Module->GetStringField(TEXT("id"))!=TEXT("AccumulatorControl")) continue;
        for (const auto& V : Module->GetArrayField(TEXT("parts")))
        {
            const FString Path=V->AsObject()->GetStringField(TEXT("mesh"));
            if (!Path.Contains(TEXT("_GalleryDeck"))) continue;
            Deck->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,*Path));
            break;
        }
    }
    Expect(Deck->GetStaticMesh() && Stack.FloorFor(Ground,{100,100,384},Deck)==0 &&
        Stack.FloorFor(Ground,{100,100,240},Deck)==1,TEXT("authored support and elevation must both match"));
    // Place the installed gallery's outer edge in the middle of a fog tile. Use its
    // actual collision surface, including its baked mesh origin.
    if (Deck->GetStaticMesh())
    {
        TArray<UStaticMesh*> Meshes={Deck->GetStaticMesh()};
        FStaticMeshCompilingManager::Get().FinishCompilation(Meshes);
        Deck->SetMobility(EComponentMobility::Movable);
        Deck->SetCollisionProfileName(TEXT("BlockAll"));
        const FBox Bounds=Deck->GetStaticMesh()->GetBoundingBox();
        Deck->SetWorldLocation({100.-Bounds.Max.X,100.-Bounds.GetCenter().Y,240.-Bounds.Max.Z});
        Deck->RegisterComponent();
        World->GetPhysicsScene()->ProcessDeferredCreatePhysicsState();
        Deck->CreatePhysicsState(false);
        bool bExercised=false;
        int32 Hits=0, CorrectFloor=0;
        const FBox Placed=Bounds.ShiftBy(Deck->GetComponentLocation());
        for (double Y=Placed.Min.Y+40.; Y<Placed.Max.Y-40. && !bExercised; Y+=25.)
        {
            FHitResult Hit;
            if (!World->LineTraceSingleByChannel(Hit,{45,Y,270},{45,Y,190},ECC_Pawn,
                FCollisionQueryParams(SCENE_QUERY_STAT(FogCheckDeckSupport),false,Pawn)) || Hit.GetComponent()!=Deck) continue;
            ++Hits;
            FColdSteelDungeonMap Ledge;
            const FVector At=Hit.ImpactPoint;
            const FBox Room(FVector(-600,Y-600,-5),FVector(800,Y+600,1000));
            const int32 Part=Footprint(Ledge,Room,3,0,0,true);
            Ledge.SpatialBins.FindOrAdd({0,FMath::FloorToInt32(Y/1600.)}).Add(Part);
            Ledge.DeckAnchors.FindOrAdd(3).Add({At,1});
            Ledge.RecordGround(*Pawn,At,Deck);
            if (Ledge.PlayerFloor==1) ++CorrectFloor;
            if (!Ledge.IsKnown(FVector2D(At),1)) continue; // The first curved edge may be too narrow to chart.
            bExercised=true;
            Expect(!Ledge.IsKnown({145,Y},1),TEXT("upper deck geometry leaked over its edge"));
            Expect(!Ledge.IsKnown(FVector2D(At),0),TEXT("upper deck exploration exposed lower room"));
        }
        Expect(bExercised,FString::Printf(TEXT("installed gallery edge: %d hits, %d upstairs, bounds %s, physics %d"),Hits,CorrectFloor,*Placed.ToString(),Deck->IsPhysicsStateCreated()));
    }
    Deck->SetCollisionEnabled(ECollisionEnabled::NoCollision);

    for (const auto Channel : {ECC_Visibility,ECC_Pawn})
        for (double Yaw : {0.,30.,90.})
        {
            FColdSteelDungeonMap Fog;
            const FVector Center(100,100,0);
            const FQuat Rotation(FVector::UpVector,FMath::DegreesToRadians(Yaw));
            const FVector Normal=Rotation.GetAxisX();
            const FVector Near=Center-Normal*60., Far=Center+Normal*42.;
            const int32 Part=Footprint(Fog,FBox(FVector(-600,-600,-5),FVector(800,800,400)),1,0,-5,false);
            for (int32 X : {-1,0}) for (int32 Y : {-1,0}) Fog.SpatialBins.FindOrAdd({X,Y}).Add(Part);
            Barrier->SetWorldLocationAndRotation(Center+FVector(0,0,135),Rotation);
            Barrier->SetCollisionResponseToAllChannels(ECR_Ignore);
            Barrier->SetCollisionResponseToChannel(Channel,ECR_Block);
            Fog.RecordGround(*Pawn,Near,Barrier);
            Expect(Fog.IsKnown(FVector2D(Near),0),TEXT("near side of closed door missing"));
            Expect(!Fog.IsKnown(FVector2D(Far),0),TEXT("far side of closed door exposed"));
            for (const auto& Patch : Fog.Layers.FindChecked(0).Patches)
                for (double X : {Patch.Bounds.Min.X,Patch.Bounds.Max.X})
                    for (double Y : {Patch.Bounds.Min.Y,Patch.Bounds.Max.Y})
                        Expect(FVector::DotProduct(FVector(X,Y,0)-Center,Normal)<=0.,TEXT("closed door cuts a drawn patch"));
            Barrier->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            Fog.RetryBlockedAt=0.; // Same stationary retry as the map timer after the door opens.
            Fog.RecordGround(*Pawn,Near,Barrier);
            Expect(Fog.IsKnown(FVector2D(Far),0),TEXT("stationary player did not reveal opened doorway"));
            Barrier->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
            Fog.RecordGround(*Pawn,Far,Barrier);
            Expect(Fog.IsKnown(FVector2D(Near),0),TEXT("closing gate erased exploration"));
        }
    World->DestroyWorld(false);
    UE_LOG(LogTemp,Display,TEXT("DungeonFogCheck: %d checks, %d failures"),Checks,Failures);
    return Failures?4:0;
#else
    return 1;
#endif
}
