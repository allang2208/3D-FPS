#pragma once
#include "CoreMinimal.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

// Measured on the authored Soviet rifle after the uniform fit in build.py.
// WPN_root inherits the FBX 100x scale; these coordinates remain in metres.
// FBX converts Blender local Y to -Y. See sight_landmarks.json / ue_sights.json.
namespace AKMSoviet
{
inline const FVector Front(.0008, .5575537682, .0968115032);
inline const FVector Rear(.0007595263, .1704100072, .1019900516);
inline const FVector Muzzle(.0008, .5802467465, .0508882552);
inline bool Matches(const USkeletalMeshComponent* Mesh)
{
    return Mesh && Mesh->GetSkeletalMeshAsset() && Mesh->GetSkeletalMeshAsset()->GetPathName().Contains(TEXT("/AKMIntegration/SovietFab/"));
}
}
