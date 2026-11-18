#pragma once
#include "BlindSupplicantAuthoring.h"

#include "Dom/JsonObject.h"
#include "Engine/SkeletalMesh.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

#if WITH_EDITOR
#include "WitchRebuiltClothingAsset.h"
#include "M07InteractingClothingAsset.h"
#include "M07MembraneClothingAsset.h"
#include "ClothingAssetFactory.h"
#include "ChaosCloth/ChaosClothConfig.h"
#include "Math/RotationMatrix.h"
#include "Misc/FileHelper.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Rendering/SkeletalMeshModel.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"
#endif

namespace BlindSupplicantCloth
{
FString WriteGillReceipt(const TSharedRef<FJsonObject>& Receipt);
#if WITH_EDITOR
constexpr int32 GillCount = 6;
// Shared by authoring and receipt generation; preserve the original tolerance.
constexpr double ManifestMatchToleranceCm = 1.0;
struct FGillPanelManifest
{
    FString Id;
    TArray<FVector3f> VerticesCm;
    TArray<float> MaxDistanceCm;
};

struct FGillCapsuleManifest
{
    FName Bone;
    FVector A;
    FVector B;
    FVector ReferenceA;
    FVector ReferenceB;
    bool bReferenceEndpoints = false;
    float RadiusCm = 0.f;
};

struct FGillDraft
{
    TStrongObjectPtr<UWitchRebuiltClothingAsset> Asset;
    TArray<float> Distances;
    int32 PinnedVertices = 0;
    float MaxDistanceCm = 0.f;
    double MaxMatchErrorCm = 0.0;
};

bool ReadGillManifest(const FString& Filename,TArray<FGillPanelManifest>& Panels,TArray<FGillCapsuleManifest>& Capsules,FString& Error,int32 ExpectedPanels=GillCount);
TArray<int32> GillSections(USkeletalMesh* Mesh,const FString& Slot);
FString GillAssetName(int32 PanelIndex);
bool MapGillDistances(const FGillPanelManifest& Panel,FGillDraft& Draft,FString& Error);
UPhysicsAsset* MakeGillCollision(USkeletalMesh* Mesh,const TArray<FGillCapsuleManifest>& Capsules);
void ConfigureGill(FGillDraft& Draft,UPhysicsAsset* Collision,UChaosClothSharedSimConfig* Shared);
FString BuildContinuousGillCloth(USkeletalMesh* Mesh,USkeletalMesh* SimulationSource,const FString& ManifestFile);
#endif
}
