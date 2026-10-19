#include "FPSOutfitRobeCloth.h"
#include "FPSOutfitRobeAnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"

namespace FPSOutfitRobeCloth
{
static const FName RobeTag(TEXT("OutfitRobeDrape"));
void Initialize(USkeletalMeshComponent* Garment,USkeletalMeshComponent* PoseSource)
{
    if(!Garment||!PoseSource)return;
    Garment->ComponentTags.AddUnique(RobeTag);
    Garment->SetLeaderPoseComponent(nullptr);
    Garment->SetAnimInstanceClass(UFPSOutfitRobeAnimInstance::StaticClass());
    Garment->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Garment->AddTickPrerequisiteComponent(PoseSource);
    Garment->bUseAttachParentBound=false;
    // The cloth-only collision asset is an inner body envelope, not the robe's
    // visible outline (collar, hood and hem). Preserve the authored bounds.
    Garment->bComponentUseFixedSkelBounds=true;
    Garment->SetBoundsScale(1.2f);
    Garment->ClothBlendWeight=0.f;
    Garment->SuspendClothingSimulation();
    Garment->SetComponentTickEnabled(true);
}
void Update(USkeletalMeshComponent* Garment,float DeltaSeconds)
{
    if(!Garment||!Garment->ComponentHasTag(RobeTag))return;
    const auto* Pawn=Cast<APawn>(Garment->GetOwner());
    const bool Local=Pawn&&Pawn->IsLocallyControlled();
    const bool Visible=Garment->IsVisible()&&!Garment->bHiddenInGame&&!(Local&&Garment->bOwnerNoSee);
    float DistanceSquared=MAX_flt;
    if(const auto* World=Garment->GetWorld())
        if(const auto* PC=World->GetFirstPlayerController();PC&&PC->PlayerCameraManager)
            DistanceSquared=FVector::DistSquared(PC->PlayerCameraManager->GetCameraLocation(),Garment->GetComponentLocation());
    const bool Suspended=Garment->IsClothingSimulationSuspended();
    const float Radius=Suspended?1800.f:2200.f;
    const bool Simulate=Visible&&DistanceSquared<Radius*Radius;
    if(Simulate&&Suspended)
    {
        Garment->SetForcedLOD(1);
        Garment->ForceClothNextUpdateTeleportAndReset();
        Garment->ResumeClothingSimulation();
    }
    Garment->ClothBlendWeight=Visible?FMath::FInterpConstantTo(Garment->ClothBlendWeight,Simulate?1.f:0.f,DeltaSeconds,4.f):0.f;
    if(!Simulate&&Garment->ClothBlendWeight<=0.f)
    {
        if(!Garment->IsClothingSimulationSuspended())Garment->SuspendClothingSimulation();
        Garment->SetForcedLOD(0);
    }
    // Keep the cloth-compatible LOD until fade-out is finished. Invisible
    // owner/world duplicates do not run a second cloth solve or pose copy.
    if(Simulate||Garment->ClothBlendWeight>0.f)Garment->SetForcedLOD(1);
    Garment->SetComponentTickEnabled(Visible);
}
}
