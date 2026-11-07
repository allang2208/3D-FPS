#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/HighlandRidgeThrust.h"
#include "../Weapons/OathJudgmentVisualComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"

void UFPSPlayerBodyComponent::PresentOathRune()
{
    if(GetNetMode()==NM_DedicatedServer||!Character.IsValid())return;
    const auto* Sword=Character->FindComponentByClass<URuneSwordComponent>();
    if(Sword&&DisplayState.Family==TEXT("Melee")&&DisplayState.Action!=EFPSBodyAction::Dead&&
        (!Character->IsLocallyControlled()||IsThirdPersonViewEnabled()))
    for(const auto& Binding:MotionBindings)
    {
        if(Binding.Definition.ItemInstance!=DisplayState.WeaponInstance||Binding.Definition.PoseFamily!=TEXT("Sword"))continue;
        auto IsOath=[](UStaticMeshComponent* Part)
        {
            if(!Part||!Part->GetStaticMesh())return false;
            for(int32 I=0;I<Part->GetNumMaterials();++I)
                if(auto* M=Part->GetOverlayMaterial(true,I);M&&M->GetBaseMaterial()->GetName().Contains(TEXT("HighlandOath")))return true;
            return false;
        };
        UStaticMeshComponent* Blade=Binding.Static.Get();
        if(!IsOath(Blade)){const auto* P=Binding.Parts.FindByPredicate([&](const auto& Part){return IsOath(Part.Get());});Blade=P?P->Get():nullptr;}
        if(!Blade||!Blade->IsVisible()||Blade->bHiddenInGame||IsWorldWeaponStowed(Blade))continue;
        if(!WorldOathVisual)WorldOathVisual=UOathJudgmentVisualComponent::CreateFor(GetOwner(),false);
        const FTransform Frame=Blade->GetComponentTransform();const FBox Bounds=Blade->GetStaticMesh()->GetBoundingBox();
        const auto& Current=Sword->OathPresentation();
        const auto State=Current.Weapon==DisplayState.WeaponInstance?Current:FHighlandOathPresentation{};
        EOathStroke Stroke=EOathStroke::None;
        const float Duration=FMath::Max(.01f,DisplayState.ActionDuration);
        // Use post-pose world geometry and the replicated executor markers. Allow
        // a short sampling margin for low frame rates / observer interpolation.
        const bool Cutting=DisplayState.bHasActionProgress && DisplayState.ActionProgress>=DisplayState.ContactFraction &&
            DisplayState.ActionProgress<=DisplayState.ReleaseFraction+.08f/Duration;
        // A short thrust may reach its fixed end pose before the first body update.
        // Catch that endpoint once while it is still held, without tracing recovery.
        const float AfterPeak=(DisplayState.ActionProgress-DisplayState.ReleaseFraction)*Duration;
        const bool HeldEndpoint=DisplayState.bHasActionProgress && AfterPeak>=0.f &&
            AfterPeak<=HighlandRidgeThrust::HoldSeconds && WorldOathVisual->NeedsThrustEndpoint(State);
        if((Cutting||HeldEndpoint) && DisplayState.ActionVariant==HighlandRidgeThrust::Release)Stroke=EOathStroke::Thrust;
        else if(Cutting && DisplayState.ActionVariant==TEXT("HeavyRelease"))Stroke=EOathStroke::Slash;
        WorldOathVisual->Present(Blade,Frame.TransformPosition(FVector(0,0,Bounds.Min.Z)),Frame.TransformPosition(FVector(0,0,Bounds.Max.Z)),
            State,Sword->OathClock(),Sword->OathImpactTime(State),Sword->OathImpactPoint,Stroke);
        return;
    }
    if(WorldOathVisual)WorldOathVisual->Hide();
}
