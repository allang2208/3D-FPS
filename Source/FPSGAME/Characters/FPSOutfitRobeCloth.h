#pragma once
class USkeletalMeshComponent;
namespace FPSOutfitRobeCloth
{
    void Initialize(USkeletalMeshComponent* Garment,USkeletalMeshComponent* PoseSource);
    void Update(USkeletalMeshComponent* Garment,float DeltaSeconds);
}
