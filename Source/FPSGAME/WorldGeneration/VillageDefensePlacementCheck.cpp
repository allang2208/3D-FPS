#include "TemperateVillageCheckCommandlet.h"
#include "HighVillageDefense.h"
#include "TemperateHillsWorld.h"
#include "../Building/VillageBuildDefense.h"
#include "../Building/VoxelBuildComponent.h"
#include "../Building/VoxelBuildGrounding.h"
#include "../Building/VoxelBuildPalette.h"
#include "../Building/VoxelBuildPersistence.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../Building/VoxelBuildWorld.h"
#include "Camera/PlayerCameraManager.h"
#include "Camera/CameraActor.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"

void UTemperateVillageCheckCommandlet::ExerciseDefensePlacement(AVoxelBuildWorld& Build,ATemperateHillsWorld& Hills,
    AHighVillageWall& GeneratedWall,TFunctionRef<bool(bool,const FString&)> Check)
{
    using namespace VillageBuildDefense;
    UWorld* World=Build.GetWorld();
    const FVector Origin(30000.,30000.,100.);
    auto* Floor=World->SpawnActor<AStaticMeshActor>();
    Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
    Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    Floor->SetActorTransform(FTransform(FQuat::Identity,Origin-FVector(0,0,50),FVector(70,70,1)));
    auto* PC=World->SpawnActor<APlayerController>();
    if(!Check(PC&&PC->PlayerCameraManager,TEXT("Placement input has a camera")))return;
    PC->SetAsLocalPlayerController();
    auto* Camera=World->SpawnActor<ACameraActor>();
    PC->SetViewTarget(Camera);
    auto* Builder=NewObject<UVoxelBuildComponent>(PC);
    Builder->BuildWorld=&Build;
    Builder->Palette=Builder->PaletteAsset.LoadSynchronous();
    Builder->VillageWorld=&Hills;
    Builder->bActive=true;
    Builder->PreviewActor=World->SpawnActor<AActor>();
    auto* Ghost=NewObject<UStaticMeshComponent>(Builder->PreviewActor);
    Builder->PreviewActor->SetRootComponent(Ghost);
    Ghost->SetMobility(EComponentMobility::Movable);
    Ghost->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Ghost->RegisterComponent();
    Builder->Preview=Ghost;
    auto Aim=[&](FVector Eye,FVector Point)
    {
        FMinimalViewInfo View;View.Location=Eye;View.Rotation=(Point-Eye).Rotation();
        // At commandlet time zero the controller reads its view target directly.
        Camera->SetActorLocationAndRotation(Eye,View.Rotation);
        PC->SetControlRotation(View.Rotation);
        PC->PlayerCameraManager->SetCameraCachePOV(View);
        Builder->UpdateTarget();
    };
    auto Press=[&](FKey Key)
    {
        Builder->HandleInput(FInputKeyEventArgs::CreateSimulated(Key,IE_Pressed,1.f),false);
        Builder->HandleInput(FInputKeyEventArgs::CreateSimulated(Key,IE_Released,0.f),false);
    };
    auto PreviewPlacement=[&]()
    {
        FTransform Pose=Ghost->GetComponentTransform();
        // The timber preview root is its left hinge. The installed assembly pivots at the centre.
        if(Builder->SelectedComponent==WoodGate)
            Pose.AddToTranslation(Pose.TransformVectorNoScale(FVector(AVillageDefenseGate::NarrowHingeOffset,0.,0.)));
        return Pose;
    };
    auto Commit=[&](const FString& Label)->AVoxelBuildPrefabActor*
    {
        const FTransform Seen=PreviewPlacement();
        const FIntVector Cell=Builder->PrefabCell;
        if(!Check(Builder->bPrefabValid,Label+TEXT(" valid preview: ")+Builder->PrefabMessage))return nullptr;
        Press(EKeys::LeftMouseButton);
        auto* Wrapper=Build.PrefabActorAt(Cell);
        if(!Check(Wrapper&&Wrapper->Logic()&&Wrapper->Logic()->GetActorTransform().Equals(Seen,.03)
            &&Wrapper->Logic()->GetActorQuat().Equals(Seen.GetRotation(),1.e-5),
            Label+TEXT(" click commits the shown transform: ")+Build.ResultMessage()))return nullptr;
        return Wrapper;
    };
    auto SnapshotKeepsPose=[&](FName Id,FIntVector Cell,const FTransform& Expected,bool bExpectDock)
    {
        TArray<uint8> Bytes;
        const auto* Snapshot=Build.MakeNetworkSnapshot(Bytes)?VoxelPersistence::Decode(MoveTemp(Bytes)):nullptr;
        const auto* Saved=Snapshot?Snapshot->Prefabs.FindByPredicate([&](const auto& Entry){return Entry.Cell==Cell;}):nullptr;
        if(!Saved||Saved->Id!=Id||(bExpectDock&&!Saved->WallDockPose.IsSet()))return false;
        const FTransform Restored=VillageWallStairs::Placement(*Saved);
        return Restored.GetLocation().Equals(Expected.GetLocation(),.03)
            &&Restored.GetScale3D().Equals(Expected.GetScale3D(),1.e-5)
            &&Restored.GetRotation().Equals(Expected.GetRotation(),1.e-5);
    };
    const int32 Brush=Builder->Brush;
    AVoxelBuildPrefabActor* Host=nullptr;
    // Interleave the two v17 recipes with records carrying the earlier conditional pose fields.
    // A reader that consumes a flag for the wrong recipe loses alignment before the final gate.
    for(const int32 Version:{14,15,16,17})
    {
        FVoxelDiskSnapshot Mixed;
        Mixed.Version=Version;
        Mixed.WorldKey=TEXT("village-pose-versions");
        for(const FName Id:{StoneWall,HighWall,WoodGate,VillageWallStairs::Id,StoneGate})
        {
            const int32 Index=Mixed.Prefabs.Num();
            auto& Entry=Mixed.Prefabs.AddDefaulted_GetRef();
            Entry.Id=Id;
            Entry.InstanceId=FGuid::NewGuid();
            Entry.Cell=FIntVector(Index*60,20,5);
            Entry.Footprint=Builder->Palette->FindComponent(Id)->Footprint;
            Entry.WallDockPose=Placement(Id,Entry.Cell,Entry.Footprint,0,13+Index);
        }
        TArray<uint8> Bytes;
        const auto* Loaded=VoxelPersistence::Encode(Mixed,Bytes)?VoxelPersistence::Decode(MoveTemp(Bytes)):nullptr;
        bool bMatching=Loaded&&Loaded->Prefabs.Num()==Mixed.Prefabs.Num();
        for(int32 Index=0;bMatching&&Index<Mixed.Prefabs.Num();++Index)
        {
            const auto& Record=Loaded->Prefabs[Index];
            const bool bHasPose=Version>=17||(Version>=16&&VillageWallStairs::CanDock(Record.Id))||
                (Version>=15&&Record.Id==VillageWallStairs::Id);
            bMatching=Record.Id==Mixed.Prefabs[Index].Id&&Record.WallDockPose.IsSet()==bHasPose&&
                (!bHasPose||Record.WallDockPose->Equals(Mixed.Prefabs[Index].WallDockPose.GetValue(),.001));
        }
        Check(bMatching,FString::Printf(TEXT("Mixed village records retain the v%d pose layout and scale"),Version));
    }
    auto Sample=[&](AVoxelBuildPrefabActor* Piece)
    {
        const FName Id=Piece->PrefabId();
        const FTransform Frame=Piece->GetActorTransform();
        const FVector Point=Id==StoneGate?FVector(-382,0,140):Id==VillageWallStairs::Id?
            FVector(80,-200,300):Id==WoodGate?FVector(-180,0,100):FVector(0,0,110);
        Builder->SelectComponent(NAME_None);
        const FVector View=Id==VillageWallStairs::Id?FVector(0,0,210):FVector(0,355,0);
        Aim(Frame.TransformPosition(Point+View),Frame.TransformPosition(Point));
        Press(EKeys::MiddleMouseButton);
        const int32 Yaw=FMath::RoundToInt(FRotator::ClampAxis(Frame.Rotator().Yaw))%360;
        Check(Builder->SelectedComponent==Id && Builder->GroundYawDegrees==Yaw,
            Id.ToString()+TEXT(" middle-click samples the placed recipe and its orientation from voxel mode"));
    };
    for(const FName Id:{StoneWall,WoodGate})
    {
        const auto Cell=AVoxelBuildWorld::ToCell(Origin+FVector(-1500,-900,0));
        if(!Check(Build.PlacePrefab(Id,Cell,1),Id.ToString()+TEXT(" legacy village piece places at a quarter turn")))continue;
        auto* Piece=Build.PrefabActorAt(Cell);
        Sample(Piece);
        Build.RemovePrefab(Piece);
        if(!Check(Build.PlacePrefab(Id,Cell,0,false,nullptr,45),Id.ToString()+TEXT(" places at 45 degrees")))continue;
        Piece=Build.PrefabActorAt(Cell);
        const FTransform Frame=Piece->GetActorTransform();
        const double NearEnd=(Builder->Palette->FindComponent(Id)->Footprint.X*.5-1.)*20.;
        const FIntVector Along=AVoxelBuildWorld::ToCell(Frame.TransformPosition(FVector(NearEnd,0.,10.)));
        const FIntVector Outside=AVoxelBuildWorld::ToCell(Frame.TransformPosition(FVector(0.,NearEnd,10.)));
        Check(Build.IsPrefabCell({},Along)&&!Build.IsPrefabCell({},Outside),
            Id.ToString()+TEXT(" diagonal occupancy reserves the wall end and leaves the opposite corner free"));
        Build.RemovePrefab(Piece);
        Check(!Build.IsPrefabCell({},Along),Id.ToString()+TEXT(" removal frees the rotated footprint"));
    }
    for(const FName Id:{StoneWall,WoodGate,VillageWallStairs::Id,StoneGate,HighWall})
    {
        Builder->SelectComponent(Id);
        Aim(Origin+FVector(0,0,240),Origin);
        Press(EKeys::MouseScrollDown);
        const FTransform Reversed=PreviewPlacement();
        Check(!Builder->DefenseDockPose.IsSet()&&Builder->Brush==Brush
            &&Reversed.GetRotation().Equals(FRotator(0.,-1.,0.).Quaternion(),1.e-5),
            Id.ToString()+TEXT(" one reverse wheel step wraps from 0 to 359 degrees without changing brush"));
        auto* Angled=Commit(Id.ToString()+TEXT(" at 359 degrees"));
        if(!Angled)return;
        Check(SnapshotKeepsPose(Id,Angled->AnchorCell(),Reversed,false),
            Id.ToString()+TEXT(" snapshot round-trip keeps the 359-degree ground placement"));
        if(Id==VillageWallStairs::Id)
        {
            const FTransform S=Angled->GetActorTransform();
            Builder->SelectComponent(HighWall);
            bool bFoundEdge=false;
            for(int32 X=160;X<=200&&!bFoundEdge;++X)
            {
                Aim(S.TransformPosition(FVector(X,-490,280)),S.TransformPosition(FVector(X,-100,280)));
                bFoundEdge=Builder->LastAimWasAssisted&&Builder->DefenseDockTarget.Get()==Angled->Logic();
            }
            Builder->SelectComponent(Id);
            Builder->UpdateTarget();
            Check(bFoundEdge&&!Builder->LastAimWasAssisted&&!Builder->DefenseDockPose.IsSet(),
                TEXT("Cone assist accepts the landing for a wall and skips the same edge for another stair"));
        }
        Sample(Angled);
        if(!Check(Build.RemovePrefab(Angled),TEXT("Clear the angled ground fixture")))return;
        Aim(Origin+FVector(0,0,240),Origin);
        Press(EKeys::MouseScrollUp);
        Check(Ghost->GetComponentQuat().Equals(FQuat::Identity,1.e-5),
            Id.ToString()+TEXT(" one forward wheel step returns from 359 to 0 degrees"));
        if(Id==StoneGate)
            Check(Builder->VillageGatePreviewParts.Num()==1&&Builder->VillageGatePreviewParts[0]->GetStaticMesh(),
                TEXT("Stone gate ghost includes the portcullis"));
        auto* Piece=Commit(Id.ToString()+TEXT(" ground"));
        if(!Piece)return;
        if(Id==HighWall)Host=Piece;
        else if(!Check(Build.RemovePrefab(Piece),TEXT("Clear the previous ground fixture")))return;
    }
    auto* Wall=CastChecked<AHighVillageWall>(Host->Logic());
    const FVector P=Wall->GetActorLocation();
    const FName Torch(TEXT("bronze_torch"));
    for(const int32 Side:{-1,1})
    {
        Builder->SelectComponent(Torch);
        Aim(P+FVector(13,Side*390,170),P+FVector(13,0,170));
        const auto Cell=Builder->PrefabCell;
        if(Check(Builder->SelectedComponent==Torch&&Builder->bPrefabValid,
            FString::Printf(TEXT("Fixed wall face %d accepts the bronze torch preview: %s (hit %s, normal %s, cell %s)"),
                Side,*Builder->PrefabMessage,*GetNameSafe(Builder->Hit.GetComponent()),
                *Builder->Hit.ImpactNormal.ToCompactString(),*Cell.ToString())))
        {
            Press(EKeys::LeftMouseButton);
            auto* Fixture=Build.PrefabActorAt(Cell);
            Check(Fixture&&Fixture->PrefabId()==Torch,FString::Printf(TEXT("Torch on wall face %d commits from the same preview"),Side));
            if(Fixture)Build.RemovePrefab(Fixture);
        }
    }
    const FVector Walk=GeneratedWall.GetActorTransform().TransformPosition(FVector(0,55,360));
    FHitResult Top;
    Check(World->LineTraceSingleByChannel(Top,Walk+FVector(0,0,55),Walk-FVector(0,0,55),ECC_Visibility,VoxelGrounding::Query(World,&Build))
        &&Top.GetActor()==&GeneratedWall&&VoxelGrounding::IsSurface(Top),
        TEXT("The generated wall walk is a fixed building surface for the voxel ground probe"));
    Builder->SelectComponent(HighWall);
    Aim(P+FVector(153,430,230),P+FVector(153,0,230));
    Check(Builder->LastAimWasAssisted&&Builder->DefenseDockTarget.Get()==Wall,
        TEXT("Existing cone assist catches the exposed wall edge on a near miss"));
    for(FName Id:{HighWall,StoneGate,VillageWallStairs::Id})
    {
        Builder->SelectComponent(Id);
        const FVector Away=P+FVector(1500,0,0);
        Aim(Away+FVector(0,0,240),Away);
        Press(EKeys::MouseScrollUp);
        const FQuat FreeRotation=FRotator(0.,1.,0.).Quaternion();
        Check(Ghost->GetComponentQuat().Equals(FreeRotation,1.e-5),
            Id.ToString()+TEXT(" forward ground step advances to 1 degree"));
        Aim(P+FVector(-118,390,145),P+FVector(-118,0,145));
        if(!Check(Builder->DefenseDockTarget.Get()==Wall,Id.ToString()+TEXT(" captures the player-built high wall")))return;
        const FTransform Initial=Ghost->GetComponentTransform();
        Press(EKeys::MouseScrollUp);
        Check(Builder->DefenseDockTarget.Get()==Wall&&!Initial.Equals(Ghost->GetComponentTransform(),.01),
            Id.ToString()+TEXT(" wheel changes the snapped pose on the same target"));
        auto* Rotated=Commit(Id.ToString()+TEXT(" rotated dock"));
        if(Rotated)Build.RemovePrefab(Rotated);
        Press(EKeys::MouseScrollDown);
        Check(Initial.Equals(Ghost->GetComponentTransform(),.03),Id.ToString()+TEXT(" reverse wheel restores dock"));
        Press(EKeys::F);
        Check(!Builder->DefenseDockPose.IsSet()&&Ghost->GetComponentQuat().Equals(FreeRotation,1.e-5),
            Id.ToString()+TEXT(" F releases dock and restores the one-degree ground direction"));
        Press(EKeys::F);
        Check(Builder->DefenseDockPose.IsSet()&&Initial.Equals(Ghost->GetComponentTransform(),.03),
            Id.ToString()+TEXT(" F reacquires dock"));
        auto* Added=Commit(Id.ToString()+TEXT(" dock"));
        if(!Added)continue;
        FString Reason;
        Check(!Build.CanPlacePrefab(Id,Builder->PrefabCell,Builder->PrefabPlanYaw,Reason,false,true,Wall),
            Id.ToString()+TEXT(" occupied connection rejects duplicate placement"));
        Check(SnapshotKeepsPose(Id,Added->AnchorCell(),Initial,true),
            Id.ToString()+TEXT(" saved and replicated snapshot keeps the exact dock pose"));
        if(Id==StoneGate)
        {
            auto* Gate=CastChecked<AHighVillageGate>(Added->Logic());
            Check(Gate->GetStonePortal()->GetStaticMesh()&&Gate->GetMasonry()->GetStaticMesh(),TEXT("Placed portal and iron grille both resolve"));
            FHitResult Arch(Gate,Gate->GetStonePortal(),FVector::ZeroVector,FVector::UpVector);
            FHitResult Grille(Gate,Gate->GetMasonry(),FVector::ZeroVector,FVector::UpVector);
            Check(VoxelGrounding::IsFixedBuildingSurface(Arch)&&!VoxelGrounding::IsFixedBuildingSurface(Grille),
                TEXT("The fixed arch accepts attachments and the moving portcullis rejects them"));
            VillageWallStairs::FDock Left,Right;
            const auto Size=Builder->Palette->FindComponent(HighWall)->Footprint;
            const FTransform G=Gate->GetActorTransform();
            const bool Both=VillageWallStairs::MakeDock(HighWall,Size,Gate,G.TransformPosition(FVector(-434,0,0)),0,Left)
                &&VillageWallStairs::MakeDock(HighWall,Size,Added,G.TransformPosition(FVector(434,0,0)),0,Right);
            Check(Both&&!Left.Pose.Equals(Right.Pose,.01),TEXT("Both jambs offer distinct wall connections"));
            const auto StairSize=Builder->Palette->FindComponent(VillageWallStairs::Id)->Footprint;
            Check(VillageWallStairs::MakeDock(VillageWallStairs::Id,StairSize,Gate,G.TransformPosition(FVector(-434,0,220)),0,Left)
                &&VillageWallStairs::MakeDock(VillageWallStairs::Id,StairSize,Gate,G.TransformPosition(FVector(434,80,220)),0,Right)
                &&!Left.Pose.Equals(Right.Pose,.01),
                TEXT("Independent stairs dock separately at both gallery landings"));
            VillageWallStairs::FDock Overlap;
            const auto GateSize=Builder->Palette->FindComponent(StoneGate)->Footprint;
            const bool Offered=VillageWallStairs::MakeDock(StoneGate,GateSize,Gate,G.TransformPosition(FVector(-434,0,0)),0,Overlap);
            Check(Offered&&!Build.CanPlacePrefab(StoneGate,Overlap.Anchor,Overlap.Yaw,Reason,false,true,Gate),
                TEXT("A second portal cannot place its projecting lookout inside the host gate pier"));
        }
        Build.RemovePrefab(Added);
    }
    const auto Size=Builder->Palette->FindComponent(VillageWallStairs::Id)->Footprint;
    VillageWallStairs::FDock Exact,Replayed;
    const bool Matched=VillageWallStairs::MakeDock(VillageWallStairs::Id,Size,&GeneratedWall,GeneratedWall.GetActorLocation(),0,Exact)
        &&VillageWallStairs::FindDock(World,VillageWallStairs::Id,Size,Exact.Anchor,Exact.Yaw,Replayed,&GeneratedWall);
    Check(Matched&&Exact.Pose.Equals(Replayed.Pose,.01)
        &&Exact.Pose.TransformPosition(FVector(80,-280,360)).Equals(GeneratedWall.GetActorTransform().TransformPosition(FVector(0,167,360)),.01),
        TEXT("Generated rotated wall replays the exact landing seam at 360 cm"));
    ExerciseDefenseSupport(Build,Origin,Check);
}
