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
// Reuse the same bounded projectile pool for the four-layer warm weapon fire.
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
        FlameFX->SetAsset(System);FlameFX->SetAutoActivate(false);FlameFX->SetAutoDestroy(false);
        FlameFX->PrimaryComponentTick.TickGroup=TG_LastDemotable;
        FlameFX->SetTickBehavior(ENiagaraTickBehavior::UseComponentTickGroup);
        FlameFX->SetCastShadow(false);FlameFX->SetVisibleInRayTracing(false);
        FlameFX->RegisterComponent();FlameFX->AddTickPrerequisiteActor(this);
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
    // Arrow actor origin is the tip. Burn only its forward section, using the
    // same local-frame contract as held weapons and no world-space tail layer.
    const float FlameLength=FMath::Clamp(Presentation.Length*.16f,5.f,16.f);
    const float Radius=FMath::Clamp(Presentation.Radius,.1f,1.5f);
    const FQuat Frame=GetActorQuat();
    FlameFX->SetRelativeLocation(FVector(-FlameLength,0,0));
    FlameFX->SetVariableVec3(TEXT("User.WeaponEnd"),FVector(FlameLength,0,0));
    FlameFX->SetVariableVec3(TEXT("User.BladeSide"),FVector::RightVector);
    FlameFX->SetVariableVec3(TEXT("User.WeaponSide"),FVector::RightVector);
    FlameFX->SetVariableVec3(TEXT("User.WeaponNormal"),FVector::UpVector);
    FlameFX->SetVariableVec3(TEXT("User.FlameUp"),Frame.UnrotateVector(FVector::UpVector));
    const FVector LocalFlow=Frame.UnrotateVector(FlameVelocity.GetClampedToMaxSize(1500.f));
    FlameFX->SetVariableVec3(TEXT("User.BaseFlow"),LocalFlow);
    FlameFX->SetVariableVec3(TEXT("User.TipFlow"),LocalFlow);
    FlameFX->SetVariableFloat(TEXT("User.SurfaceMode"),0.f);
    static const FName SurfaceNames[]={TEXT("User.Surface0"),TEXT("User.Surface1"),TEXT("User.Surface2"),TEXT("User.Surface3"),
        TEXT("User.Surface4"),TEXT("User.Surface5"),TEXT("User.Surface6"),TEXT("User.Surface7")};
    for(int32 Station=0;Station<8;++Station)
    {
        const float T=float(Station)/7.f;
        const float HalfWidth=Radius*FMath::Lerp(1.35f,.25f,T);
        FlameFX->SetVariableVec4(SurfaceNames[Station],FVector4(0,0,HalfWidth,HalfWidth));
    }
    FlameFX->SetVariableFloat(TEXT("User.WeaponSize"),.24f);
    FlameFX->SetVariableFloat(TEXT("User.Coverage"),FMath::Clamp(FlameLength/60.f,.15f,1.f));
    FlameFX->SetVariableFloat(TEXT("User.MotionEnergy"),1.f);
    FlameFX->SetVariableFloat(TEXT("User.FlameClock"),GetWorld()->GetTimeSeconds());
    FlameFX->SetVariablePosition(TEXT("User.PreviousPosition"),PreviousFlamePosition);
    FlameFX->SetVariablePosition(TEXT("User.CurrentPosition"),Position);
    FlameFX->SetVariableVec3(TEXT("User.Velocity"),FlameVelocity);
    FlameFX->SetVariableFloat(TEXT("User.Detail"),Detail);
    FlameFX->SetVariableFloat(TEXT("User.VariationSeed"),float(GetUniqueID()&0xffff)*.015625f);
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
        // The copied edge core is persistent. Destroy it with the projectile
        // effect instead of leaving an immortal, detached component behind.
        FlameFX->DeactivateImmediate();FlameFX->DestroyComponent();FlameFX=nullptr;
    }
}
