#include "TemperateVillageCheckCommandlet.h"
#include "TemperateHillsWorld.h"
#include "TemperateVillagePerimeter.h"
#include "HighVillageDefense.h"
#include "HighVillageCollapse.h"
#include "VillageDefenseRepairTargets.h"
#include "VillageDefenseStairs.h"
#include "VillageDefenseState.h"
#include "HillsCarpenterWorkshop.h"
#include "VillageGunshopServices.h"
#include "../Building/VillageWallStairs.h"
#include "../Building/VoxelBuildPalette.h"
#include "../Building/VoxelBuildPersistence.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Monsters/PoisonMaggotMonster.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DamageEvents.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/DefaultPawn.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#if WITH_EDITOR
#include "StaticMeshCompiler.h"
#endif

// Invoked explicitly with -run=TemperateVillageCheck -DefenseBlocks -UserDir=<isolated directory>.
int32 UTemperateVillageCheckCommandlet::CheckDefenseBlocks(const FString& Params)
{
    FString UserDir;
    if(!FParse::Value(FCommandLine::Get(),TEXT("UserDir="),UserDir)||UserDir.IsEmpty())return 2;
    auto* Game=NewObject<UGameInstance>(GEngine);Game->AddToRoot();
    Game->InitializeStandalone(TEXT("VillageDefenseBlockCheck"));
    auto* World=Game->GetWorld();
    World->InitializeActorsForPlay(FURL());
    World->SetAllowDeferredPhysicsStateCreation(false);
    const auto Report=MakeShared<FJsonObject>();
    TArray<TSharedPtr<FJsonValue>> Checks;
    int32 Failures=0;
    auto Check=[&](bool bPass,const FString& Name)
    {
        auto Row=MakeShared<FJsonObject>();
        Row->SetStringField(TEXT("check"),Name);Row->SetBoolField(TEXT("pass"),bPass);
        Checks.Add(MakeShared<FJsonValueObject>(Row));
        if(!bPass)++Failures;
        UE_LOG(LogTemp,Display,TEXT("DEFENSE_BLOCKS %s %s"),bPass?TEXT("PASS"):TEXT("FAIL"),*Name);
        return bPass;
    };
    auto Run=[&]()
    {
        TArray<FSoftObjectPath> Assets;
        TemperateVillagePerimeter::AddMeshPaths(Assets);
        Assets.Emplace(TEXT("/Engine/BasicShapes/Cube.Cube"));
        bool bLoaded=true;
        TArray<UStaticMesh*> FixtureMeshes;
        for(const auto& Path:Assets)
        {
            UObject* Asset=Path.TryLoad();
            if(!Asset){bLoaded=false;UE_LOG(LogTemp,Warning,TEXT("Missing %s"),*Path.ToString());}
            if(auto* Mesh=Cast<UStaticMesh>(Asset))FixtureMeshes.Add(Mesh);
        }
#if WITH_EDITOR
        FStaticMeshCompilingManager::Get().FinishCompilation(FixtureMeshes);
#endif
        if(!Check(bLoaded,TEXT("Production perimeter and collapse assets load")))return;
        auto* Hills=World->SpawnActor<ATemperateHillsWorld>();
        Hills->WorldId=FGuid::NewGuid();
        Hills->VillageSite.bPlaced=true;Hills->VillageSite.bHilltop=true;
        // The fortified hilltop reserves a larger pad than the legacy streamed village.
        Hills->VillageSite.PadHalfX=7000.;Hills->VillageSite.PadHalfY=5500.;
        Hills->VillageSite.Ground=FVector(113.,-257.,42.75);
        Hills->VillageSite.Axis=FVector2D(.8,.6);
        Hills->bVillageWallRepaired=true;
        Hills->BuildVillagePerimeter();
        const int32 OrdinaryParts=Hills->VillageDefenseParts.Num();
        Report->SetNumberField(TEXT("repaired_perimeter_parts_including_gates"),OrdinaryParts);
        Hills->VillagePlansUnlocked=UTemperateHillsSave::HighWallPlan;
        Hills->BuildVillagePerimeter();
        auto FixedFlight=[Hills](int32 Id)->AVillageDefenseStairs*
        {
            for(AVillageDefenseSection* Part:Hills->VillageDefenseParts)
                if(Part->GetSectionId()==Id)return Cast<AVillageDefenseStairs>(Part);
            return nullptr;
        };
        {
            auto* West=FixedFlight(51000);
            auto* East=FixedFlight(51001);
            if(!Check(West && East,TEXT("Upgrading creates one fixed switchback per gatehouse")))return;
            const FTransform Original=West->GetActorTransform();
            West->TakeDamage(135.f,FDamageEvent(),nullptr,nullptr);
            const float Remaining=West->GetHealth();
            const FGuid PlayerId=FGuid::NewGuid();
            auto* Legacy=World->SpawnActorDeferred<AVillageDefenseStairs>(AVillageDefenseStairs::StaticClass(),
                Original,Hills,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
            Legacy->Initialize(Hills,63510,AVillageDefenseStairs::StairMeshPath(),1200.f,PlayerId);
            Legacy->FinishSpawning(Original);
            Legacy->TakeDamage(210.f,FDamageEvent(),nullptr,nullptr);
            auto AtAlternate=[&]()
            {
                auto* Fixed=FixedFlight(51000);
                return Fixed && !Fixed->GetActorTransform().Equals(Original,.01) && Fixed->GetHealth()==Remaining &&
                    Legacy->GetHealth()==990.f && Legacy->GetActorTransform().Equals(Original,.01);
            };
            Check(AtAlternate(),TEXT("A legacy player stair arriving after the perimeter keeps its site and independent health"));
            Hills->BuildVillagePerimeter();
            Check(AtAlternate(),TEXT("Rebuilding after the player stair selects the same alternate pier and restores both health records"));
            Legacy->Destroy();
            West=FixedFlight(51000);
            Check(West && West->GetActorTransform().Equals(Original,.01) && West->GetHealth()==Remaining,
                TEXT("Removing the legacy player stair releases its pier without healing the fixed section"));
        }
        TArray<AHighVillageWall*> Walls;
        TArray<AHighVillageGate*> Gates;
        TSet<int32> Ids;
        double MaxSpan=0.;
        for(AVillageDefenseSection* Part:Hills->VillageDefenseParts)
        {
            Ids.Add(Part->GetSectionId());
            if(auto* Wall=Cast<AHighVillageWall>(Part))
            {Walls.Add(Wall);MaxSpan=FMath::Max(MaxSpan,300.*Wall->GetActorScale3D().X);}
            if(auto* Gate=Cast<AHighVillageGate>(Part))Gates.Add(Gate);
        }
        Report->SetNumberField(TEXT("high_wall_independent_bays"),Walls.Num());
        Report->SetNumberField(TEXT("high_gates"),Gates.Num());
        Report->SetNumberField(TEXT("longest_bay_cm"),MaxSpan);
        if(!Check(OrdinaryParts>100&&Walls.Num()>100&&Gates.Num()==2&&Ids.Num()==Hills->VillageDefenseParts.Num()&&MaxSpan<305.,
            TEXT("Repaired and fortified perimeters use individually addressed bays and gates")))return;
        for(auto* Gate:Gates)
        {
            const bool bWest=Gate->GetSectionId()==50000;
            auto* Flight=FixedFlight(bWest?51000:51001);
            if(!Check(Flight!=nullptr,TEXT("Generated gate retains its own stair section")))return;
            const FTransform& Pose=Flight->GetActorTransform();
            const FVector Join=Pose.TransformPosition(FVector(160.,-200.,360.));
            const FVector Across=Pose.GetUnitAxis(EAxis::X);
            auto Surface=[&](const FVector& At,const AActor* Expected)
            {
                FHitResult Hit;
                return World->LineTraceSingleByChannel(Hit,At+FVector(0,0,12.),At-FVector(0,0,12.),
                    ECC_Pawn,FCollisionQueryParams(SCENE_QUERY_STAT(FixedStairLanding),false)) &&
                    Hit.GetActor()==Expected && FMath::Abs(Hit.ImpactPoint.Z-Join.Z)<.5;
            };
            const FVector Foot=Gate->GetActorTransform().InverseTransformPosition(Pose.TransformPosition(FVector(-80.,-120.,0.)));
            Check(Foot.Y>400. && Foot.X>(bWest?430.:330.) && VillageWallStairs::HasClearStairEntrance(*World,Pose) &&
                Surface(Join-Across*4.,Flight) && Surface(Join+Across*4.,Gate),
                FString::Printf(TEXT("Gate %d has a courtyard approach and level collision across the gallery seam"),Gate->GetSectionId()));
        }
        const FVector2D Mid=Hills->VillageSite.World(0.,-Hills->VillageSite.WallHalfSize().Y);
        Walls.Sort([&](const auto& A,const auto& B){return FVector2D::DistSquared(FVector2D(A.GetActorLocation()),Mid)
            <FVector2D::DistSquared(FVector2D(B.GetActorLocation()),Mid);});
        auto* Bay=Walls[0];
        auto* Masonry=Bay->GetMasonry();
        Report->SetBoolField(TEXT("physics_scene"),World->GetPhysicsScene()!=nullptr);
        Report->SetBoolField(TEXT("bay_registered"),Masonry->IsRegistered());
        Report->SetBoolField(TEXT("bay_physics"),Masonry->IsPhysicsStateCreated());
        Report->SetNumberField(TEXT("bay_object_channel"),int32(Masonry->GetCollisionObjectType()));
        FTransform Dock;
        FIntVector Anchor;
        int32 Turns=0;
        if(!Check(VillageWallStairs::MakeDock(*Bay,Dock,Anchor,Turns),TEXT("Rotated wall offers a stair dock")))return;
        FTransform FoundDock;
        Check(VillageWallStairs::FindDock(World,Anchor,Turns,FoundDock)==Bay&&FoundDock.Equals(Dock,.01),
            TEXT("Grid address resolves to the same wall and exact pose"));
        // A patch of level ground provides the actual blocking surface required by player placement.
        auto* Ground=World->SpawnActor<AStaticMeshActor>();
        Ground->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
        Ground->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
        Ground->SetActorTransform(FTransform(FQuat::Identity,Dock.GetLocation()-FVector(0,0,50.),FVector(35.,35.,1.)));
        auto* Build=World->SpawnActor<AVoxelBuildWorld>();
        const FString Key=TEXT("DefenseBlocks-")+Hills->WorldId.ToString();
        if(!Check(Build->DebugInitialize(Key),TEXT("Load the live building palette")))return;
        {
            auto* OpenShop=World->SpawnActor<AVillageGunshopWorkbench>();
            auto* RuinedShop=World->SpawnActor<AHillsCarpenterWorkshop>();
            if(!Check(OpenShop&&RuinedShop,TEXT("Spawn authored workshop snapshot fixtures")))return;
            const FIntVector OpenCell(700,30,3),RuinedCell(710,30,3);
            OpenShop->SetOwner(Build);
            OpenShop->Configure(VoxelGunWorkbenchId,OpenCell,0,nullptr,nullptr,nullptr);
            Build->RegisterSceneStation(OpenShop);
            RuinedShop->SetOwner(Build);
            RuinedShop->Configure(NAME_None,RuinedCell,0,nullptr,nullptr,nullptr);
            TArray<uint8> Snapshot;
            if(!Check(Build->PrefabActorAt(OpenCell)==OpenShop&&!Build->HasPrefabAt(RuinedCell)
                &&Build->MakeNetworkSnapshot(Snapshot)&&Build->ApplyNetworkSnapshot(Snapshot)&&Build->ApplyNetworkSnapshot(Snapshot),
                TEXT("Apply two authority inventory rollbacks while village workshops are present")))return;
            if(!Check(!Build->RemovePrefab(OpenShop)&&IsValid(OpenShop)&&IsValid(RuinedShop)&&Build->PrefabActorAt(OpenCell)==OpenShop
                &&Build->PrefabActorAt(RuinedCell)==nullptr&&Build->PrefabCount()==0,
                TEXT("Rollbacks retain active and ruined workshop actors without creating construction records")))return;
            OpenShop->Destroy();
            RuinedShop->Destroy();
        }
        FString Reason;
        Check(!Build->CanPlacePrefab(VillageWallStairs::Id,Anchor,Turns,Reason,false,true),
            TEXT("Locked village construction denies placement"));
        Hills->Slot=TEXT("VillagePlanParity_")+Hills->WorldId.ToString(EGuidFormats::Digits);
        auto* PlanSave=NewObject<UTemperateHillsSave>();
        PlanSave->WorldId=Hills->WorldId;PlanSave->Seed=Hills->Seed;
        PlanSave->Version=6;PlanSave->VillagePlanVersion=7;
        PlanSave->bVillageWallRepaired=true;PlanSave->VillagePlansUnlocked=Hills->VillagePlansUnlocked;
        FText PlanFailure;
        if(!Check(UGameplayStatics::SaveGameToSlot(PlanSave,Hills->Slot,0)
            &&Hills->UnlockVillagePlan(TEXT("village_construction"),PlanFailure),
            TEXT("Nun construction unlock commits on an existing fortified v7 village save")))return;
        const auto* Unlocked=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(Hills->Slot,0));
        Check(Unlocked&&(Unlocked->SavedVillagePlans()&UTemperateHillsSave::ConstructionPlan)
            &&(Unlocked->SavedVillagePlans()&UTemperateHillsSave::HighWallPlan),
            TEXT("Loading the village plan keeps both the existing high wall and the new recipes"));
        auto CheckVillageReset=[&]()
        {
            const FGuid OldGeneration=Hills->VillageDefenseGeneration;
            const bool bReset=Hills->ResetVillageUpgrades(PlanFailure);
            const auto* Reset=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(Hills->Slot,0));
            Check(bReset&&Reset&&Reset->SavedVillagePlans()==0&&!Reset->bVillageWallRepaired
                &&Reset->VillageDefenseGeneration.IsValid()&&Reset->VillageDefenseGeneration!=OldGeneration
                &&!Hills->IsVillagePlanUnlocked(TEXT("village_construction"))&&!Hills->HasVillageHighWall()
                &&!FixedFlight(51000)&&!FixedFlight(51001),
                TEXT("F6 resets the repaired perimeter, locked recipes and damage generation on disk"));
            FString LockedReason;
            Check(!Build->CanPlacePrefab(VillageWallStairs::Id,Anchor,Turns,LockedReason,false,false)
                &&LockedReason.Contains(TEXT("修女")),TEXT("World placement enforces the reset until the construction plan is unlocked again"));
        };
        {
            // Reproduce late resolution of a prefab carrier after the broken health was published.
            auto* Carrier=World->SpawnActor<AVoxelBuildPrefabActor>(FVector(52000.,52000.,600.),FRotator::ZeroRotator);
            auto* Viewer=World->SpawnActor<ADefaultPawn>(FVector(54000.,54000.,600.),FRotator::ZeroRotator);
            auto* Wall=World->SpawnActorDeferred<AHighVillageWall>(AHighVillageWall::StaticClass(),
                Carrier->GetActorTransform(),Hills,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
            Wall->InitializeHighWall(Hills,63003,FGuid::NewGuid());
            Wall->FinishSpawning(Carrier->GetActorTransform());
            Wall->AttachToActor(Carrier,FAttachmentTransformRules::KeepWorldTransform);
            Carrier->AttachLogicActor(Wall);
            Wall->TakeDamage(Wall->GetMaximumHealth(),FDamageEvent(),nullptr,nullptr);
            auto* Targets=World->GetSubsystem<UVillageDefenseRepairTargets>();
            auto TraceWall=[&](const FTransform& Pose,AVillageDefenseSection** Nearby=nullptr)
            {
                return Targets->Trace(*Viewer,Pose.TransformPosition(FVector(0,215,90)),Pose.TransformPosition(FVector(0,0,90)),Nearby);
            };
            const FTransform Initial=Carrier->GetActorTransform();
            Check(TraceWall(Initial)==Wall,TEXT("Broken placed wall registers its repair surface"));
            Carrier->SetActorLocationAndRotation(Initial.GetLocation()+FVector(1700.,280.,0.),FRotator(0.,37.,0.));
            AVillageDefenseSection* Nearby=nullptr;
            Check(TraceWall(Initial,&Nearby)==nullptr&&!Nearby&&TraceWall(Carrier->GetActorTransform())==Wall,
                TEXT("Moving the broken wall carrier updates repair reach and clears the old preview"));
            Wall->Tags.AddUnique(TEXT("VoxelDetached"));
            Check(TraceWall(Carrier->GetActorTransform(),&Nearby)==nullptr&&!Nearby,
                TEXT("Detached falling wall cannot present a repair interaction"));
            Wall->Destroy();Carrier->Destroy();Viewer->Destroy();
        }
        {
            const FTransform Pose(FVector(58000.,58000.,600.));
            auto* Gate=World->SpawnActorDeferred<AVillageDefenseGate>(AVillageDefenseGate::StaticClass(),Pose,Hills,
                nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
            Gate->InitializeGate(Hills,63004,false);
            Gate->FinishSpawning(Pose);
            Gate->ToggleDoor();Gate->Tick(.2f);
            const float OpeningAngle=Gate->GetGateAngle();
            Gate->ToggleDoor();Gate->Tick(.1f);
            Check(OpeningAngle>0.f&&Gate->GetGateAngle()<OpeningAngle,
                TEXT("Using a timber gate twice reverses it during the first half of opening"));
            Gate->Tick(1.f);
            Gate->ToggleDoor();Gate->Tick(.6f);
            const float BeforeObstruction=Gate->GetGateAngle();
            const FVector AtStop=Pose.TransformPosition(FVector(-AVillageDefenseGate::NarrowHingeOffset,0.,0.)+
                FRotator(0.,BeforeObstruction+21.,0.).RotateVector(FVector(250.,5.5,115.)));
            auto* Occupant=World->SpawnActor<ADefaultPawn>(AtStop,FRotator::ZeroRotator);
            Gate->Tick(.5f);
            const bool bStopped=FMath::IsNearlyEqual(Gate->GetGateAngle(),BeforeObstruction)&&!Gate->IsActorTickEnabled();
            Gate->ToggleDoor();Gate->Tick(.1f);
            Check(bStopped&&Gate->GetGateAngle()<BeforeObstruction,TEXT("A blocked timber gate can back away from its occupant"));
            Occupant->Destroy();Gate->Destroy();
        }
        const bool bPlacementOnly=FParse::Param(*Params,TEXT("PlacementOnly"));
        if(bPlacementOnly||FParse::Param(*Params,TEXT("BuildParity")))
        {
            ExerciseDefensePlacement(*Build,*Hills,*Bay,Check);
            ExerciseDefenseUndo(*Build,Check);
            if(bPlacementOnly){CheckVillageReset();return;}
        }
        if(!Check(Build->PlacePrefab(VillageWallStairs::Id,Anchor,Turns,true),
            TEXT("Place stairs through the player build-world entry")))
        {Report->SetStringField(TEXT("placement_reason"),Build->ResultMessage());return;}
        auto* Prefab=Build->PrefabActorAt(Anchor);
        auto* Stair=Prefab?Cast<AVillageDefenseSection>(Prefab->Logic()):nullptr;
        if(!Check(Stair&&Stair->GetMasonry()->GetStaticMesh()&&Stair->GetActorTransform().Equals(Dock,.02),
            TEXT("Placed stairs have a damageable body at the preview pose")))return;
        const FVector Edge=Dock.TransformPosition(FVector(80.,-280.,360.));
        const FVector WallEdge=Bay->GetActorTransform().TransformPosition(FVector(0,100.,360.));
        Report->SetNumberField(TEXT("dock_edge_distance_cm"),FVector::Distance(Edge,WallEdge));
        TArray<TSharedPtr<FJsonValue>> FloorSamples;
        auto FloorAt=[&](double Offset,AActor* Expected)
        {
            const FVector Point=Edge+Dock.GetUnitAxis(EAxis::Y)*Offset;
            FHitResult Hit;
            // CharacterMovement walks on simple collision. A complex visibility
            // trace instead measures the bevel and chipped face of the top stone.
            const bool bHit=World->LineTraceSingleByChannel(Hit,Point+FVector(0,0,35.),Point-FVector(0,0,35.),ECC_Pawn,
                FCollisionQueryParams(SCENE_QUERY_STAT(VillageWalkSurface),false));
            auto Row=MakeShared<FJsonObject>();Row->SetNumberField(TEXT("offset_cm"),Offset);
            Row->SetStringField(TEXT("expected"),GetNameSafe(Expected));Row->SetStringField(TEXT("hit"),GetNameSafe(Hit.GetActor()));
            if(bHit)Row->SetNumberField(TEXT("z_error_cm"),Hit.ImpactPoint.Z-Edge.Z);
            FloorSamples.Add(MakeShared<FJsonValueObject>(Row));Report->SetArrayField(TEXT("seam_samples"),FloorSamples);
            return bHit&&Hit.GetActor()==Expected&&FMath::Abs(Hit.ImpactPoint.Z-Edge.Z)<.5;
        };
        const bool bWallFloor=FloorAt(-3.,Bay),bStairFloor=FloorAt(3.,Stair);
        Check(Edge.Equals(WallEdge,.02)&&bWallFloor&&bStairFloor,TEXT("Collision on both sides of the stair to wall seam is level"));
        FCollisionQueryParams WalkQuery(SCENE_QUERY_STAT(VillageStairWalk),false);
        bool bFlights=true;
        for(int32 Step=0;Step<10;++Step)for(int32 Lane=0;Lane<2;++Lane)
        {
            const double Z=Lane?360.-18.*Step:18.*(Step+1);
            const FVector Target=Dock.TransformPosition(FVector(Lane?80.:-80.,-106.+28.*Step,Z));
            FHitResult Tread;
            bFlights&=World->LineTraceSingleByChannel(Tread,Target+FVector(0,0,10.),Target-FVector(0,0,10.),ECC_Pawn,WalkQuery)
                &&Tread.GetActor()==Stair&&FMath::Abs(Tread.ImpactPoint.Z-Target.Z)<.5&&Tread.ImpactNormal.Z>.99;
        }
        const FVector Across=Dock.GetUnitAxis(EAxis::Y),CapsuleAt=Edge+FVector(0,0,89.);
        Check(bFlights&&!World->SweepTestByChannel(CapsuleAt+Across*80.,CapsuleAt-Across*55.,FQuat::Identity,
            ECC_Pawn,FCollisionShape::MakeCapsule(34.f,88.f),WalkQuery),TEXT("All twenty treads match their rises and the player-sized capsule crosses the top seam"));
        const FVector FreeBase=Dock.TransformPosition(FVector(0.,910.,0.));
        const FIntVector FreeCell=AVoxelBuildWorld::ToCell(FreeBase)-FIntVector(8,14,0);
        const bool bFree=Build->PlacePrefab(VillageWallStairs::Id,FreeCell,0,false);
        auto* FreePrefab=bFree?Build->PrefabActorAt(FreeCell):nullptr;
        auto* FreeStair=FreePrefab?Cast<AVillageDefenseSection>(FreePrefab->Logic()):nullptr;
        Check(FreeStair&&FreeStair->GetMasonry()->GetStaticMesh()&&Build->RemovePrefab(FreePrefab),
            TEXT("A freestanding stair can be placed on ground and dismantled"));
        const FGuid StairId=Build->PrefabInstanceIdentity(Anchor);
        const float BayHp=Bay->GetMaximumHealth();
        const FDamageEvent Damage;
        TArray<uint8> Saved;
        Check(Build->MakeNetworkSnapshot(Saved),TEXT("Placed stairs can be serialized"));
        const auto* Decoded=VoxelPersistence::Decode(Saved);
        const auto* SavedStair=Decoded?Decoded->Prefabs.FindByPredicate([&](const auto& P){return P.InstanceId==StairId;}):nullptr;
        Check(SavedStair&&SavedStair->WallDockPose.IsSet()&&SavedStair->WallDockPose->Equals(Dock,.02),
            TEXT("Snapshot retains the stair identity and the exact off-grid pose"));
        auto EffectOf=[&](AActor* Target)->AHighVillageCollapse*
        {
            for(TActorIterator<AHighVillageCollapse> It(World);It;++It)if(It->GetOwner()==Target)return *It;
            return nullptr;
        };
        auto Break=[&](AVillageDefenseSection* Section,const TCHAR* Label,int32 ExpectedParts)
        {
            const float HP=Section->GetMaximumHealth();
            Section->TakeDamage(HP*.25f,Damage,nullptr,nullptr);
            Check(Section->GetHealth()==HP*.75f&&!EffectOf(Section),FString(Label)+TEXT(" partial damage"));
            Section->TakeDamage(HP,Damage,nullptr,nullptr);
            Check(!Section->BlocksPassage()&&!Section->GetMasonry()->IsVisible()
                &&Section->GetMasonry()->GetCollisionEnabled()==ECollisionEnabled::NoCollision,FString(Label)+TEXT(" opens only its own breach"));
            auto* Effect=EffectOf(Section);
            if(!Check(Effect!=nullptr,FString(Label)+TEXT(" authoritative damage dispatches collapse")))return;
            TInlineComponentArray<UStaticMeshComponent*> Parts(Effect);
            const int32 Count=Parts.Num();
            int32 WithMeshes=0;for(auto* Part:Parts)WithMeshes+=Part->GetStaticMesh()!=nullptr;
            Check(WithMeshes==Count&&(ExpectedParts>0?Count==ExpectedParts:Count>1),FString(Label)+TEXT(" authored debris meshes"));
            Report->SetNumberField(FString(Label)+TEXT("_pieces"),Count);
            auto Moving=[&](){int32 N=0;for(auto* Part:Parts)N+=Part->IsSimulatingPhysics();return N;};
            const int32 Before=Moving();
            Effect->Tick(.14f);const int32 First=Moving();
            Effect->Tick(1.15f);const int32 After=Moving();
            Check(Before==0&&First<After&&After==Count,FString(Label)+TEXT(" staged rigid-body release"));
            Effect->Tick(6.f);
            Check(Moving()==0,FString(Label)+TEXT(" debris physics stops after settling"));
            Section->TakeDamage(HP,Damage,nullptr,nullptr);
            int32 Active=0;for(TActorIterator<AHighVillageCollapse> It(World);It;++It)Active+=It->GetOwner()==Section;
            Check(Active==1,FString(Label)+TEXT(" repeated damage does not replay collapse"));
        };
        Break(Stair,TEXT("stairs"),18);
        Check(Bay->GetHealth()==BayHp&&FloorAt(-3.,Bay)&&!FloorAt(3.,Stair),TEXT("Stair destruction leaves the wall walk intact and removes stair collision"));
        auto* Payer=World->SpawnActor<ADefaultPawn>(FVector(0.,0.,1300.),FRotator::ZeroRotator);
        const FVector Eye=Dock.TransformPosition(FVector(260.,-190.,145.));
        auto* Repair=World->GetSubsystem<UVillageDefenseRepairTargets>();
        Check(Payer&&Repair->Trace(*Payer,Eye,Dock.TransformPosition(FVector(20.,-190.,145.)),nullptr)==Stair,
            TEXT("Destroyed stairs can be targeted at their upper platform for repair"));
        const int32 BayId=Bay->GetSectionId();
        Break(Bay,TEXT("high_wall"),9);
        bool bNeighboursIntact=true;
        for(const auto* Wall:Walls)if(Wall!=Bay)bNeighboursIntact&=Wall->GetHealth()==Wall->GetMaximumHealth()&&Wall->BlocksPassage();
        Check(bNeighboursIntact&&Gates[0]->BlocksPassage()&&Gates[1]->BlocksPassage(),TEXT("Every other bay and both gates keep their health and collision"));
        Check(!VillageWallStairs::MakeDock(*Bay,FoundDock,Anchor,Turns),TEXT("Destroyed high wall rejects docking"));
        for(auto* Gate:Gates)
        {
            Gate->ToggleDoor();Gate->Tick(1.f);
            const double Lift=Gate->GetMasonry()->GetRelativeLocation().Z;
            Gate->TakeDamage(Gate->GetMaximumHealth(),Damage,nullptr,nullptr);
            auto* Effect=EffectOf(Gate);UStaticMeshComponent* Grille=nullptr;
            if(Effect)
            {
                TInlineComponentArray<UStaticMeshComponent*> Parts(Effect);
                for(auto* Part:Parts)if(Part->GetStaticMesh()==Gate->GetMasonry()->GetStaticMesh())Grille=Part;
            }
            const bool bRaised=Grille&&Lift>1.&&FMath::IsNearlyEqual(Grille->GetRelativeLocation().Z,Lift,.1);
            if(Effect)Effect->Tick(1.8f);
            Check(bRaised&&Grille->GetRelativeLocation().Z<Lift&&Grille->GetRelativeRotation().Quaternion().GetAngle()>1.
                &&Gate->GetStonePortal()->IsVisible()&&Gate->GetStonePortal()->IsCollisionEnabled(),
                FString::Printf(TEXT("Gate %d falls from its current lift while stone arch remains"),Gate->GetSectionId()));
        }
        auto* State=World->GetSubsystem<UVillageDefenseState>();State->Flush();
        const auto* Disk=Cast<UVillageDefenseSave>(UGameplayStatics::LoadGameFromSlot(TEXT("VillageDefenses_")+Hills->WorldId.ToString(EGuidFormats::Digits),0));
        Check(Disk&&Disk->DamagedSections.Contains(BayId)&&Disk->DamagedSections.FindRef(BayId)==0.f
            &&Disk->DamagedPlacedSections.Contains(StairId)&&Disk->DamagedPlacedSections.FindRef(StairId)==0.f,
            TEXT("Independent wall and player-built stair breaches persist to the isolated save"));
        Hills->BuildVillagePerimeter();
        int32 Broken=0;int32 RestoredId=INDEX_NONE;
        for(AVillageDefenseSection* Part:Hills->VillageDefenseParts)
            if(Part->IsA<AHighVillageWall>()&&!Part->BlocksPassage()){++Broken;RestoredId=Part->GetSectionId();}
        Check(Broken==1&&RestoredId==BayId,TEXT("Rebuilding the perimeter restores exactly the one broken bay"));
        FVoxelDiskSnapshot Empty;Empty.WorldKey=Key;TArray<uint8> EmptyBytes;
        const bool bReload=VoxelPersistence::Encode(MoveTemp(Empty),EmptyBytes)
            &&Build->ApplyNetworkSnapshot(EmptyBytes)&&Build->ApplyNetworkSnapshot(Saved);
        auto* ReloadedPrefab=bReload?Build->PrefabActorAt(SavedStair?SavedStair->Cell:Anchor):nullptr;
        Stair=ReloadedPrefab?Cast<AVillageDefenseSection>(ReloadedPrefab->Logic()):nullptr;
        if(!Check(Stair&&Stair->GetHealth()==0.f&&Stair->GetActorTransform().Equals(Dock,.02)&&!FloorAt(3.,Stair),
            TEXT("Loading the placed prefab restores the same broken stair, without invisible collision")))return;
        auto* Model=Game->GetSubsystem<UColdSteelStatusModel>();
        auto* Controller=World->SpawnActor<APlayerController>();
        if(!Check(Controller&&Payer&&Model&&Model->GrantSouls(Stair->GetRepairSoulCost()*2),TEXT("Prepare the isolated repair payer")))return;
        auto* PlayerState=World->SpawnActor<APlayerState>();
        PlayerState->SetOwner(Controller);Controller->SetPlayerState(PlayerState);
        Controller->SetAsLocalPlayerController();Controller->Possess(Payer);Payer->SetPlayerState(PlayerState);
        Payer->SetActorLocation(Eye);
        FText Failure;
        {
            const FTransform EnemyPose(Dock.TransformPosition(FVector(700.,0.,90.)));
            auto* EnemyClass=LoadClass<APoisonMaggotMonster>(nullptr,TEXT("/Game/Monsters/PoisonMaggot/BP_PoisonMaggot.BP_PoisonMaggot_C"));
            if(!Check(EnemyClass!=nullptr,TEXT("Repair enemy uses its configured monster blueprint")))return;
            auto* Enemy=World->SpawnActorDeferred<APoisonMaggotMonster>(EnemyClass,
                EnemyPose,nullptr,nullptr,ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
            Enemy->AutoPossessAI=EAutoPossessAI::Disabled;
            Enemy->FinishSpawning(EnemyPose);
            if(!Enemy->HasActorBegunPlay())Enemy->DispatchBeginPlay();
            const int64 Balance=Model->SoulBalance();
            Check(Stair->HasNearbyRepairEnemy(Payer)&&!Stair->TryRepair(Payer,Failure)&&Failure.ToString().Contains(TEXT("敌方"))
                &&Stair->GetHealth()==0.f&&Model->SoulBalance()==Balance,
                TEXT("A live hostile near the breach blocks its repair without spending souls"));
            Enemy->Destroy();
        }
        auto Repaired=[&]()
        {
            const int64 Before=Model->SoulBalance();
            const bool bPaid=Stair->TryRepair(Payer,Failure);
            if(!bPaid)Report->SetStringField(TEXT("repair_reason"),Failure.ToString());
            return bPaid&&Model->SoulBalance()==Before-Stair->GetRepairSoulCost()&&Stair->GetHealth()==Stair->GetMaximumHealth()
                &&Stair->GetMasonry()->IsVisible()&&FloorAt(3.,Stair)&&!EffectOf(Stair);
        };
        if(Check(Repaired(),TEXT("Pay the repair cost once and restore stair collision at the original pose")))
        {
            Stair->TakeDamage(Stair->GetMaximumHealth(),Damage,nullptr,nullptr);
            Check(EffectOf(Stair)&&Repaired(),TEXT("Repair before first animation tick clears this collapse immediately"));
        }
        CheckVillageReset();
    };
    Run();
    Report->SetBoolField(TEXT("passed"),Failures==0);Report->SetArrayField(TEXT("checks"),Checks);
    FString File=FPaths::ProjectSavedDir()/TEXT("DefenseBlocks.json");
    FParse::Value(*Params,TEXT("Out="),File);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    const bool bWritten=FFileHelper::SaveStringToFile(Json,*File,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    Game->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);Game->RemoveFromRoot();
    return bWritten&&Failures==0?0:1;
}
