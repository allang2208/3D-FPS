#include "RuneSwordComponent.h"
#include "../Characters/FPSComponentVisibility.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Movement/PlayerKnockdownComponent.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"

// Player knockdown (2026-11-14). A_RuneSword_Knockdown is sampled on the knockdown component's clock so the
// arms' ground impact lands on the same frame as the camera's (PlayerKnockdownMotion::Impact).
void URuneSwordComponent::PresentKnockdown(float Age)
{
    if(!Character.IsValid()||!Character->IsLocallyControlled()||!IsEquipped()||!Viewmodel)return;
    if(!Animations.FindRef(TEXT("Knockdown")))
    {
        UE_LOG(LogTemp,Warning,TEXT("KNOCKDOWN A_RuneSword_Knockdown missing for %s; the camera falls with the idle pose."),
            *EquippedAnimationFolder);
        return;
    }
    // Attacks, guard, charge and inspect yield. CancelAction's return to Idle captures the interrupted pose,
    // and that short entry blend keeps running into the knockdown's first (idle) frame.
    CancelAction();
    bKnockdownPose=true;
    SetClip(TEXT("Knockdown"),false);
    if(CurrentAnimation){Elapsed=FMath::Clamp(Age,0.f,CurrentAnimation->GetPlayLength());SamplePose(Elapsed);}
}

bool URuneSwordComponent::TickKnockdown(float Delta)
{
    if(!bKnockdownPose)return false;
    auto* Pawn=Character.Get();
    const auto* Knockdown=UPlayerKnockdownComponent::Find(Pawn);
    const auto* Health=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    if(!CanPresent()||(Health&&Health->IsDead())){CancelAction();return false;}
    FPSComponentVisibility::SetVisibilityTree(Viewmodel,true);
    if(!Knockdown||!Knockdown->IsRunning()||CurrentClip!=TEXT("Knockdown")||!CurrentAnimation)
    {
        bKnockdownPose=false;SetClip(TEXT("Idle"),true);
        return true;
    }
    Elapsed=FMath::Min(CurrentAnimation->GetPlayLength(),Knockdown->Age());
    SamplePose(Elapsed);
    return true;
}
