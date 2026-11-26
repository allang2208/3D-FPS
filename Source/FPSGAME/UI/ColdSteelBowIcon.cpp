#include "ColdSteelWeaponIcons.h"
#include "ColdSteelMeleePreview.h"
#include "../Weapons/Bow/BowAssembly.h"
#include "Engine/World.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/Texture.h"
#include "Materials/MaterialInterface.h"

bool UColdSteelWeaponIcons::PrepareBow(const FColdSteelItem& I)
{
    if(!BowMesh)
    {
        BowMesh=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
        BowMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Studio->AddComponent(BowMesh,FTransform::Identity);
    }
    if(!ColdSteelBowAssembly::Apply(BowMesh,I))return false;
    const bool bCompound=SupersampleBowIcon(I);
    FQuat View=ColdSteelBowAssembly::Rotation();
    if(bCompound)View=FQuat(FVector::RightVector,FMath::DegreesToRadians(-13.0))*View;
    BowMesh->SetWorldTransform(ColdSteelMeleePreview::Pose(ColdSteelBowAssembly::LocalBounds(BowMesh),View));
    const auto Pieces=ColdSteelBowAssembly::Components(BowMesh);
    FBox Bounds(ForceInit);
    Capture->ShowOnlyComponents.Reset();
    for(auto* Piece:Pieces)
    {
        Capture->ShowOnlyComponent(Piece);
        Bounds+=Piece->CalcBounds(Piece->GetComponentTransform()).GetBox();
    }
    if(!Bounds.IsValid)return false;
    const FVector Size=Bounds.GetSize(),Center=Bounds.GetCenter();
    const FIntPoint Grid=ColdSteelInventory::BaseFootprint(I);
    const int32 Scale=bCompound?2:1;
    const int32 Height=320*Scale,Width=Scale*FMath::Max(256,FMath::RoundToInt(320.f*float(Grid.X)/FMath::Max(1,Grid.Y)));
    if(Target->SizeX!=Width||Target->SizeY!=Height)Target->ResizeTarget(Width,Height);
    const float Aspect=float(Width)/Height;
    Capture->SetWorldLocation(FVector(Bounds.Min.X-200,Center.Y,Center.Z));Capture->SetWorldRotation(FRotator::ZeroRotator);
    Capture->OrthoWidth=FMath::Max(float(Size.Y),float(Size.Z)*Aspect)/(bCompound?.94f:.91f);
    Capture->bAutoCalculateOrthoPlanes=false;Capture->bUseCustomProjectionMatrix=true;
    Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(Capture->OrthoWidth*.5f,Capture->OrthoWidth*.5f/Aspect,1.f/2000.f,-.1f);
    CaptureMeshes.Reset();CaptureMaterials.Reset();CaptureTextures.Reset();
    for(auto* C:Pieces)
    {
        CaptureMeshes.Add(C);for(auto* M:C->GetMaterials())if(M)CaptureMaterials.AddUnique(M);
    }
    for(UMaterialInterface* M:CaptureMaterials)
    {
        TArray<UTexture*> Used;M->GetUsedTextures(Used);for(auto* T:Used)if(T)CaptureTextures.AddUnique(T);
    }
    RequestCaptureTextureMips();Studio->GetWorld()->SendAllEndOfFrameUpdates();return true;
}
