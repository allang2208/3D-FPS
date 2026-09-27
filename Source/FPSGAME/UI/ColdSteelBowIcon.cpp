#include "ColdSteelWeaponIcons.h"
#include "ColdSteelMeleePreview.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/Bow/BowAssembly.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/Texture.h"
#include "Materials/MaterialInterface.h"

bool UColdSteelWeaponIcons::PrepareBow(const FColdSteelItem& Item)
{
    const FGunsmithParts Factory;
    const auto I=GetGameInstance()->GetSubsystem<UGunsmithSystem>()->ResolveBowVisual(Item,bCatalogExport?&Factory:nullptr);
    if(!BowMesh)
    {
        BowMesh=NewObject<UStaticMeshComponent>(GetTransientPackage(),NAME_None,RF_Transient);
        BowMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Studio->AddComponent(BowMesh,FTransform::Identity);
    }
    if(!ColdSteelBowAssembly::Apply(BowMesh,I))return false;
    const FBox Local=ColdSteelBowAssembly::LocalBounds(BowMesh);
    BowMesh->SetWorldTransform(ColdSteelMeleePreview::Pose(Local,ColdSteelBowAssembly::Rotation()));
    Capture->ShowOnlyComponents.Reset();for(auto* C:ColdSteelBowAssembly::Components(BowMesh))Capture->ShowOnlyComponent(C);
    const FBox Bounds=Local.TransformBy(BowMesh->GetComponentTransform());const FVector Size=Bounds.GetSize(),Center=Bounds.GetCenter();
    const FIntPoint Grid=ColdSteelInventory::BaseFootprint(I);const int32 Width=FMath::Max(256,FMath::RoundToInt(320.f*float(Grid.X)/FMath::Max(1,Grid.Y))),Height=320;
    if(Target->SizeX!=Width||Target->SizeY!=Height)Target->ResizeTarget(Width,Height);
    const float Aspect=float(Width)/Height;
    Capture->SetWorldLocation(FVector(Bounds.Min.X-200,Center.Y,Center.Z));Capture->SetWorldRotation(FRotator::ZeroRotator);
    Capture->OrthoWidth=FMath::Max(float(Size.Y),float(Size.Z)*Aspect)/.91f;
    Capture->bAutoCalculateOrthoPlanes=false;Capture->bUseCustomProjectionMatrix=true;
    Capture->CustomProjectionMatrix=FReversedZOrthoMatrix(Capture->OrthoWidth*.5f,Capture->OrthoWidth*.5f/Aspect,1.f/2000.f,-.1f);
    CaptureMeshes.Reset();CaptureMaterials.Reset();CaptureTextures.Reset();
    for(auto* C:ColdSteelBowAssembly::Components(BowMesh))
    {
        CaptureMeshes.Add(C);for(auto* M:C->GetMaterials())if(M)CaptureMaterials.AddUnique(M);
    }
    for(UMaterialInterface* M:CaptureMaterials)
    {
        TArray<UTexture*> Used;M->GetUsedTextures(Used);for(auto* T:Used)if(T)CaptureTextures.AddUnique(T);
    }
    RequestCaptureTextureMips();Studio->GetWorld()->SendAllEndOfFrameUpdates();return true;
}
