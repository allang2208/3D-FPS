#include "ColdSteelPickup.h"
#include "../Building/VoxelBuildPalette.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

bool AColdSteelPickup::BuildVoxelBlock(const FColdSteelItem& Item)
{
    // Voxel blocks are the only drop that reuses the building palette entry: the piece on the ground is
    // exactly the 20 cm cube the player builds with, same mesh and same surface.
    static const FString Prefix(TEXT("voxel_block_"));
    if(!Item.Definition.StartsWith(Prefix))return false;
    const FString MaterialId=Item.Definition.RightChop(Prefix.Len());
    auto* Palette=LoadObject<UVoxelBuildPalette>(nullptr,
        TEXT("/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette.DA_VoxelBuildPalette"));
    UStaticMesh* Asset=nullptr;UMaterialInterface* Surface=nullptr;
    if(Palette)if(const FVoxelBuildMaterial* Entry=Palette->Find(FName(*MaterialId)))
    {
        Asset=Entry->ExampleMesh.LoadSynchronous();
        Surface=Entry->Surface.LoadSynchronous();
    }
    if(!Asset)Asset=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Building/Voxels/Rounded/SM_Voxel20_Stone.SM_Voxel20_Stone"));
    if(!Asset)return false;
    bVoxelBlock=true;SetActorTickInterval(.15f);
    Body->SetSimulatePhysics(false);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Mesh->SetStaticMesh(Asset);if(Surface)Mesh->SetMaterial(0,Surface);
    const FBoxSphereBounds Bounds=Asset->GetBounds();
    Mesh->SetRelativeScale3D(FVector(1.f));Mesh->SetRelativeLocation(-Bounds.Origin);
    Body->SetBoxExtent(Bounds.BoxExtent.ComponentMax(FVector(4.f)));
    Body->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    Body->SetCollisionResponseToChannel(ECC_PhysicsBody,ECR_Ignore);
    Body->SetLinearDamping(.6f);Body->SetAngularDamping(2.f);
    Body->SetSimulatePhysics(true);
    return true;
}
