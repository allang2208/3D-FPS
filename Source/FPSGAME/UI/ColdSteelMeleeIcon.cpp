#include "ColdSteelWeaponIcons.h"
#include "FPSPerformanceMetrics.h"
#include "Engine/GameInstance.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "ColdSteelMeleePreview.h"
#include "ColdSteelStaffPreview.h"
#include "../Weapons/MeleeRuneVisual.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "../Weapons/Staff/StaffAssembly.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/Texture.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"

bool UColdSteelWeaponIcons::PrepareMelee(const FColdSteelItem& Item)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Icon_PrepareMelee);
    FFPSPerformanceScope MeleeScope(bCatalogExport?nullptr:GetGameInstance(),TEXT("Icon.MeleeAssembly"));
    const bool Staff=ColdSteelStaff::IsStaff(Item);
    const bool Modular=ColdSteelModularSword::Supports(Item);
    const FString Path=Staff||Modular?FString():ColdSteelMeleePreview::MeshPath(Item);
    auto* Asset=Path.IsEmpty()?nullptr:LoadObject<UStaticMesh>(nullptr,*Path);
    if(!Staff&&!Modular&&!Asset)return false;
    if(!MeleeMesh)
    {
        MeleeMesh=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
        MeleeMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);MeleeMesh->SetForcedLodModel(1);
        Studio->AddComponent(MeleeMesh,FTransform::Identity);
    }
    if(!Staff)ColdSteelStaffAssembly::Clear(MeleeMesh);
    if(Staff)
    {
        ColdSteelModularSword::Clear(MeleeMesh);MeleeMesh->EmptyOverrideMaterials();MeleeMesh->SetOverlayMaterial(nullptr);
        const ColdSteelStaff::FParts Factory;
        if(!ColdSteelStaffAssembly::Apply(MeleeMesh,ColdSteelStaff::Resolve(Item,bCatalogExport?&Factory:nullptr)))return false;
        if(!ColdSteelStaffPreview::ApplyMaterials(MeleeMesh))return false;
    }
    else if(Modular)
    {
        if(!ColdSteelModularSword::Apply(MeleeMesh,Item,nullptr,!bCatalogExport))return false;
        if(!ColdSteelModularSword::ApplyGlassPreview(MeleeMesh))return false;
    }
    else {ColdSteelModularSword::Clear(MeleeMesh);MeleeMesh->EmptyOverrideMaterials();MeleeMesh->SetStaticMesh(Asset);ColdSteelMeleeRune::Apply(MeleeMesh,bCatalogExport?FString():ColdSteelMeleeRune::Selected(Item),Item.Definition);}
    const auto Parts=Staff?ColdSteelStaffAssembly::Components(MeleeMesh):ColdSteelModularSword::Components(MeleeMesh);
    const FBox Local=Staff?ColdSteelStaffAssembly::Bounds(MeleeMesh):ColdSteelModularSword::LocalBounds(MeleeMesh);
    FQuat Portrait=ColdSteelMeleePreview::Rotation(Local,true);
    if(Item.Definition==TEXT("ue_tactical_hatchet"))
    {
        // Turn the broad cheek toward a three-quarter view. The camera looks along X;
        // Y is canvas width and Z is the grip axis. Cap the turn so the blade face reads.
        const FVector Extent=Local.TransformBy(FTransform(Portrait)).GetSize();
        const double TargetWidth=.255*Extent.Z;
        if(Extent.Y>TargetWidth)
        {
            const double Diagonal=FMath::Sqrt(Extent.X*Extent.X+Extent.Y*Extent.Y);
            const double Angle=FMath::Atan2(Extent.X,Extent.Y)+FMath::Acos(TargetWidth/Diagonal);
            Portrait=FQuat(FVector::UpVector,FMath::Min(Angle,FMath::DegreesToRadians(65.0)))*Portrait;
        }
    }
    MeleeMesh->SetWorldTransform(ColdSteelMeleePreview::Pose(Local,Portrait));
    Capture->ShowOnlyComponents.Reset();for(auto* Part:Parts)Capture->ShowOnlyComponent(Part);
    FBox Bounds=Local.TransformBy(MeleeMesh->GetComponentTransform());
    if(Item.Definition==TEXT("ue_tactical_hatchet"))
    {
        // Use each fitted part's bounds, including the lanyard. Rotating one large
        // assembly AABB would frame empty corners between the head and handle.
        FBox Fitted(ForceInit);
        for(const UStaticMeshComponent* Part:Parts)
            if(const UStaticMesh* Mesh=Part->GetStaticMesh())
                Fitted+=Mesh->GetBoundingBox().TransformBy(Part->GetComponentTransform());
        if(Fitted.IsValid)Bounds=Fitted;
    }
    const FVector Size=Bounds.GetSize(),Center=Bounds.GetCenter();
    // Staffs and single-hand blades retain their own inventory aspect. The
    // kukri is 1x3 (256x768), rather than the two-handed sword's 384x768 canvas.
    const bool FootprintCanvas=Staff||ColdSteelInventory::IsOneHandedMelee(Item);
    const FIntPoint Grid=ColdSteelInventory::BaseFootprint(Item);
    const int32 Width=FootprintCanvas?FMath::Max(256,FMath::RoundToInt(320.f*float(Grid.X)/FMath::Max(1,Grid.Y))):384;
    const int32 Height=FootprintCanvas?FMath::Max(320,FMath::RoundToInt(float(Width)*Grid.Y/FMath::Max(1,Grid.X))):768;
    if(Target->SizeX!=Width||Target->SizeY!=Height)Target->ResizeTarget(Width,Height);
    const float Aspect=float(Width)/Height;
    Capture->SetWorldLocation(FVector(Bounds.Min.X-200,Center.Y,Center.Z));Capture->SetWorldRotation(FRotator::ZeroRotator);
    Capture->OrthoWidth=FMath::Max(float(Size.Y),float(Size.Z)*Aspect)/.91f;
    Capture->bAutoCalculateOrthoPlanes=false;Capture->bUseCustomProjectionMatrix=true;
    Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(Capture->OrthoWidth*.5f,Capture->OrthoWidth*.5f/Aspect,1.f/2000.f,-.1f);
    CaptureMeshes.Reset();CaptureMaterials.Reset();CaptureTextures.Reset();
    for(auto* Part:Parts)
    {
        CaptureMeshes.Add(Part);
        for(auto* Material:Part->GetMaterials())if(Material)CaptureMaterials.AddUnique(Material);
        for(int32 Slot=0;Slot<Part->GetNumMaterials();++Slot)if(auto* Overlay=Part->GetOverlayMaterial(true,Slot))CaptureMaterials.AddUnique(Overlay);
    }
    for(UMaterialInterface* Material:CaptureMaterials)
    {
        TArray<UTexture*> UsedTextures;Material->GetUsedTextures(UsedTextures);
        for(auto* Texture:UsedTextures)if(Texture)CaptureTextures.AddUnique(Texture);
    }
    RequestCaptureTextureMips();Studio->GetWorld()->SendAllEndOfFrameUpdates();
    return true;
}
