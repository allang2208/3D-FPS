#include "ColdSteelWorldInteraction.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
AActor* ColdSteelWorldInteraction::TraceTarget(const APlayerController* PC,float Reach)
{
    if(!IsValid(PC)||!PC->GetPawn()||PC->bShowMouseCursor||PC->GetNetMode()!=NM_Standalone)return nullptr;
    FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ColdSteelUse),false,PC->GetPawn());FHitResult Hit;
    return PC->GetWorld()->LineTraceSingleByChannel(Hit,Eye,Eye+View.Vector()*Reach,ECC_Visibility,Query)?Hit.GetActor():nullptr;
}
bool ColdSteelWorldInteraction::IsFocused(const APawn* Pawn,const AActor* Target,float Reach)
{
    return IsValid(Pawn)&&IsValid(Target)&&Pawn->GetWorld()==Target->GetWorld()&&TraceTarget(Cast<APlayerController>(Pawn->GetController()),Reach)==Target;
}
