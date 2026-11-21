#include "TemperateVillageCheckCommandlet.h"
#include "../Building/VillageBuildDefense.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "Engine/GameInstance.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerState.h"

void UTemperateVillageCheckCommandlet::ExerciseDefenseUndo(AVoxelBuildWorld& Build,TFunctionRef<bool(bool,const FString&)> Check)
{
    UWorld* World=Build.GetWorld();
    auto* Floor=World->SpawnActor<AStaticMeshActor>();
    Floor->GetStaticMeshComponent()->SetMobility(EComponentMobility::Movable);
    Floor->GetStaticMeshComponent()->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    Floor->SetActorTransform(FTransform(FQuat::Identity,FVector(72000,72000,150),FVector(60,60,1)));
    auto* A=World->SpawnActor<APlayerState>();
    auto* B=World->SpawnActor<APlayerState>();
    const FIntVector Block=AVoxelBuildWorld::ToCell(FVector(71000,71000,200));
    const FIntVector First=Block+FIntVector(25,2,0),Second=First+FIntVector(35,0,0);
    const FName Wood(TEXT("wood"));
    const auto Wall=[&](FIntVector Cell){return Build.PlacePrefab(VillageBuildDefense::HighWall,Cell,0,false,nullptr,17);};
    TMap<FName,int32> Refund;
    TGuardValue<APlayerState*> Owner(Build.UndoPlayer,A);
    if(!Check(Build.EditCells({Block},Wood)&&Wall(First),TEXT("Undo fixture places a voxel batch followed by a wall")))return;
    Build.UndoPlayer=B;
    Check(!Build.Undo()&&Build.PrefabActorAt(First),TEXT("A second builder with empty history cannot undo the first builder's wall"));
    if(!Check(Wall(Second),TEXT("Second builder places a different wall")))return;
    Build.UndoPlayer=A;
    Check(Build.Undo(&Refund)&&Refund.IsEmpty()&&!Build.PrefabActorAt(First)&&Build.PrefabActorAt(Second)
        &&Build.MaterialAt(Block)==Wood,TEXT("Mixed undo removes the newest personal wall before an older voxel batch"));
    Check(Build.Undo(&Refund)&&Refund.FindRef(Wood)==1&&Build.MaterialAt(Block).IsNone(),
        TEXT("Next undo refunds only the original owner's voxel batch"));
    Build.UndoPlayer=B;
    Check(Build.Undo()&&!Build.PrefabActorAt(Second),TEXT("The other builder still has their own wall undo"));
    Build.UndoPlayer=A;
    if(!Check(Wall(First)&&Wall(Second),TEXT("A single builder can queue two consecutive wall placements")))return;
    Check(Build.Undo()&&!Build.PrefabActorAt(Second)&&Build.PrefabActorAt(First),
        TEXT("Consecutive prefab undo keeps the older wall available"));
    Build.UndoPlayer=B;
    if(!Check(Build.RemovePrefab(Build.PrefabActorAt(First))&&Wall(First),TEXT("Second builder replaces the same wall at the same angle")))return;
    const FGuid Replacement=Build.PrefabInstanceIdentity(First);
    Build.UndoPlayer=A;
    Check(!Build.Undo()&&Build.PrefabInstanceIdentity(First)==Replacement,
        TEXT("Stale history cannot remove another instance with the same cell, recipe and angle"));
    Build.UndoPlayer=B;
    if(!Check(Build.EditCells({Block},Wood)&&Build.RemovePrefab(Build.PrefabActorAt(First)),
        TEXT("Manual demolition succeeds after mixed construction")))return;
    Check(!Build.Undo()&&Build.MaterialAt(Block)==Wood,TEXT("Manual demolition clears the builder's mixed history"));
    Build.EditCells({Block},NAME_None);

    auto* Profile=World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Check(Profile!=nullptr,TEXT("Server request fixture has the profile subsystem")))return;
    auto MakeBuilder=[&](APlayerState* State,FVector Position)
    {
        auto* Model=Profile->CreateShadowModel(Profile->Snapshot());
        auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(Position,FRotator::ZeroRotator);
        if(!Model||!Pawn)return static_cast<UColdSteelStatusModel*>(nullptr);
        Pawn->SetPlayerState(State);Model->AttachPawn(Pawn);
        return Model;
    };
    auto* ModelA=MakeBuilder(A,FVector(71100,70450,330));
    auto* ModelB=MakeBuilder(B,FVector(72400,70600,330));
    if(!Check(ModelA&&ModelB,TEXT("Two builders have distinct server-side pawns and profiles")))return;
    FColdSteelInventoryRequest R;
    R.Action=EColdSteelInventoryAction::Building;
    R.Mode=TEXT("groundDefensePrefab");R.Definition=VillageBuildDefense::HighWall;R.Orientation=17;
    FString Reason;
    R.Anchor=First;
    if(!Check(Build.ExecuteNetworkEdit(R,ModelA,Reason),TEXT("First player places a 17-degree wall through the authoritative request handler: ")+Reason))return;
    R.Anchor=Second;
    if(!Check(Build.ExecuteNetworkEdit(R,ModelB,Reason),TEXT("Second player places a wall through the authoritative request handler: ")+Reason))return;
    R.Mode=TEXT("undo");
    Check(Build.ExecuteNetworkEdit(R,ModelA,Reason)&&!Build.PrefabActorAt(First)&&Build.PrefabActorAt(Second),
        TEXT("Server undo uses the requesting player even when another player made the most recent placement"));
    Check(Build.ExecuteNetworkEdit(R,ModelB,Reason)&&!Build.PrefabActorAt(Second),TEXT("Second player can undo their own request"));
}
