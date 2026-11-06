#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/HighlandRidgeGatherComponent.h"
#include "../Weapons/HighlandRidgeThrust.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

void UFPSPlayerBodyComponent::PresentRidgeGather()
{
    if(GetNetMode()==NM_DedicatedServer||!Character.IsValid())return;
    // Remote players and the local third-person camera use the world blade,
    // after the final hand pose. First person uses its own sampled viewmodel.
    if(DisplayState.Family==TEXT("Melee")&&DisplayState.Action!=EFPSBodyAction::Dead&&
        (!Character->IsLocallyControlled()||IsThirdPersonViewEnabled()))
    {
        static const FName RidgeMesh(TEXT("SM_Highland_Blade_RidgePiercer_V1"));
        for(const auto& Binding:MotionBindings)
        {
            if(Binding.Definition.ItemInstance!=DisplayState.WeaponInstance||Binding.Definition.PoseFamily!=TEXT("Sword"))continue;
            const auto IsRidge=[&](UStaticMeshComponent* Part)
            {return Part&&Part->GetStaticMesh()&&Part->GetStaticMesh()->GetFName()==RidgeMesh;};
            UStaticMeshComponent* Blade=Binding.Static.Get();
            if(!IsRidge(Blade))
            {
                const auto* Part=Binding.Parts.FindByPredicate([&](const auto& P){return IsRidge(P.Get());});
                Blade=Part?Part->Get():nullptr;
            }
            if(!Blade)continue;
            if(!WorldRidgeGather)WorldRidgeGather=UHighlandRidgeGatherComponent::CreateFor(GetOwner(),false);
            if(DisplayState.Action==EFPSBodyAction::Thrust&&HighlandRidgeThrust::IsRelease(DisplayState.ActionVariant)&&
                Blade->IsVisible()&&!Blade->bHiddenInGame&&!IsWorldWeaponStowed(Blade))
            {
                const float Duration=DisplayState.ActionDuration,Peak=DisplayState.ReleaseFraction*Duration;
                Blade->UpdateComponentToWorld();
                const FTransform& Frame=Blade->GetComponentTransform();
                const FVector Tip=Frame.TransformPosition(FVector(0,0,Blade->GetStaticMesh()->GetBoundingBox().Max.Z));
                const FTransform Eye(Character->GetBaseAimRotation(),Character->GetPawnViewLocation());
                WorldRidgeGather->Present(Eye,Tip,Frame.GetUnitAxis(EAxis::Z),
                    DisplayState.ActionProgress*Duration-Peak,FMath::Min(.22f,Peak));
                return;
            }
            break;
        }
    }
    if(WorldRidgeGather)WorldRidgeGather->Hide();
}
