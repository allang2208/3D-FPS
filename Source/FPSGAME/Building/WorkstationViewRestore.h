#pragma once
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"

namespace ColdSteelWorkstationView
{
inline void Restore(APlayerController* Player,AActor* View,APawn* WorkingPawn,AActor* PreviousView,float BlendSeconds)
{
    if(!Player||!View)return;
    const bool Pending=Player->PlayerCameraManager&&Player->PlayerCameraManager->PendingViewTarget.Target==View;
    if(Player->GetViewTarget()!=View&&!Pending)return;
    const bool PawnChanged=Player->GetPawn()!=WorkingPawn;
    AActor* Target=(!PawnChanged&&IsValid(PreviousView)&&!PreviousView->IsActorBeingDestroyed())?PreviousView:Player->GetPawn();
    if(!Target)Target=Player;
    // A respawn may finish while the old workstation is blending in. Never
    // restore its old pawn over the controller's newly possessed character.
    Player->SetViewTargetWithBlend(Target,PawnChanged?0.f:BlendSeconds,VTBlend_Cubic);
}
}
