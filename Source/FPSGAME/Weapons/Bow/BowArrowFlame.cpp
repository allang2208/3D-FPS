#include "BowArrow.h"
#include "../../Skills/FPSFireMagicComponent.h"
#include "../../Skills/FlameArmorAssets.h"
#include "Components/SceneComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"

namespace
{
// Includes the short dying tail, so rapid releases cannot grow an unbounded FX pool.
TArray<TWeakObjectPtr<UNiagaraComponent>> ArrowFlames;
constexpr int32 MaxArrowFlamesPerWorld=8;
}

void ABowArrow::UpdateFlameVisual(float Delta)
{
    if(GetNetMode()==NM_DedicatedServer||!Presentation.bFlameArmor||bStuck||IsActorBeingDestroyed())return;
    float Detail=1.f;
    if(const auto* PC=GetWorld()->GetFirstPlayerController();PC&&PC->PlayerCameraManager)
    {
        const double Distance=FVector::DistSquared(PC->PlayerCameraManager->GetCameraLocation(),GetActorLocation());
        if(Distance>FMath::Square(5000.f)){StopFlameVisual();return;}
        if(Distance>FMath::Square(1800.f))Detail=.5f;
    }
    if(!IsValid(FlameFX))
    {
        ArrowFlames.RemoveAll([](const auto& FX){return !FX.IsValid();});
        int32 Count=0;for(const auto& FX:ArrowFlames)if(FX->GetWorld()==GetWorld())++Count;
        if(Count>=MaxArrowFlamesPerWorld)return;
        const auto* Fire=GetInstigator()?GetInstigator()->FindComponentByClass<UFPSFireMagicComponent>():nullptr;
        auto* System=Fire?Fire->GetArmorArrowSystem():nullptr;
        if(!System)System=Cast<UNiagaraSystem>(FSoftObjectPath(FlameArmorAssets::Arrow).ResolveObject());
        if(!System)
        {
            if(!bFlameLoadRequested)
            {
                bFlameLoadRequested=true;
                FlameLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(FSoftObjectPath(FlameArmorAssets::Arrow),
                    FStreamableDelegate::CreateWeakLambda(this,[this](){UpdateFlameVisual(0.f);}));
            }
            return;
        }
        FlameFX=NewObject<UNiagaraComponent>(this,NAME_None,RF_Transient);
        AddInstanceComponent(FlameFX);FlameFX->SetupAttachment(Root);
        FlameFX->SetAsset(System);FlameFX->SetAutoActivate(false);FlameFX->SetAutoDestroy(true);
        FlameFX->SetCastShadow(false);FlameFX->SetVisibleInRayTracing(false);
        FlameFX->RegisterComponent();FlameFX->AddTickPrerequisiteActor(this);
        FlameFX->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);
        ArrowFlames.Add(FlameFX.Get());bFlameHistoryValid=false;
    }
    const FVector Position=GetActorLocation();
    if(!bFlameHistoryValid||FVector::DistSquared(PreviousFlamePosition,Position)>FMath::Square(1200.f))
    {
        PreviousFlamePosition=Position;FlameVelocity=GetActorForwardVector()*Speed;
        FlameFX->ResetSystem();
    }
    const FVector Displacement=Position-PreviousFlamePosition;
    if(HasAuthority())FlameVelocity=Velocity;
    else if(Delta>SMALL_NUMBER&&!Displacement.IsNearlyZero())FlameVelocity=(Displacement/Delta).GetClampedToMaxSize(12000.f);
    FlameFX->SetVariablePosition(TEXT("User.PreviousPosition"),PreviousFlamePosition);
    FlameFX->SetVariablePosition(TEXT("User.CurrentPosition"),Position);
    FlameFX->SetVariableVec3(TEXT("User.Velocity"),FlameVelocity);
    FlameFX->SetVariableFloat(TEXT("User.Detail"),Detail);
    FlameFX->SetVariableFloat(TEXT("User.Fade"),1.f);
    if(!FlameFX->IsActive())FlameFX->Activate(true);
    PreviousFlamePosition=Position;bFlameHistoryValid=true;
}

void ABowArrow::StopFlameVisual()
{
    if(FlameLoad){FlameLoad->CancelHandle();FlameLoad.Reset();}
    bFlameLoadRequested=false;bFlameHistoryValid=false;
    if(IsValid(FlameFX))
    {
        // World-space particles finish at the contact point in at most .24 seconds.
        FlameFX->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
        FlameFX->Deactivate();FlameFX=nullptr;
    }
}
