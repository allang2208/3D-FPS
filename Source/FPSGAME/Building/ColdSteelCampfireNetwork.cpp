#include "ColdSteelCampfire.h"
#include "CampfireCookingPresentation.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildPrefabActor.h"
#include "SmeltingSystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"

bool AColdSteelCampfire::ResolveStation(AVoxelBuildWorld*& World,FIntVector& Cell) const
{
    const auto* Piece=Cast<AVoxelBuildPrefabActor>(GetAttachParentActor());
    World=Piece?Cast<AVoxelBuildWorld>(Piece->GetOwner()):nullptr;
    if(!IsAvailable()||!Piece||!World||Piece->IsFalling()||Piece->Logic()!=this)return false;
    Cell=Piece->AnchorCell();
    return World->HasAuthority()&&World->IsReady()&&World->IsCampfireAt(Cell)&&World->PrefabActorAt(Cell)==Piece;
}
bool AColdSteelCampfire::CanOperate(const APlayerController* PC) const
{
    const APawn* Pawn=PC?PC->GetPawn():nullptr;
    if(!IsAvailable()||!Pawn||Pawn->GetWorld()!=GetWorld()
        ||FVector::DistSquared(Pawn->GetActorLocation(),GetActorLocation())>FMath::Square(350.f))return false;
    const auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Health&&Health->IsDead())return false;
    FHitResult Hit;FCollisionQueryParams Q(SCENE_QUERY_STAT(CampfireOperate),false,Pawn);
    const bool Blocked=GetWorld()->LineTraceSingleByChannel(Hit,Pawn->GetPawnViewLocation(),GetActorLocation()+FVector(0,0,25),ECC_Visibility,Q);
    return !Blocked||Hit.GetActor()==this||Hit.GetActor()==GetAttachParentActor();
}
void AColdSteelCampfire::PublishSharedState(bool Force)
{
    if(!HasAuthority())return;
    const double Now=GetWorld()->GetTimeSeconds();
    if(!Force&&Now-LastSharedPublish<.5)return;
    AVoxelBuildWorld* W=nullptr;FIntVector Cell;
    if(!ResolveStation(W,Cell))return;
    auto* S=GetGameInstance()->GetSubsystem<UColdSteelSmeltingSystem>();if(!S)return;
    const int32 Next=Shared.Revision+1;
    Shared=S->CampfireState(W,Cell);Shared.ServerTime=Now;Shared.Revision=Next;
    LastSharedPublish=Now;OnRep_Shared();ForceNetUpdate();
}
void AColdSteelCampfire::OnRep_Shared()
{
    if(CookingPresentation)CookingPresentation->Update(bPresentationRequested);
}
double AColdSteelCampfire::DisplayFuel() const
{
    const auto* GS=GetWorld()->GetGameState();
    const double Now=GS?GS->GetServerWorldTimeSeconds():Shared.ServerTime;
    return FMath::Max(0.0,Shared.Fuel-(Shared.bSaveBlocked?0.0:FMath::Max(0.0,Now-Shared.ServerTime)));
}
double AColdSteelCampfire::DisplayProgress() const
{
    const auto* GS=GetWorld()->GetGameState();
    const double Now=GS?GS->GetServerWorldTimeSeconds():Shared.ServerTime;
    return Shared.Progress+(Shared.BurnTicks>0&&!Shared.bSaveBlocked
        ?FMath::Min(Shared.Fuel,FMath::Max(0.0,Now-Shared.ServerTime)):0.0);
}
