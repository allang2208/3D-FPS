#include "ColdSteelWeaponIcons.h"
#include "FPSPerformanceMetrics.h"
#include "Engine/GameInstance.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "ColdSteelMeleePreview.h"
#include "../Weapons/MeleeRuneVisual.h"
#include "../Weapons/ModularSwordVisual.h"
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
    const bool Modular=ColdSteelModularSword::Supports(Item);
    const FString Path=Modular?FString():ColdSteelMeleePreview::MeshPath(Item);
    auto* Asset=Path.IsEmpty()?nullptr:LoadObject<UStaticMesh>(nullptr,*Path);
    if(!Modular&&!Asset)return false;
    if(!MeleeMesh)
    {
        MeleeMesh=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
        MeleeMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);MeleeMesh->SetForcedLodModel(1);
        Studio->AddComponent(MeleeMesh,FTransform::Identity);
    }
    if(Modular){if(!ColdSteelModularSword::Apply(MeleeMesh,Item,nullptr,!bCatalogExport))return false;}
    else {ColdSteelModularSword::Clear(MeleeMesh);MeleeMesh->EmptyOverrideMaterials();MeleeMesh->SetStaticMesh(Asset);ColdSteelMeleeRune::Apply(MeleeMesh,bCatalogExport?FString():ColdSteelMeleeRune::Selected(Item),Item.Definition);}
    const FBox Local=ColdSteelModularSword::LocalBounds(MeleeMesh);
    MeleeMesh->SetWorldTransform(ColdSteelMeleePreview::Pose(Local,ColdSteelMeleePreview::Rotation(Local,true)));
    Capture->ShowOnlyComponents.Reset();for(auto* Part:ColdSteelModularSword::Components(MeleeMesh))Capture->ShowOnlyComponent(Part);
    const FBox Bounds=Local.TransformBy(MeleeMesh->GetComponentTransform());
    const FVector Size=Bounds.GetSize(),Center=Bounds.GetCenter();
    constexpr int32 Width=384,Height=768;
    if(Target->SizeX!=Width||Target->SizeY!=Height)Target->ResizeTarget(Width,Height);
    const float Aspect=float(Width)/Height;
    Capture->SetWorldLocation(FVector(Bounds.Min.X-200,Center.Y,Center.Z));Capture->SetWorldRotation(FRotator::ZeroRotator);
    Capture->OrthoWidth=FMath::Max(float(Size.Y),float(Size.Z)*Aspect)/.91f;
    Capture->bAutoCalculateOrthoPlanes=false;Capture->bUseCustomProjectionMatrix=true;
    Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(Capture->OrthoWidth*.5f,Capture->OrthoWidth*.5f/Aspect,1.f/2000.f,-.1f);
    CaptureMeshes.Reset();CaptureMaterials.Reset();CaptureTextures.Reset();
    for(auto* Part:ColdSteelModularSword::Components(MeleeMesh))
    {
        CaptureMeshes.Add(Part);
        for(auto* Material:Part->GetMaterials())if(Material)CaptureMaterials.AddUnique(Material);
        for(int32 Slot=0;Slot<Part->GetNumMaterials();++Slot)if(auto* Overlay=Part->GetOverlayMaterial(true,Slot))CaptureMaterials.AddUnique(Overlay);
        Part->PrestreamTextures(12.f,true);
    }
    for(UMaterialInterface* Material:CaptureMaterials)
    {
        TArray<UTexture*> UsedTextures;Material->GetUsedTextures(UsedTextures);
        for(auto* Texture:UsedTextures)if(Texture){CaptureTextures.AddUnique(Texture);Texture->SetForceMipLevelsToBeResident(12.f);}
    }
    MeleeMesh->PrestreamTextures(12.f,true);Studio->GetWorld()->SendAllEndOfFrameUpdates();
    return true;
}
