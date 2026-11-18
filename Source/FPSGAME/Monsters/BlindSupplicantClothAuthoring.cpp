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

#include "BlindSupplicantClothAuthoringPrivate.h"

#if WITH_EDITOR
namespace BlindSupplicantCloth
{
// Both arrays describe the same exported proxy; this allowance is for FBX
// welding and float precision, never for guessing scale or coordinate axes.
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
    TArray<FGillCapsuleManifest>& Capsules, FString& Error, int32 ExpectedPanels)
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
}
#endif
