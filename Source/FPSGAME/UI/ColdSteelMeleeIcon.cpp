#include "ColdSteelWeaponIcons.h"
#include "ColdSteelMeleePreview.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/Texture.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"

bool UColdSteelWeaponIcons::PrepareMelee(const FColdSteelItem& Item)
{
    const FString Path=ColdSteelMeleePreview::MeshPath(Item);
    auto* Asset=Path.IsEmpty()?nullptr:LoadObject<UStaticMesh>(nullptr,*Path);
    if(!Asset)return false;
    if(!MeleeMesh)
    {
        MeleeMesh=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
        MeleeMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);MeleeMesh->SetForcedLodModel(1);
        Studio->AddComponent(MeleeMesh,FTransform::Identity);
    }
    MeleeMesh->EmptyOverrideMaterials();MeleeMesh->SetStaticMesh(Asset);
    MeleeMesh->SetWorldTransform(ColdSteelMeleePreview::Pose(*Asset,ColdSteelMeleePreview::Rotation(*Asset,true)));
    Capture->ShowOnlyComponents.Reset();Capture->ShowOnlyComponent(MeleeMesh);
    const FBox Bounds=Asset->GetBoundingBox().TransformBy(MeleeMesh->GetComponentTransform());
    const FVector Size=Bounds.GetSize(),Center=Bounds.GetCenter();
    constexpr int32 Width=384,Height=768;
    if(Target->SizeX!=Width||Target->SizeY!=Height)Target->ResizeTarget(Width,Height);
    const float Aspect=float(Width)/Height;
    Capture->SetWorldLocation(FVector(Bounds.Min.X-200,Center.Y,Center.Z));Capture->SetWorldRotation(FRotator::ZeroRotator);
    Capture->OrthoWidth=FMath::Max(float(Size.Y),float(Size.Z)*Aspect)/.91f;
    Capture->bAutoCalculateOrthoPlanes=false;Capture->bUseCustomProjectionMatrix=true;
    Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(Capture->OrthoWidth*.5f,Capture->OrthoWidth*.5f/Aspect,1.f/2000.f,-.1f);
    CaptureMeshes.Reset();CaptureMaterials.Reset();CaptureTextures.Reset();CaptureMeshes.Add(MeleeMesh);
    for(auto* Material:MeleeMesh->GetMaterials())if(Material)CaptureMaterials.AddUnique(Material);
    for(UMaterialInterface* Material:CaptureMaterials)
    {
        TArray<UTexture*> UsedTextures;Material->GetUsedTextures(UsedTextures);
        for(auto* Texture:UsedTextures)if(Texture){CaptureTextures.AddUnique(Texture);Texture->SetForceMipLevelsToBeResident(12.f);}
    }
    MeleeMesh->PrestreamTextures(12.f,true);Studio->GetWorld()->SendAllEndOfFrameUpdates();
    return true;
}
