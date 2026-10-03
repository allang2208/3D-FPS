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

namespace
{
FString WriteGillReceipt(const TSharedRef<FJsonObject>& Receipt)
{
    FString Result;
    const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Result);
    FJsonSerializer::Serialize(Receipt, Writer);
    return Result;
}

#if WITH_EDITOR
constexpr int32 GillCount = 6;
// Both arrays describe the same exported proxy; this allowance is for FBX
// welding and float precision, never for guessing scale or coordinate axes.
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

bool ReadCmVector(const TSharedPtr<FJsonValue>& Value, FVector& Out)
{
    if (!Value || Value->Type != EJson::Array) return false;
    const auto& Values = Value->AsArray();
    if (Values.Num() != 3) return false;
    double Components[3];
    for (int32 Index = 0; Index < 3; ++Index)
        if (!Values[Index] || !Values[Index]->TryGetNumber(Components[Index]) || !FMath::IsFinite(Components[Index])) return false;
    Out = FVector(Components[0], Components[1], Components[2]);
    return !Out.ContainsNaN();
}

bool ReadGillManifest(const FString& Filename, TArray<FGillPanelManifest>& Panels,
    TArray<FGillCapsuleManifest>& Capsules, FString& Error, int32 ExpectedPanels = GillCount)
{
    FString Text;
    if (!FFileHelper::LoadFileToString(Text, *Filename))
    {
        Error = TEXT("Cannot read the gill weight manifest.");
        return false;
    }
    TSharedPtr<FJsonObject> Manifest;
    if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Manifest) || !Manifest)
    {
        Error = TEXT("The gill weight manifest is not a JSON object.");
        return false;
    }
    const TArray<TSharedPtr<FJsonValue>>* PanelValues = nullptr;
    if (!Manifest->TryGetArrayField(TEXT("panels"), PanelValues) || PanelValues->Num() != ExpectedPanels)
    {
        Error = TEXT("The manifest panel count does not match the selected cloth authoring route.");
        return false;
    }
    Panels.SetNum(ExpectedPanels);
    for (const auto& Value : *PanelValues)
    {
        const auto Panel = Value && Value->Type == EJson::Object ? Value->AsObject() : nullptr;
        FString Id;
        if (!Panel || !Panel->TryGetStringField(TEXT("id"), Id))
        {
            Error = TEXT("A panel is missing its string id.");
            return false;
        }
        int32 PanelIndex = INDEX_NONE;
        for (int32 Index = 0; Index < ExpectedPanels; ++Index)
            if (Id == FString::Printf(TEXT("%02d"), Index + 1)) PanelIndex = Index;
        if (PanelIndex == INDEX_NONE || !Panels[PanelIndex].Id.IsEmpty())
        {
            Error = FString::Printf(TEXT("Unknown or duplicate panel id: %s."), *Id);
            return false;
        }
        auto& Output = Panels[PanelIndex];
        Output.Id = Id;
        const TArray<TSharedPtr<FJsonValue>>* Vertices = nullptr;
        const TArray<TSharedPtr<FJsonValue>>* Distances = nullptr;
        if (!Panel->TryGetArrayField(TEXT("vertices_cm"), Vertices) ||
            !Panel->TryGetArrayField(TEXT("max_distance_cm"), Distances) ||
            Vertices->Num() < 3 || Vertices->Num() != Distances->Num())
        {
            Error = FString::Printf(TEXT("Panel %s has missing or unequal vertex/MaxDistance arrays."), *Id);
            return false;
        }
        for (int32 Index = 0; Index < Vertices->Num(); ++Index)
        {
            FVector Vertex;
            double Distance = 0.0;
            if (!ReadCmVector((*Vertices)[Index], Vertex) ||
                !(*Distances)[Index] || !(*Distances)[Index]->TryGetNumber(Distance) ||
                !FMath::IsFinite(Distance) || Distance < 0.0 || Distance > MAX_flt)
            {
                Error = FString::Printf(TEXT("Panel %s contains an invalid vertex or nonnegative MaxDistance value at %d."), *Id, Index);
                return false;
            }
            const FVector3f VertexFloat(Vertex);
            if (VertexFloat.ContainsNaN())
            {
                Error = FString::Printf(TEXT("Panel %s contains a vertex outside the float coordinate range."), *Id);
                return false;
            }
            Output.VerticesCm.Add(VertexFloat);
            Output.MaxDistanceCm.Add(static_cast<float>(Distance));
        }
    }
    const TArray<TSharedPtr<FJsonValue>>* CapsuleValues = nullptr;
    if (!Manifest->TryGetArrayField(TEXT("collision_capsules"), CapsuleValues) || CapsuleValues->IsEmpty())
    {
        Error = TEXT("The manifest must provide body collision capsules in bone-local centimeters.");
        return false;
    }
    for (const auto& Value : *CapsuleValues)
    {
        const auto Capsule = Value && Value->Type == EJson::Object ? Value->AsObject() : nullptr;
        FString Bone;
        double Radius = 0.0;
        FGillCapsuleManifest Output;
        if (!Capsule || !Capsule->TryGetStringField(TEXT("bone"), Bone) || Bone.IsEmpty() ||
            !Capsule->HasField(TEXT("a_cm")) || !ReadCmVector(Capsule->TryGetField(TEXT("a_cm")), Output.A) ||
            !Capsule->HasField(TEXT("b_cm")) || !ReadCmVector(Capsule->TryGetField(TEXT("b_cm")), Output.B) ||
            !Capsule->TryGetNumberField(TEXT("radius_cm"), Radius) || !FMath::IsFinite(Radius) || Radius <= 0.0 || Radius > MAX_flt)
        {
            Error = TEXT("A collision capsule has invalid bone-local endpoints or radius.");
            return false;
        }
        Output.Bone = FName(*Bone);
        Output.RadiusCm = static_cast<float>(Radius);
        if (Capsule->HasField(TEXT("a_reference_cm")) || Capsule->HasField(TEXT("b_reference_cm")))
        {
            if (!ReadCmVector(Capsule->TryGetField(TEXT("a_reference_cm")), Output.ReferenceA) ||
                !ReadCmVector(Capsule->TryGetField(TEXT("b_reference_cm")), Output.ReferenceB))
            {
                Error = TEXT("A collision capsule has invalid mesh-reference centimeter endpoints.");
                return false;
            }
            Output.bReferenceEndpoints = true;
        }
        Capsules.Add(Output);
    }
    return true;
}

TArray<int32> GillSections(USkeletalMesh* Mesh, const FString& Slot)
{
    TArray<int32> Found;
    const FName Name(*Slot);
    const auto& Materials = Mesh->GetMaterials();
    const auto& Sections = Mesh->GetImportedModel()->LODModels[0].Sections;
    for (int32 Index = 0; Index < Sections.Num(); ++Index)
    {
        if (!Materials.IsValidIndex(Sections[Index].MaterialIndex)) continue;
        const auto& Material = Materials[Sections[Index].MaterialIndex];
        if (Material.ImportedMaterialSlotName == Name || Material.MaterialSlotName == Name) Found.Add(Index);
    }
    return Found;
}

FString GillAssetName(int32 PanelIndex)
{
    return FString::Printf(TEXT("M07_GillCloth_%02d"), PanelIndex + 1);
}

bool MapGillDistances(const FGillPanelManifest& Panel, FGillDraft& Draft, FString& Error)
{
    const auto& Physical = Draft.Asset->LodData[0].PhysicalMeshData;
    if (Physical.Vertices.Num() < 3 || Physical.Indices.Num() < 3 || Physical.Indices.Num() % 3 != 0)
    {
        Error = FString::Printf(TEXT("Panel %s has no usable simulation triangles."), *Panel.Id);
        return false;
    }
    Draft.Distances.SetNum(Physical.Vertices.Num());
    for (int32 Index = 0; Index < Physical.Vertices.Num(); ++Index)
    {
        const FVector3f Vertex = Physical.Vertices[Index];
        if (Vertex.ContainsNaN())
        {
            Error = FString::Printf(TEXT("Panel %s contains an invalid imported simulation vertex."), *Panel.Id);
            return false;
        }
        int32 Nearest = INDEX_NONE;
        double BestDistanceSquared = TNumericLimits<double>::Max();
        for (int32 Source = 0; Source < Panel.VerticesCm.Num(); ++Source)
        {
            const double DistanceSquared = FVector::DistSquared(FVector(Vertex), FVector(Panel.VerticesCm[Source]));
            if (DistanceSquared < BestDistanceSquared)
            {
                BestDistanceSquared = DistanceSquared;
                Nearest = Source;
            }
        }
        const double MatchError = FMath::Sqrt(BestDistanceSquared);
        if (Nearest == INDEX_NONE || MatchError > ManifestMatchToleranceCm)
        {
            Error = FString::Printf(TEXT("Panel %s simulation vertex %d is %.4f cm from the manifest; export mesh-reference UE centimeters."),
                *Panel.Id, Index, MatchError);
            return false;
        }
        const float Distance = Panel.MaxDistanceCm[Nearest];
        Draft.Distances[Index] = Distance;
        Draft.PinnedVertices += Distance == 0.f;
        Draft.MaxDistanceCm = FMath::Max(Draft.MaxDistanceCm, Distance);
        Draft.MaxMatchErrorCm = FMath::Max(Draft.MaxMatchErrorCm, MatchError);
    }
    if (Draft.PinnedVertices == 0 || Draft.PinnedVertices == Draft.Distances.Num())
    {
        Error = FString::Printf(TEXT("Panel %s must contain both fixed attachment vertices and movable membrane vertices."), *Panel.Id);
        return false;
    }
    return true;
}

UPhysicsAsset* MakeGillCollision(USkeletalMesh* Mesh, const TArray<FGillCapsuleManifest>& Capsules)
{
    auto* Collision = NewObject<UPhysicsAsset>(Mesh,
        MakeUniqueObjectName(Mesh, UPhysicsAsset::StaticClass(), TEXT("M07_GillBodyCollision")), RF_Transactional);
    TMap<FName, USkeletalBodySetup*> Bodies;
    const auto& Reference = Mesh->GetRefSkeleton();
    TArray<FTransform> Frames = Reference.GetRefBonePose();
    for (int32 Bone = 0; Bone < Frames.Num(); ++Bone)
        if (Reference.GetParentIndex(Bone) >= 0) Frames[Bone] *= Frames[Reference.GetParentIndex(Bone)];
    for (const auto& Capsule : Capsules)
    {
        USkeletalBodySetup* Body = Bodies.FindRef(Capsule.Bone);
        if (!Body)
        {
            Body = NewObject<USkeletalBodySetup>(Collision, NAME_None, RF_Transactional);
            Body->BoneName = Capsule.Bone;
            Bodies.Add(Capsule.Bone, Body);
            Collision->SkeletalBodySetups.Add(Body);
        }
        // V12 uses actual original-body reference endpoints. Resolve them
        // against the IMPORTED frame so FBX bone post rotations and unit scale
        // cannot rotate or shrink a cloth collider. Older manifests remain
        // bone-local and must not be transformed twice.
        FVector A = Capsule.A, B = Capsule.B;
        double Radius = Capsule.RadiusCm;
        if (Capsule.bReferenceEndpoints)
        {
            const auto& Frame = Frames[Reference.FindBoneIndex(Capsule.Bone)];
            A = Frame.InverseTransformPosition(Capsule.ReferenceA);
            B = Frame.InverseTransformPosition(Capsule.ReferenceB);
            Radius /= Frame.GetScale3D().GetAbsMax();
            Body->PhysicsType = PhysType_Kinematic;
            Body->DefaultInstance.SetCollisionProfileName(TEXT("NoCollision"));
        }
        FKSphylElem Shape;
        Shape.Center = (A + B) * 0.5;
        Shape.Rotation = FRotationMatrix::MakeFromZ((B - A).GetSafeNormal(SMALL_NUMBER, FVector::ZAxisVector)).Rotator();
        Shape.Radius = Radius;
        Shape.Length = static_cast<float>((B - A).Size());
        Body->AggGeom.SphylElems.Add(Shape);
    }
    Collision->UpdateBodySetupIndexMap();
    Collision->SetPreviewMesh(Mesh, false);
    return Collision;
}

void ConfigureGill(FGillDraft& Draft, UPhysicsAsset* Collision, UChaosClothSharedSimConfig* Shared)
{
    auto* Cloth = Draft.Asset.Get();
    Cloth->Modify();
    Cloth->PhysicsAsset = Collision;
    auto& Lod = Cloth->LodData[0];
    Lod.bUseMultipleInfluences = false;
    Lod.bSmoothTransition = true;
    Lod.PointWeightMaps.Reset();
    FPointWeightMap Distance(Draft.Distances.Num());
    Distance.Name = TEXT("M07_AuthoredGillAttachmentAndTravelCm");
    Distance.bEnabled = true;
    Distance.CurrentTarget = static_cast<uint8>(EWeightMapTargetCommon::MaxDistance);
    for (int32 Index = 0; Index < Draft.Distances.Num(); ++Index) Distance[Index] = Draft.Distances[Index];
    Lod.PointWeightMaps.Add(MoveTemp(Distance));

    auto* Config = NewObject<UChaosClothConfig>(Cloth,
        MakeUniqueObjectName(Cloth, UChaosClothConfig::StaticClass(), TEXT("M07_GillMembraneChaosConfig")), RF_Transactional);
    Config->Density = 0.2f;
    Config->EdgeStiffnessWeighted = {0.96f, 0.96f};
    Config->AreaStiffnessWeighted = {0.96f, 0.96f};
    Config->bUseBendingElements = true;
    Config->BendingStiffnessWeighted = {0.12f, 0.12f};
    Config->BucklingRatio = 0.6f;
    Config->BucklingStiffnessWeighted = {0.08f, 0.08f};
    Config->TetherStiffness = {1.f, 1.f};
    Config->TetherScale = {1.f, 1.f};
    Config->bUseGeodesicDistance = true;
    Config->AnimDriveStiffness = {0.12f, 0.12f};
    Config->AnimDriveDamping = {0.25f, 0.25f};
    Config->DampingCoefficient = 0.055f;
    Config->LocalDampingCoefficient = 0.3f;
    Config->CollisionThickness = 0.6f;
    Config->FrictionCoefficient = 0.25f;
    Config->bUseCCD = true;
    Config->bUseSelfCollisions = false;
    Config->bUseSelfCollisionSpheres = false;
    Config->Drag = {0.025f, 0.025f};
    Config->Lift = {0.01f, 0.01f};
    Config->Pressure = {0.f, 0.f};
    Config->LinearVelocityScale = FVector(0.45);
    Config->AngularVelocityScale = 0.35f;
    Cloth->ClothConfigs.Reset();
    Cloth->ClothConfigs.Add(Config->GetClass()->GetFName(), Config);
    Cloth->ClothConfigs.Add(Shared->GetClass()->GetFName(), Shared);
    Cloth->ApplyParameterMasks(true);
    Cloth->InvalidateAllCachedData();
}

FString BuildContinuousGillCloth(USkeletalMesh* Mesh, USkeletalMesh* SimulationSource, const FString& ManifestFile)
{
    auto Receipt = MakeShared<FJsonObject>();
    Receipt->SetBoolField(TEXT("success"), false);
    Receipt->SetBoolField(TEXT("saved"), false);
    Receipt->SetBoolField(TEXT("tested"), false);
    const bool bAnatomyV03 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_AnatomyV03");
    const bool bAnatomyV04 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_AnatomyV04");
    const bool bAnatomyV05 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_AnatomyV05");
    const bool bOriginalV06 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV06");
    const bool bOriginalV07 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV07");
    const bool bOriginalV08 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV08");
    const bool bOriginalV09 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV09");
    const bool bOriginalV11 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV11");
    const bool bOriginalV12 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV12");
    // V16 changes only arm skin, and keeps the V13 collision/source/solver policy.
    const bool bOriginalV13 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV13") ||
        Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_ArmSweepV16") ||
        Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_LegJointsV17") ||
        Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18");
    const bool bBodyMotionV18 = Mesh->GetOutermost()->GetName() == TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18");
    Receipt->SetStringField(TEXT("source_revision"), bBodyMotionV18 ? TEXT("original_v18_body_motion_local_leaf_clearance_and_14_contacts") : bOriginalV13 ? TEXT("original_v13_leg_skin_attack_recovery_and_bounded_low_cost_gills") : bOriginalV12 ? TEXT("original_v11_surface_v12_arm_driven_gill_collision") : bOriginalV11 ? TEXT("original_hands_arms_repair_v11_retained_gills_v09") : bOriginalV09 ? TEXT("original_gill_local_repair_v09") : bOriginalV08 ? TEXT("original_biped_legs_human_hands_layered_gills_v08") : bOriginalV07 ? TEXT("original_anatomical_hands_hindlegs_layered_gills_v07") : bOriginalV06 ? TEXT("original_mesh_display_and_six_proxy_islands_v06") : bAnatomyV05 ? TEXT("continuous_gills_complete_anatomy_v05") : bAnatomyV04 ? TEXT("continuous_gills_reference_v04") :
        bAnatomyV03 ? TEXT("continuous_gills_anatomy_v03") : TEXT("continuous_gills_v02"));
    auto Fail = [&](const FString& Error)
    {
        Receipt->SetStringField(TEXT("error"), Error);
        return WriteGillReceipt(Receipt);
    };
    if (!Mesh->GetImportedModel() || Mesh->GetImportedModel()->LODModels.IsEmpty() ||
        !SimulationSource->GetImportedModel() || SimulationSource->GetImportedModel()->LODModels.IsEmpty())
        return Fail(TEXT("The continuous display and simulation source require imported LOD0 data."));
    const auto Display = GillSections(Mesh, TEXT("M07_Gills"));
    const auto Proxy = GillSections(SimulationSource, TEXT("M07_GillSimulation"));
    if (Display.Num() != 1 || Proxy.Num() != 1)
        return Fail(TEXT("The six continuous membranes require one shared display section and one shared physical source section."));
    UE_LOG(LogTemp, Display, TEXT("M07_AUTHOR_INPUT_FRAMES display_root=%s source_root=%s display_bounds=%s source_bounds=%s"),
        *Mesh->GetRefSkeleton().GetRefBonePose()[0].ToHumanReadableString(),
        *SimulationSource->GetRefSkeleton().GetRefBonePose()[0].ToHumanReadableString(),
        *Mesh->GetBounds().BoxExtent.ToString(), *SimulationSource->GetBounds().BoxExtent.ToString());
    if (!Mesh->GetRefSkeleton().GetRefBonePose()[0].GetScale3D().Equals(
        SimulationSource->GetRefSkeleton().GetRefBonePose()[0].GetScale3D(), .001))
        return Fail(TEXT("The display and physical source have different imported root units; import the continuous display into a fresh package before cloth authoring."));
    TArray<FGillPanelManifest> Panels;
    TArray<FGillCapsuleManifest> Capsules;
    FString Error;
    if (!ReadGillManifest(ManifestFile, Panels, Capsules, Error)) return Fail(Error);
    for (const auto& Capsule : Capsules)
        if (Mesh->GetRefSkeleton().FindBoneIndex(Capsule.Bone) == INDEX_NONE)
            return Fail(TEXT("A continuous-source body collision bone is absent from the display skeleton."));

    TStrongObjectPtr<UClothingAssetFactory> Factory(NewObject<UClothingAssetFactory>());
    FSkeletalMeshClothBuildParams Params;
    Params.AssetName = TEXT("M07_ContinuousSixGillPhysicalSource");
    Params.LodIndex = 0;
    Params.SourceSection = Proxy[0];
    Params.bRemoveFromMesh = false;
    TStrongObjectPtr<UClothingAssetCommon> Extracted(Cast<UClothingAssetCommon>(Factory->CreateFromSkeletalMesh(SimulationSource, Params)));
    if (!Extracted.IsValid() || Extracted->LodData.Num() != 1)
        return Fail(TEXT("The complete six-island physical source could not be extracted."));
    auto* Cloth = NewObject<UM07InteractingClothingAsset>(Mesh,
        MakeUniqueObjectName(Mesh, UM07InteractingClothingAsset::StaticClass(), bBodyMotionV18 ? TEXT("M07_OriginalGills_V18") : bOriginalV13 ? TEXT("M07_OriginalGills_V13") : bOriginalV12 ? TEXT("M07_OriginalGills_V12") : bOriginalV11 ? TEXT("M07_OriginalGills_V11") : bOriginalV09 ? TEXT("M07_OriginalGills_V09") : bOriginalV08 ? TEXT("M07_OriginalGills_V08") : bOriginalV07 ? TEXT("M07_OriginalGills_V07") : bOriginalV06 ? TEXT("M07_OriginalGills_V06") : bAnatomyV05 ? TEXT("M07_ContinuousGills_V05") : bAnatomyV04 ? TEXT("M07_ContinuousGills_V04") :
            bAnatomyV03 ? TEXT("M07_ContinuousGills_V03") : TEXT("M07_ContinuousGills_V02")), RF_Transactional);
    Cloth->InitializeSimulationFrom(Extracted.Get());
    FGillDraft Draft;
    Draft.Asset.Reset(Cloth);
    auto& Physical = Cloth->LodData[0].PhysicalMeshData;
    Draft.Distances.SetNum(Physical.Vertices.Num());
    Physical.VertexColors.SetNum(Physical.Vertices.Num());
    double MaximumMatchErrorCm = 0.0;
    TArray<int32> PanelVertices;
    PanelVertices.Init(0, GillCount);
    // Use the native factory's whole-mesh particle and bone numbering. The
    // authoring manifest supplies distance masks and anatomical island IDs;
    // it never reconstructs or manually offsets runtime particle indices.
    for (int32 Vertex = 0; Vertex < Physical.Vertices.Num(); ++Vertex)
    {
        double BestSquared = TNumericLimits<double>::Max();
        int32 BestPanel = INDEX_NONE, BestPoint = INDEX_NONE;
        for (int32 Panel = 0; Panel < Panels.Num(); ++Panel)
            for (int32 Point = 0; Point < Panels[Panel].VerticesCm.Num(); ++Point)
            {
                const double Squared = FVector::DistSquared(FVector(Physical.Vertices[Vertex]), FVector(Panels[Panel].VerticesCm[Point]));
                if (Squared < BestSquared)
                {
                    BestSquared = Squared;
                    BestPanel = Panel;
                    BestPoint = Point;
                }
            }
        if (BestPoint == INDEX_NONE || BestSquared > FMath::Square(ManifestMatchToleranceCm))
            return Fail(TEXT("A physical vertex has no corresponding continuous-sheet authoring input."));
        const float Distance = Panels[BestPanel].MaxDistanceCm[BestPoint];
        Draft.Distances[Vertex] = Distance;
        Draft.PinnedVertices += Distance <= 0.f;
        Draft.MaxDistanceCm = FMath::Max(Draft.MaxDistanceCm, Distance);
        MaximumMatchErrorCm = FMath::Max(MaximumMatchErrorCm, FMath::Sqrt(BestSquared));
        ++PanelVertices[BestPanel];
        Physical.VertexColors[Vertex] = FColor(255, 255, BestPanel + 1, 255);
    }
    // Body authoring accounts for the imported root/bone scale when writing
    // local capsule dimensions. Reuse that centimeter-correct anatomy instead
    // of assigning manifest centimeter radii directly to scaled bones.
    auto* Collision = Mesh->GetPhysicsAsset();
    const FString CollisionPackage = bOriginalV13 ? TEXT("/Game/Monsters/BlindSupplicantM07/PA_M07_OriginalV13") : bOriginalV12 ? TEXT("/Game/Monsters/BlindSupplicantM07/PA_M07_OriginalV12") : bOriginalV11 ? TEXT("/Game/Monsters/BlindSupplicantM07/PA_M07_OriginalV11") : bOriginalV09 ? TEXT("/Game/Monsters/BlindSupplicantM07/PA_M07_OriginalV09") : bOriginalV08 ? TEXT("/Game/Monsters/BlindSupplicantM07/PA_M07_OriginalV08") : bOriginalV07 ? TEXT("/Game/Monsters/BlindSupplicantM07/PA_M07_OriginalV07") : bOriginalV06 ? TEXT("/Game/Monsters/BlindSupplicantM07/PA_M07_OriginalV06") : bAnatomyV05 ? TEXT("/Game/Monsters/BlindSupplicantM07/PA_M07_V05") : bAnatomyV04 ? TEXT("/Game/Monsters/BlindSupplicantM07/PA_M07_V04") : TEXT("/Game/Monsters/BlindSupplicantM07/PA_M07");
    if (!Collision || Collision->GetOutermost()->GetName() != CollisionPackage)
        return Fail(TEXT("Author the M07 body physics in the matching mesh reference frame before its cloth."));
    if (bOriginalV12 || bOriginalV13)
    {
        // Animated hand/finger shapes push cloth without adding tiny ragdoll
        // bodies or making animation bones block against a Character capsule.
        for (const auto& Capsule : Capsules)
            if (!Capsule.bReferenceEndpoints)
                return Fail(TEXT("V12 cloth collision requires mesh-reference endpoints from the retained V11 body."));
        Collision = MakeGillCollision(Mesh, Capsules);
    }
    auto* Shared = NewObject<UChaosClothSharedSimConfig>(Mesh,
        MakeUniqueObjectName(Mesh, UChaosClothSharedSimConfig::StaticClass(), TEXT("M07_ContinuousGillSharedConfig")), RF_Transactional);
    Shared->IterationCount = bOriginalV13 ? 4 : bOriginalV12 ? 7 : 6;
    Shared->MaxIterationCount = bOriginalV13 ? 6 : bOriginalV12 ? 10 : 8;
    Shared->SubdivisionCount = bOriginalV12 ? 3 : 1;
    Shared->bUseLocalSpaceSimulation = true;
    ConfigureGill(Draft, Collision, Shared);
    auto* Config = Cloth->GetClothConfig<UChaosClothConfig>();
    Config->bUseSelfCollisions = true;
    Config->SelfCollisionThickness = (bOriginalV07 || bOriginalV08 || bOriginalV09 || bOriginalV11 || bOriginalV12) ? 0.8f : 1.0f;
    Config->SelfCollisionFriction = 0.1f;
    Config->AnimDriveStiffness = {0.28f, 0.28f};
    if (bOriginalV12)
    {
        Config->CollisionThickness = 0.9f;
        Config->FrictionCoefficient = 0.16f;
        Config->AnimDriveStiffness = {0.045f, 0.045f};
        Config->AnimDriveDamping = {0.12f, 0.12f};
        Config->DampingCoefficient = 0.07f;
        Config->LocalDampingCoefficient = 0.25f;
        Config->TetherScale = {1.025f, 1.025f};
        Config->LinearVelocityScale = FVector(0.55);
        Config->AngularVelocityScale = 0.45f;
        Config->bUseCCD = true;
    }
    if (bOriginalV13)
    {
        // Adopt the settled Witch approach: body collision plus sparse sphere
        // repulsion, without particle/face self collision on folded sheets.
        Config->bUseSelfCollisions = false;
        Config->bUseSelfCollisionSpheres = true;
        Config->SelfCollisionSphereRadius = 1.2f;
        Config->SelfCollisionSphereRadiusCullMultiplier = 2.f;
        Config->SelfCollisionSphereStiffness = .8f;
        Config->CollisionThickness = 1.f;
        Config->FrictionCoefficient = .16f;
        Config->AnimDriveStiffness = {.12f, .12f};
        Config->AnimDriveDamping = {.15f, .15f};
        Config->DampingCoefficient = .04f;
        Config->LocalDampingCoefficient = .2f;
        Config->TetherScale = {1.01f, 1.01f};
        Config->LinearVelocityScale = FVector(.65);
        Config->AngularVelocityScale = .55f;
        Config->bUseCCD = true;
    }
    if (bBodyMotionV18)
    {
        // Same bounded solver as V13. Contact coverage and kinematic clearance
        // improve first; never multiply substeps to compensate for bad binding.
        Shared->IterationCount = 4;
        Shared->MaxIterationCount = 6;
        Shared->SubdivisionCount = 1;
        Config->AnimDriveStiffness = {.07f, .07f};
        Config->AnimDriveDamping = {.15f, .15f};
        Config->SelfCollisionSphereRadiusCullMultiplier = 3.f;
        Config->LinearVelocityScale = FVector(.55);
        Config->AngularVelocityScale = .45f;
    }
    Cloth->RefreshBoneMapping(Mesh);
    Cloth->CalculateReferenceBoneIndex();
    Cloth->InvalidateAllCachedData();
    FScopedSkeletalMeshPostEditChange Change(Mesh);
    Mesh->Modify();
    const auto Previous = Mesh->GetMeshClothingAssets();
    for (UClothingAssetBase* Asset : Previous)
        if (Asset) Asset->UnbindFromSkeletalMesh(Mesh, INDEX_NONE, INDEX_NONE);
    Mesh->SetMeshClothingAssets({Cloth});
    if (!Cloth->BindToSkeletalMesh(Mesh, 0, Display[0], 0))
        return Fail(TEXT("The continuous membrane display could not be bound to its complete physical mesh."));
    auto& Lod = Mesh->GetImportedModel()->LODModels[0];
    auto& Section = Lod.Sections[Display[0]];
    auto& User = Lod.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
    User.CorrespondClothAssetIndex = Section.CorrespondClothAssetIndex = 0;
    User.ClothingData = Section.ClothingData;
    User.bDisabled = Section.bDisabled = false;
    int32 CapturedVertices = 0, SkinVertices = 0;
    if (!Section.ClothMappingDataLODs.IsEmpty())
        for (const auto& Mapping : Section.ClothMappingDataLODs[0])
            if (Mapping.SourceMeshVertIndices[3] == 0xffff) ++SkinVertices;
            else ++CapturedVertices;
    if (CapturedVertices == 0)
        return Fail(TEXT("The continuous cloth capture produced no cloth-driven display vertices."));
    Mesh->InvalidateDeriveDataCacheGUID();
    Mesh->MarkPackageDirty();
    Receipt->SetBoolField(TEXT("success"), true);
    Receipt->SetBoolField(TEXT("caller_must_save_package"), true);
    Receipt->SetBoolField(TEXT("inter_panel_collision"), true);
    Receipt->SetStringField(TEXT("cloth_asset"), Cloth->GetPathName());
    Receipt->SetStringField(TEXT("collision_asset"), Collision->GetPathName());
    Receipt->SetNumberField(TEXT("collision_capsules"), Capsules.Num());
    Receipt->SetNumberField(TEXT("solver_substeps"), Shared->SubdivisionCount);
    Receipt->SetNumberField(TEXT("solver_iterations"), Shared->IterationCount);
    Receipt->SetNumberField(TEXT("solver_max_iterations"), Shared->MaxIterationCount);
    Receipt->SetBoolField(TEXT("bounded_leaf_bone_clearance"), bBodyMotionV18);
    Receipt->SetBoolField(TEXT("particle_face_self_collision"), Config->bUseSelfCollisions);
    Receipt->SetBoolField(TEXT("sphere_self_repulsion"), Config->bUseSelfCollisionSpheres);
    Receipt->SetNumberField(TEXT("collision_thickness_cm"), Config->CollisionThickness);
    Receipt->SetNumberField(TEXT("anim_drive_stiffness"), Config->AnimDriveStiffness.Low);
    Receipt->SetBoolField(TEXT("dedicated_animated_arm_palm_finger_collision"), bOriginalV12 || bOriginalV13);
    Receipt->SetStringField(TEXT("reference_bone"), Mesh->GetRefSkeleton().GetBoneName(Cloth->ReferenceBoneIndex).ToString());
    Receipt->SetNumberField(TEXT("display_panels"), GillCount);
    Receipt->SetNumberField(TEXT("display_sections"), 1);
    Receipt->SetStringField(TEXT("mesh_root_reference_scale"), Mesh->GetRefSkeleton().GetRefBonePose()[0].GetScale3D().ToString());
    Receipt->SetStringField(TEXT("display_bounds_extent_cm"), Mesh->GetBounds().BoxExtent.ToString());
    Receipt->SetNumberField(TEXT("cloth_captured_display_vertices"), CapturedVertices);
    Receipt->SetNumberField(TEXT("skin_only_display_vertices"), SkinVertices);
    Receipt->SetNumberField(TEXT("simulation_vertices"), Physical.Vertices.Num());
    Receipt->SetNumberField(TEXT("simulation_triangles"), Physical.Indices.Num() / 3);
    Receipt->SetNumberField(TEXT("pinned_vertices"), Draft.PinnedVertices);
    Receipt->SetNumberField(TEXT("max_distance_cm"), Draft.MaxDistanceCm);
    Receipt->SetNumberField(TEXT("max_manifest_match_error_cm"), MaximumMatchErrorCm);
    return WriteGillReceipt(Receipt);
}
#endif
}

FString UBlindSupplicantAuthoring::BuildGillCloth(USkeletalMesh* Mesh, const FString& WeightManifestFile, bool bExtractSimulation)
{
    const TSharedRef<FJsonObject> Receipt = MakeShared<FJsonObject>();
    Receipt->SetBoolField(TEXT("success"), false);
    Receipt->SetStringField(TEXT("mesh"), Mesh ? Mesh->GetPathName() : FString());
    Receipt->SetBoolField(TEXT("extract_simulation"), bExtractSimulation);
    Receipt->SetBoolField(TEXT("saved"), false);
    Receipt->SetBoolField(TEXT("tested"), false);
    Receipt->SetBoolField(TEXT("inter_panel_collision"), false);
    Receipt->SetStringField(TEXT("collision_boundary"), TEXT("Six separate cloth assets collide with the supplied body capsules; panel-to-panel collision is not provided. Author static panel clearance in the source mesh."));
    bool bChanged = false;
    auto Fail = [&](const FString& Stage, const FString& Error)
    {
        Receipt->SetStringField(TEXT("stage"), Stage);
        Receipt->SetStringField(TEXT("error"), Error);
        Receipt->SetBoolField(TEXT("mesh_changed"), bChanged);
        return WriteGillReceipt(Receipt);
    };
#if WITH_EDITOR
    if (!Mesh || !Mesh->GetOutermost()->GetName().StartsWith(TEXT("/Game/Monsters/BlindSupplicantM07/")))
        return Fail(TEXT("scope"), TEXT("Only skeletal meshes inside /Game/Monsters/BlindSupplicantM07/ can be authored."));
    if (!IsInGameThread()) return Fail(TEXT("thread"), TEXT("Invoke this authoring function on the editor/commandlet game thread."));
    auto* Model = Mesh->GetImportedModel();
    if (!Model || Model->LODModels.IsEmpty()) return Fail(TEXT("mesh"), TEXT("The mesh has no imported LOD0 model."));

    TArray<FGillPanelManifest> Panels;
    TArray<FGillCapsuleManifest> Capsules;
    FString Error;
    if (!ReadGillManifest(WeightManifestFile, Panels, Capsules, Error)) return Fail(TEXT("manifest"), Error);
    for (const auto& Capsule : Capsules)
        if (Mesh->GetRefSkeleton().FindBoneIndex(Capsule.Bone) == INDEX_NONE)
            return Fail(TEXT("collision_bone"), FString::Printf(TEXT("Collision bone %s is absent from this mesh's skeleton."), *Capsule.Bone.ToString()));

    TArray<FGillDraft> Drafts;
    Drafts.SetNum(GillCount);
    const auto PreviousAssets = Mesh->GetMeshClothingAssets();
    for (UClothingAssetBase* Asset : PreviousAssets)
    {
        int32 PanelIndex = INDEX_NONE;
        if (Asset && Asset->GetOuter() == Mesh)
            for (int32 Index = 0; Index < GillCount; ++Index)
            {
                const FString Base = GillAssetName(Index);
                if (Asset->GetName() == Base || Asset->GetName().StartsWith(Base + TEXT("_"))) PanelIndex = Index;
            }
        auto* Gill = Cast<UWitchRebuiltClothingAsset>(Asset);
        if (PanelIndex == INDEX_NONE || !Gill || Drafts[PanelIndex].Asset.IsValid())
            return Fail(TEXT("existing_cloth"), TEXT("The mesh contains unknown, external or duplicate cloth assets; they have been left unchanged."));
        Drafts[PanelIndex].Asset.Reset(Gill);
    }

    for (int32 Index = 0; Index < GillCount; ++Index)
    {
        const FString DisplaySlot = TEXT("M07_Gill_") + Panels[Index].Id;
        const auto Display = GillSections(Mesh, DisplaySlot);
        if (Display.Num() != 1)
            return Fail(TEXT("display_section"), FString::Printf(TEXT("Expected one LOD0 section for material slot %s; found %d."), *DisplaySlot, Display.Num()));
        if (bExtractSimulation)
        {
            const FString ProxySlot = TEXT("M07_GillSimulationProxy_") + Panels[Index].Id;
            const auto Proxy = GillSections(Mesh, ProxySlot);
            if (Proxy.Num() != 1 || Model->LODModels[0].Sections[Proxy[0]].HasClothingData())
                return Fail(TEXT("proxy_section"), FString::Printf(TEXT("Expected one unbound LOD0 section for material slot %s."), *ProxySlot));
        }
        else if (!Drafts[Index].Asset.IsValid() || Drafts[Index].Asset->LodData.IsEmpty())
            return Fail(TEXT("saved_cloth"), FString::Printf(TEXT("No saved simulation asset for panel %s; extract the ClothBuildSource mesh first."), *Panels[Index].Id));
    }

    if (bExtractSimulation)
    {
        TStrongObjectPtr<UClothingAssetFactory> Factory(NewObject<UClothingAssetFactory>());
        for (int32 Index = 0; Index < GillCount; ++Index)
        {
            FSkeletalMeshClothBuildParams Params;
            Params.AssetName = GillAssetName(Index) + TEXT("_Extract");
            Params.LodIndex = 0;
            Params.SourceSection = GillSections(Mesh, TEXT("M07_GillSimulationProxy_") + Panels[Index].Id)[0];
            // Stage all six simulations and manifest maps before removing any
            // render sections, so malformed input leaves the source geometry.
            Params.bRemoveFromMesh = false;
            TStrongObjectPtr<UClothingAssetCommon> Extracted(Cast<UClothingAssetCommon>(Factory->CreateFromSkeletalMesh(Mesh, Params)));
            if (!Extracted.IsValid() || Extracted->LodData.IsEmpty())
                return Fail(TEXT("extraction"), FString::Printf(TEXT("Cannot extract the simulation proxy for panel %s."), *Panels[Index].Id));
            auto* Cloth = NewObject<UWitchRebuiltClothingAsset>(Mesh,
                MakeUniqueObjectName(Mesh, UWitchRebuiltClothingAsset::StaticClass(), FName(*GillAssetName(Index))), RF_Transactional);
            Cloth->InitializeSimulationFrom(Extracted.Get());
            Drafts[Index].Asset.Reset(Cloth);
        }
    }
    for (int32 Index = 0; Index < GillCount; ++Index)
        if (!MapGillDistances(Panels[Index], Drafts[Index], Error)) return Fail(TEXT("weight_mapping"), Error);

    FScopedSkeletalMeshPostEditChange Change(Mesh);
    Mesh->Modify();
    bChanged = true;
    for (UClothingAssetBase* Asset : PreviousAssets) Asset->UnbindFromSkeletalMesh(Mesh, INDEX_NONE, INDEX_NONE);
    Mesh->SetMeshClothingAssets({});
    if (bExtractSimulation)
    {
        TArray<int32> Proxies;
        for (const auto& Panel : Panels)
            Proxies.Add(GillSections(Mesh, TEXT("M07_GillSimulationProxy_") + Panel.Id)[0]);
        Proxies.Sort([](int32 A, int32 B) { return A > B; });
        for (const int32 SectionIndex : Proxies) Mesh->RemoveMeshSection(0, SectionIndex);
    }

    auto* Collision = MakeGillCollision(Mesh, Capsules);
    auto* Shared = NewObject<UChaosClothSharedSimConfig>(Mesh,
        MakeUniqueObjectName(Mesh, UChaosClothSharedSimConfig::StaticClass(), TEXT("M07_GillChaosSharedConfig")), RF_Transactional);
    Shared->IterationCount = 4;
    Shared->MaxIterationCount = 6;
    Shared->SubdivisionCount = 1;
    Shared->bUseLocalSpaceSimulation = true;
    for (auto& Draft : Drafts)
    {
        ConfigureGill(Draft, Collision, Shared);
        Draft.Asset->RefreshBoneMapping(Mesh);
        Mesh->AddClothingAsset(Draft.Asset.Get());
    }

    TArray<TSharedPtr<FJsonValue>> PanelReceipts;
    for (int32 Index = 0; Index < GillCount; ++Index)
    {
        auto* Cloth = Drafts[Index].Asset.Get();
        const auto RenderSections = GillSections(Mesh, TEXT("M07_Gill_") + Panels[Index].Id);
        if (RenderSections.Num() != 1 || !Cloth->BindToSkeletalMesh(Mesh, 0, RenderSections[0], 0))
            return Fail(TEXT("binding"), FString::Printf(TEXT("Cannot bind saved simulation to the display section for panel %s."), *Panels[Index].Id));
        const int32 Render = RenderSections[0];
        auto& Lod = Mesh->GetImportedModel()->LODModels[0];
        auto& Section = Lod.Sections[Render];
        Section.bDisabled = false;
        auto& User = Lod.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
        User.bDisabled = false;
        User.CorrespondClothAssetIndex = Index;
        User.ClothingData.AssetGuid = Cloth->GetAssetGuid();
        User.ClothingData.AssetLodIndex = 0;

        const TSharedRef<FJsonObject> Item = MakeShared<FJsonObject>();
        Item->SetStringField(TEXT("id"), Panels[Index].Id);
        Item->SetStringField(TEXT("cloth_asset"), Cloth->GetPathName());
        Item->SetNumberField(TEXT("display_section"), Render);
        Item->SetNumberField(TEXT("simulation_vertices"), Drafts[Index].Distances.Num());
        Item->SetNumberField(TEXT("simulation_triangles"), Cloth->LodData[0].PhysicalMeshData.Indices.Num() / 3);
        Item->SetNumberField(TEXT("pinned_vertices"), Drafts[Index].PinnedVertices);
        Item->SetNumberField(TEXT("max_distance_cm"), Drafts[Index].MaxDistanceCm);
        Item->SetNumberField(TEXT("max_manifest_match_error_cm"), Drafts[Index].MaxMatchErrorCm);
        PanelReceipts.Add(MakeShared<FJsonValueObject>(Item));
    }
    Mesh->InvalidateDeriveDataCacheGUID();
    Mesh->MarkPackageDirty();
    Receipt->SetBoolField(TEXT("success"), true);
    Receipt->SetBoolField(TEXT("mesh_changed"), true);
    Receipt->SetStringField(TEXT("stage"), TEXT("authored"));
    Receipt->SetStringField(TEXT("package"), Mesh->GetOutermost()->GetName());
    Receipt->SetStringField(TEXT("collision_asset"), Collision->GetPathName());
    Receipt->SetNumberField(TEXT("collision_capsules"), Capsules.Num());
    Receipt->SetNumberField(TEXT("proxy_sections_removed"), bExtractSimulation ? GillCount : 0);
    Receipt->SetNumberField(TEXT("manifest_match_tolerance_cm"), ManifestMatchToleranceCm);
    Receipt->SetBoolField(TEXT("caller_must_save_package"), true);
    Receipt->SetArrayField(TEXT("panels"), PanelReceipts);
    return WriteGillReceipt(Receipt);
#else
    return Fail(TEXT("editor_only"), TEXT("Gill cloth authoring requires an Editor or commandlet build."));
#endif
}

FString UBlindSupplicantAuthoring::BuildInteractingGillCloth(USkeletalMesh* Mesh, const FString& WeightManifestFile)
{
    auto Receipt = MakeShared<FJsonObject>();
    Receipt->SetBoolField(TEXT("success"), false);
    Receipt->SetBoolField(TEXT("saved"), false);
    Receipt->SetBoolField(TEXT("tested"), false);
    auto Fail = [&](const FString& Error)
    {
        Receipt->SetStringField(TEXT("error"), Error);
        return WriteGillReceipt(Receipt);
    };
#if WITH_EDITOR
    if (!Mesh || Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07"))
        return Fail(TEXT("Only the saved M07 display mesh may be authored."));
    const auto Previous = Mesh->GetMeshClothingAssets();
    if (Previous.Num() == 1 && Cast<UM07InteractingClothingAsset>(Previous[0]))
    {
        Receipt->SetBoolField(TEXT("success"), true);
        Receipt->SetBoolField(TEXT("inter_panel_collision"), true);
        Receipt->SetBoolField(TEXT("caller_must_save_package"), true);
        Receipt->SetStringField(TEXT("cloth_asset"), Previous[0]->GetPathName());
        return WriteGillReceipt(Receipt);
    }
    TArray<FGillPanelManifest> Panels;
    TArray<FGillCapsuleManifest> Capsules;
    FString Error;
    if (!ReadGillManifest(WeightManifestFile, Panels, Capsules, Error)) return Fail(Error);
    TArray<FGillDraft> Parts;
    Parts.SetNum(GillCount);
    if (Previous.Num() != GillCount) return Fail(TEXT("The six original saved simulations are required."));
    for (const auto& Base : Previous)
    {
        auto* Part = Cast<UWitchRebuiltClothingAsset>(Base.Get());
        if (!Part || Part->LodData.Num() != 1) return Fail(TEXT("An original gill simulation is unavailable."));
        int32 Id = INDEX_NONE;
        for (int32 Index = 0; Index < GillCount; ++Index)
            if (Part->GetName().StartsWith(GillAssetName(Index))) Id = Index;
        if (Id == INDEX_NONE || Parts[Id].Asset.IsValid()) return Fail(TEXT("The original gill identities must be unique."));
        Parts[Id].Asset.Reset(Part);
    }
    int32 VertexCount = 0, IndexCount = 0;
    TArray<int32> Offsets, Sections;
    for (int32 Index = 0; Index < GillCount; ++Index)
    {
        if (!Parts[Index].Asset.IsValid() || !MapGillDistances(Panels[Index], Parts[Index], Error)) return Fail(Error);
        const auto Render = GillSections(Mesh, TEXT("M07_Gill_") + Panels[Index].Id);
        if (Render.Num() != 1) return Fail(TEXT("Each gill display panel requires one saved section."));
        const auto& Section = Mesh->GetImportedModel()->LODModels[0].Sections[Render[0]];
        if (Section.ClothingData.AssetGuid != Parts[Index].Asset->GetAssetGuid() || Section.ClothMappingDataLODs.IsEmpty())
            return Fail(TEXT("Each original display-to-simulation mapping must already be authored."));
        Offsets.Add(VertexCount);
        Sections.Add(Render[0]);
        const auto& Physical = Parts[Index].Asset->LodData[0].PhysicalMeshData;
        VertexCount += Physical.Vertices.Num();
        IndexCount += Physical.Indices.Num();
    }
    // Reuse the six existing low-density islands and their exact display
    // captures. They remain disconnected anatomically, but share one solver
    // particle set, so triangle self-collision includes neighbouring panels.
    TStrongObjectPtr<UClothingAssetCommon> CombinedSource(NewObject<UClothingAssetCommon>());
    CombinedSource->LodData.AddDefaulted();
    auto& Physical = CombinedSource->LodData[0].PhysicalMeshData;
    Physical.Reset(VertexCount, IndexCount);
    FGillDraft Combined;
    int32 TriangleIndex = 0;
    for (int32 PartIndex = 0; PartIndex < GillCount; ++PartIndex)
    {
        auto* Source = Parts[PartIndex].Asset.Get();
        const auto& Input = Source->LodData[0].PhysicalMeshData;
        const int32 Offset = Offsets[PartIndex];
        for (int32 Index = 0; Index < Input.Vertices.Num(); ++Index)
        {
            Physical.Vertices[Offset + Index] = Input.Vertices[Index];
            Physical.Normals[Offset + Index] = Input.Normals[Index];
            Physical.VertexColors[Offset + Index] = Input.VertexColors.IsValidIndex(Index) ? Input.VertexColors[Index] : FColor::White;
            auto BoneData = Input.BoneData[Index];
            for (int32 Influence = 0; Influence < FClothVertBoneData::MaxTotalInfluences; ++Influence)
            {
                if (BoneData.BoneWeights[Influence] <= 0.f) continue;
                const int32 BoneIndex = BoneData.BoneIndices[Influence];
                if (!Source->UsedBoneNames.IsValidIndex(BoneIndex)) return Fail(TEXT("An original simulation influence has no named bone."));
                BoneData.BoneIndices[Influence] = CombinedSource->UsedBoneNames.AddUnique(Source->UsedBoneNames[BoneIndex]);
            }
            Physical.BoneData[Offset + Index] = BoneData;
        }
        for (uint32 Index : Input.Indices) Physical.Indices[TriangleIndex++] = Index + Offset;
        Combined.Distances.Append(Parts[PartIndex].Distances);
        Combined.PinnedVertices += Parts[PartIndex].PinnedVertices;
        Combined.MaxDistanceCm = FMath::Max(Combined.MaxDistanceCm, Parts[PartIndex].MaxDistanceCm);
    }
    Physical.CalculateNumInfluences();
    auto* Cloth = NewObject<UM07InteractingClothingAsset>(Mesh,
        MakeUniqueObjectName(Mesh, UM07InteractingClothingAsset::StaticClass(), TEXT("M07_InteractingGills")), RF_Transactional);
    Cloth->InitializeSimulationFrom(CombinedSource.Get());
    Cloth->PanelVertexOffsets = Offsets;
    for (int32 Index = 0; Index < GillCount; ++Index)
    {
        auto& Panel = Cloth->PanelSimulations.Add_GetRef(Parts[Index].Asset->LodData[0].PhysicalMeshData);
        for (int32 Vertex = 0; Vertex < Panel.BoneData.Num(); ++Vertex)
            Panel.BoneData[Vertex] = Cloth->LodData[0].PhysicalMeshData.BoneData[Offsets[Index] + Vertex];
        Cloth->PanelMaterialSlots.Add(FName(*(TEXT("M07_Gill_") + Panels[Index].Id)));
    }
    Combined.Asset.Reset(Cloth);
    auto* Shared = NewObject<UChaosClothSharedSimConfig>(Mesh,
        MakeUniqueObjectName(Mesh, UChaosClothSharedSimConfig::StaticClass(), TEXT("M07_InteractingGillsShared")), RF_Transactional);
    Shared->IterationCount = 6;
    Shared->MaxIterationCount = 8;
    Shared->SubdivisionCount = 1;
    Shared->bUseLocalSpaceSimulation = true;
    auto* Collision = MakeGillCollision(Mesh, Capsules);
    ConfigureGill(Combined, Collision, Shared);
    auto* Config = Cloth->GetClothConfig<UChaosClothConfig>();
    Config->bUseSelfCollisions = true;
    Config->SelfCollisionThickness = 1.0f;
    Config->SelfCollisionFriction = 0.1f;
    Config->AnimDriveStiffness = {0.28f, 0.28f};
    Cloth->RefreshBoneMapping(Mesh);
    Cloth->CalculateReferenceBoneIndex();
    Cloth->LodMap = {0};
    Cloth->InvalidateAllCachedData();

    FScopedSkeletalMeshPostEditChange Change(Mesh);
    Mesh->Modify();
    // No high-detail mesh recapture is needed: existing section captures are
    // local indices into each island. Offset only the three particle indices;
    // the fourth index stores skinning/fixed-vertex flags and is preserved.
    auto& Lod = Mesh->GetImportedModel()->LODModels[0];
    for (int32 Index = 0; Index < GillCount; ++Index)
    {
        auto& Section = Lod.Sections[Sections[Index]];
        for (auto& MappingLod : Section.ClothMappingDataLODs)
            for (auto& Mapping : MappingLod)
                for (int32 Corner = 0; Corner < 3; ++Corner)
                    Mapping.SourceMeshVertIndices[Corner] += Offsets[Index];
        Section.CorrespondClothAssetIndex = 0;
        Section.ClothingData.AssetGuid = Cloth->GetAssetGuid();
        Section.ClothingData.AssetLodIndex = 0;
        auto& User = Lod.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
        User.CorrespondClothAssetIndex = 0;
        User.ClothingData = Section.ClothingData;
        User.bDisabled = false;
        Section.bDisabled = false;
    }
    Mesh->SetMeshClothingAssets({Cloth});
    Mesh->InvalidateDeriveDataCacheGUID();
    Mesh->MarkPackageDirty();
    Receipt->SetBoolField(TEXT("success"), true);
    Receipt->SetBoolField(TEXT("inter_panel_collision"), true);
    Receipt->SetBoolField(TEXT("caller_must_save_package"), true);
    Receipt->SetStringField(TEXT("cloth_asset"), Cloth->GetPathName());
    Receipt->SetStringField(TEXT("collision_asset"), Collision->GetPathName());
    Receipt->SetNumberField(TEXT("display_panels"), GillCount);
    Receipt->SetNumberField(TEXT("simulation_vertices"), VertexCount);
    Receipt->SetNumberField(TEXT("simulation_triangles"), IndexCount / 3);
    Receipt->SetNumberField(TEXT("pinned_vertices"), Combined.PinnedVertices);
    Receipt->SetNumberField(TEXT("self_collision_thickness_cm"), Config->SelfCollisionThickness);
    return WriteGillReceipt(Receipt);
#else
    return Fail(TEXT("Editor authoring build required."));
#endif
}

FString UBlindSupplicantAuthoring::RemoveGillClothForReimport(USkeletalMesh* Mesh)
{
#if WITH_EDITOR
    if (!Mesh || (Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV12") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV13") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_ArmSweepV16") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_LegJointsV17") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18")) ||
        !Mesh->GetImportedModel() || Mesh->GetImportedModel()->LODModels.IsEmpty())
        return TEXT("{\"success\":false,\"error\":\"Only this task's imported M07 display may be detached.\"}");
    FScopedSkeletalMeshPostEditChange Change(Mesh);
    Mesh->Modify();
    const auto Previous = Mesh->GetMeshClothingAssets();
    for (UClothingAssetBase* Asset : Previous)
        if (Asset) Asset->UnbindFromSkeletalMesh(Mesh, INDEX_NONE, INDEX_NONE);
    Mesh->SetMeshClothingAssets({});
    for (auto& Lod : Mesh->GetImportedModel()->LODModels)
        for (auto& Section : Lod.Sections)
        {
            Section.ClothingData.AssetGuid.Invalidate();
            Section.ClothingData.AssetLodIndex = INDEX_NONE;
            Section.CorrespondClothAssetIndex = INDEX_NONE;
            Section.ClothMappingDataLODs.Reset();
            auto& User = Lod.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
            User.ClothingData = Section.ClothingData;
            User.CorrespondClothAssetIndex = INDEX_NONE;
        }
    Mesh->InvalidateDeriveDataCacheGUID();
    Mesh->MarkPackageDirty();
    return TEXT("{\"success\":true,\"saved\":false,\"stage\":\"detached_for_geometry_reimport\"}");
#else
    return TEXT("{\"success\":false,\"error\":\"Editor authoring build required.\"}");
#endif
}

FString UBlindSupplicantAuthoring::BuildWitchStyleMembrane(USkeletalMesh* Mesh, USkeletalMesh* SimulationSource,
    UClothingAssetCommon* ReferenceCloth, const FString& WeightManifestFile)
{
#if WITH_EDITOR
    auto Receipt=MakeShared<FJsonObject>();Receipt->SetBoolField(TEXT("success"),false);
    auto Fail=[&](const FString& Error){Receipt->SetStringField(TEXT("error"),Error);return WriteGillReceipt(Receipt);};
    if(!Mesh || Mesh->GetOutermost()->GetName()!=TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18") ||
        !SimulationSource || !SimulationSource->GetImportedModel() || SimulationSource->GetImportedModel()->LODModels.IsEmpty() ||
        !ReferenceCloth || !ReferenceCloth->GetOutermost()->GetName().StartsWith(TEXT("/Game/Monsters/WitchRebuilt/")))
        return Fail(TEXT("M07 display/proxy and current Witch cloth reference are required."));
    const auto Proxy=GillSections(SimulationSource,TEXT("M07_GillSimulation"));
    if(Proxy.Num()!=1)return Fail(TEXT("The two continuous sheets must share one hidden proxy section."));
    TArray<FGillPanelManifest> Panels;TArray<FGillCapsuleManifest> Capsules;FString Error;
    if(!ReadGillManifest(WeightManifestFile,Panels,Capsules,Error,2))return Fail(Error);
    for(const auto& Capsule:Capsules)
        if(Mesh->GetRefSkeleton().FindBoneIndex(Capsule.Bone)==INDEX_NONE)return Fail(TEXT("A membrane collider bone is missing."));
    UChaosClothConfig* TemplateConfig=nullptr;UChaosClothSharedSimConfig* TemplateShared=nullptr;
    for(const auto& Pair:ReferenceCloth->ClothConfigs)
    {
        if(auto* Config=Cast<UChaosClothConfig>(Pair.Value))TemplateConfig=Config;
        if(auto* Shared=Cast<UChaosClothSharedSimConfig>(Pair.Value))TemplateShared=Shared;
    }
    if(!TemplateConfig||!TemplateShared)return Fail(TEXT("The saved Witch cloth has no Chaos configuration."));
    FSkeletalMeshClothBuildParams Params;
    Params.AssetName=TEXT("M07_ContinuousMembraneProxyV36");Params.LodIndex=0;Params.SourceSection=Proxy[0];Params.bRemoveFromMesh=false;
    TStrongObjectPtr<UClothingAssetFactory> Factory(NewObject<UClothingAssetFactory>());
    TStrongObjectPtr<UClothingAssetCommon> Extracted(Cast<UClothingAssetCommon>(Factory->CreateFromSkeletalMesh(SimulationSource,Params)));
    if(!Extracted.IsValid()||Extracted->LodData.Num()!=1)return Fail(TEXT("Continuous membrane extraction failed."));
    auto* Cloth=NewObject<UM07MembraneClothingAsset>(Mesh,
        MakeUniqueObjectName(Mesh,UM07MembraneClothingAsset::StaticClass(),TEXT("M07_WitchStyleMembraneV36")),RF_Transactional);
    Cloth->InitializeSimulationFrom(Extracted.Get());
    FGillDraft Draft;Draft.Asset.Reset(Cloth);
    const auto& Physical=Cloth->LodData[0].PhysicalMeshData;
    Draft.Distances.SetNum(Physical.Vertices.Num());
    for(int32 V=0;V<Physical.Vertices.Num();++V)
    {
        double Best=TNumericLimits<double>::Max();float Distance=0;
        for(const auto& Panel:Panels)for(int32 I=0;I<Panel.VerticesCm.Num();++I)
        {
            const double D=FVector3f::DistSquared(Physical.Vertices[V],Panel.VerticesCm[I]);
            if(D<Best){Best=D;Distance=Panel.MaxDistanceCm[I];}
        }
        if(Best>FMath::Square(ManifestMatchToleranceCm))return Fail(TEXT("Imported proxy units differ from authored centimeters."));
        Draft.Distances[V]=Distance;Draft.PinnedVertices+=Distance==0;Draft.MaxDistanceCm=FMath::Max(Draft.MaxDistanceCm,Distance);
    }
    if(!Draft.PinnedVertices||Draft.PinnedVertices==Draft.Distances.Num())return Fail(TEXT("Continuous sheets require fixed roots and free hems."));
    auto* Shared=DuplicateObject<UChaosClothSharedSimConfig>(TemplateShared,Cloth);
    ConfigureGill(Draft,MakeGillCollision(Mesh,Capsules),Shared);
    // Copy the actual installed Witch config, then adapt the contact scale to
    // the taller membrane. No separate point/face self-collision solver.
    auto* Config=DuplicateObject<UChaosClothConfig>(TemplateConfig,Cloth);
    Config->CollisionThickness=1.2f;
    Config->bUseSelfCollisions=false;Config->bUseSelfCollisionSpheres=true;
    Config->SelfCollisionSphereRadius=1.1f;Config->SelfCollisionSphereRadiusCullMultiplier=2.5f;
    Cloth->ClothConfigs.Add(Config->GetClass()->GetFName(),Config);
    Cloth->ApplyParameterMasks(true);Cloth->InvalidateAllCachedData();
    Cloth->RefreshBoneMapping(Mesh);Cloth->CalculateReferenceBoneIndex();
    FScopedSkeletalMeshPostEditChange Change(Mesh);Mesh->Modify();
    const auto Old=Mesh->GetMeshClothingAssets();
    for(UClothingAssetBase* Asset:Old)if(Asset)Asset->UnbindFromSkeletalMesh(Mesh,INDEX_NONE,INDEX_NONE);
    Mesh->SetMeshClothingAssets({Cloth});
    auto& Lod=Mesh->GetImportedModel()->LODModels[0];
    int32 Bound=0;
    for(int32 S=0;S<Lod.Sections.Num();++S)
    {
        bool HasMovingVertex=false;
        for(const auto& V:Lod.Sections[S].SoftVertices)if(V.Color.A>0){HasMovingVertex=true;break;}
        if(!HasMovingVertex)continue;
        if(!Cloth->BindToSkeletalMesh(Mesh,0,S,0))return Fail(TEXT("A membrane display section could not bind."));
        auto& Section=Lod.Sections[S];auto& User=Lod.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
        User.CorrespondClothAssetIndex=0;User.ClothingData=Section.ClothingData;User.bDisabled=Section.bDisabled=false;++Bound;
    }
    if(!Bound)return Fail(TEXT("The imported display has no authored cloth mobility alpha."));
    Mesh->InvalidateDeriveDataCacheGUID();Mesh->MarkPackageDirty();
    Receipt->SetBoolField(TEXT("success"),true);Receipt->SetBoolField(TEXT("saved"),false);
    Receipt->SetStringField(TEXT("template"),ReferenceCloth->GetPathName());
    Receipt->SetStringField(TEXT("cloth"),Cloth->GetPathName());
    Receipt->SetNumberField(TEXT("physical_vertices"),Physical.Vertices.Num());
    Receipt->SetNumberField(TEXT("physical_triangles"),Physical.Indices.Num()/3);
    Receipt->SetNumberField(TEXT("pinned_vertices"),Draft.PinnedVertices);
    Receipt->SetNumberField(TEXT("maximum_travel_cm"),Draft.MaxDistanceCm);
    Receipt->SetNumberField(TEXT("bound_sections"),Bound);
    Receipt->SetNumberField(TEXT("solver_iterations"),Shared->IterationCount);
    Receipt->SetNumberField(TEXT("solver_max_iterations"),Shared->MaxIterationCount);
    Receipt->SetNumberField(TEXT("solver_subdivisions"),Shared->SubdivisionCount);
    Receipt->SetNumberField(TEXT("anim_drive_stiffness"),Config->AnimDriveStiffness.Low);
    return WriteGillReceipt(Receipt);
#else
    return TEXT("{\"success\":false,\"error\":\"Editor authoring build required.\"}");
#endif
}

FString UBlindSupplicantAuthoring::BuildInteractingGillClothFromSavedSource(USkeletalMesh* Mesh, USkeletalMesh* SimulationSource, const FString& WeightManifestFile)
{
#if WITH_EDITOR
    auto Receipt = MakeShared<FJsonObject>();
    auto Fail = [&](const FString& Error)
    {
        Receipt->SetBoolField(TEXT("success"), false);
        Receipt->SetStringField(TEXT("error"), Error);
        return WriteGillReceipt(Receipt);
    };
    if (!Mesh || (Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_ContinuousV02") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_AnatomyV03") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_AnatomyV04") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_AnatomyV05") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV06") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV07") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV08") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV09") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV11") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV12") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_OriginalV13") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_ArmSweepV16") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_LegJointsV17") &&
        Mesh->GetOutermost()->GetName() != TEXT("/Game/Monsters/BlindSupplicantM07/SK_M07_BodyMotionV18")) || !SimulationSource ||
        !SimulationSource->GetOutermost()->GetName().StartsWith(TEXT("/Game/Monsters/BlindSupplicantM07/Working/")))
        return Fail(FString::Printf(TEXT("Only the M07 display and its preserved simulation source may be restored. Display=%s Simulation=%s"),
            *GetPathNameSafe(Mesh), *GetPathNameSafe(SimulationSource)));
    if (GillSections(Mesh, TEXT("M07_Gills")).Num() == 1)
        return BuildContinuousGillCloth(Mesh, SimulationSource, WeightManifestFile);
    TArray<FGillPanelManifest> Panels;
    TArray<FGillCapsuleManifest> Capsules;
    FString Error;
    if (!ReadGillManifest(WeightManifestFile, Panels, Capsules, Error)) return Fail(Error);
    const auto Sources = SimulationSource->GetMeshClothingAssets();
    if (Sources.Num() != GillCount) return Fail(TEXT("The preserved source must contain the six original gill simulations."));
    TArray<FGillDraft> Parts;
    Parts.SetNum(GillCount);
    for (UClothingAssetBase* Base : Sources)
    {
        auto* Source = Cast<UClothingAssetCommon>(Base);
        if (!Source || Source->LodData.Num() != 1) return Fail(TEXT("The preserved source cloth data is unavailable."));
        int32 Index = INDEX_NONE;
        for (int32 Id = 0; Id < GillCount; ++Id)
            if (Source->GetName().StartsWith(GillAssetName(Id))) Index = Id;
        if (Index == INDEX_NONE || Parts[Index].Asset.IsValid()) return Fail(TEXT("The preserved source gill identities are ambiguous."));
        TStrongObjectPtr<UClothingAssetCommon> Copy(NewObject<UClothingAssetCommon>());
        Copy->LodData = Source->LodData;
        Copy->UsedBoneNames = Source->UsedBoneNames;
        Copy->UsedBoneIndices = Source->UsedBoneIndices;
        Copy->ReferenceBoneIndex = Source->ReferenceBoneIndex;
        auto* Part = NewObject<UWitchRebuiltClothingAsset>(Mesh,
            MakeUniqueObjectName(Mesh, UWitchRebuiltClothingAsset::StaticClass(), FName(*GillAssetName(Index))), RF_Transactional);
        Part->InitializeSimulationFrom(Copy.Get());
        Parts[Index].Asset.Reset(Part);
        if (!MapGillDistances(Panels[Index], Parts[Index], Error)) return Fail(Error);
    }
    FScopedSkeletalMeshPostEditChange Change(Mesh);
    Mesh->Modify();
    const auto Old = Mesh->GetMeshClothingAssets();
    for (UClothingAssetBase* Asset : Old) Asset->UnbindFromSkeletalMesh(Mesh, INDEX_NONE, INDEX_NONE);
    Mesh->SetMeshClothingAssets({});
    auto* Collision = MakeGillCollision(Mesh, Capsules);
    auto* Shared = NewObject<UChaosClothSharedSimConfig>(Mesh, NAME_None, RF_Transactional);
    Shared->IterationCount = 4;
    Shared->MaxIterationCount = 6;
    Shared->SubdivisionCount = 1;
    for (auto& Part : Parts)
    {
        ConfigureGill(Part, Collision, Shared);
        Part.Asset->RefreshBoneMapping(Mesh);
        Mesh->AddClothingAsset(Part.Asset.Get());
    }
    for (int32 Index = 0; Index < GillCount; ++Index)
    {
        const auto Render = GillSections(Mesh, TEXT("M07_Gill_") + Panels[Index].Id);
        if (Render.Num() != 1 || !Parts[Index].Asset->BindToSkeletalMesh(Mesh, 0, Render[0], 0))
            return Fail(TEXT("A preserved gill simulation could not be restored to the display section."));
        auto& Lod = Mesh->GetImportedModel()->LODModels[0];
        auto& Section = Lod.Sections[Render[0]];
        auto& User = Lod.UserSectionsData.FindOrAdd(Section.OriginalDataSectionIndex);
        User.CorrespondClothAssetIndex = Index;
        User.ClothingData = Section.ClothingData;
        User.bDisabled = Section.bDisabled = false;
    }
    return BuildInteractingGillCloth(Mesh, WeightManifestFile);
#else
    return TEXT("{\"success\":false,\"error\":\"Editor authoring build required.\"}");
#endif
}
