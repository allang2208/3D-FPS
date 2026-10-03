#include "M07SkinReadback.h"

#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

#if WITH_EDITOR
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimSequence.h"
#include "Engine/SkeletalMesh.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"
#endif

namespace
{
FString WriteSkinJson(const TSharedRef<FJsonObject>& Object)
{
    FString Result;
    FJsonSerializer::Serialize(Object, TJsonWriterFactory<>::Create(&Result));
    return Result;
}

#if WITH_EDITOR
TArray<TSharedPtr<FJsonValue>> VectorJson(const FVector& Vector)
{
    return { MakeShared<FJsonValueNumber>(Vector.X), MakeShared<FJsonValueNumber>(Vector.Y),
        MakeShared<FJsonValueNumber>(Vector.Z) };
}

TArray<TSharedPtr<FJsonValue>> MatrixJson(const FMatrix& Matrix)
{
    TArray<TSharedPtr<FJsonValue>> Values;
    for (int32 Row = 0; Row < 4; ++Row)
    {
        for (int32 Column = 0; Column < 4; ++Column)
        {
            Values.Add(MakeShared<FJsonValueNumber>(Matrix.M[Row][Column]));
        }
    }
    return Values;
}

TSharedRef<FJsonObject> BoundsJson(const FBox& Bounds)
{
    const TSharedRef<FJsonObject> Object = MakeShared<FJsonObject>();
    Object->SetBoolField(TEXT("valid"), Bounds.IsValid != 0);
    if (Bounds.IsValid)
    {
        Object->SetArrayField(TEXT("min_cm"), VectorJson(Bounds.Min));
        Object->SetArrayField(TEXT("max_cm"), VectorJson(Bounds.Max));
    }
    return Object;
}

double MatrixIdentityResidual(const FMatrix& Matrix)
{
    double Maximum = 0.0;
    for (int32 Row = 0; Row < 4; ++Row)
    {
        for (int32 Column = 0; Column < 4; ++Column)
        {
            Maximum = FMath::Max(Maximum, FMath::Abs(Matrix.M[Row][Column] - (Row == Column ? 1.0 : 0.0)));
        }
    }
    return Maximum;
}

FVector TransformPosition(const FMatrix& Matrix, const FVector& Position)
{
    const FVector4 Result = Matrix.TransformFVector4(FVector4(Position, 1.0));
    return FVector(Result.X, Result.Y, Result.Z);
}

struct FM07ReadInfluence
{
    int32 PaletteIndex = INDEX_NONE;
    int32 BoneIndex = INDEX_NONE;
    uint16 RawWeight = 0;
};

struct FM07ReadContext
{
    const FReferenceSkeleton& Reference;
    TArray<FMatrix> ReferenceComponent;
    TArray<FMatrix> AnimationComponent;
    TArray<FMatrix> CachedInverse;
    TArray<FMatrix> CalculatedInverse;
    TMap<FName, int32> SampleCounts;

    explicit FM07ReadContext(const FReferenceSkeleton& InReference) : Reference(InReference) {}

    FVector Skin(const FVector& Position, const TArray<FM07ReadInfluence>& Influences,
        const TArray<FMatrix>& Inverses, bool bReferencePose = false) const
    {
        FVector Result = FVector::ZeroVector;
        for (const FM07ReadInfluence& Influence : Influences)
        {
            if (Inverses.IsValidIndex(Influence.BoneIndex))
            {
                const FMatrix Matrix = Inverses[Influence.BoneIndex] *
                    (bReferencePose ? ReferenceComponent[Influence.BoneIndex] : AnimationComponent[Influence.BoneIndex]);
                // GetBoneWeight expands an 8-bit weight to 16-bit; soft vertices already use 16-bit.
                Result += TransformPosition(Matrix, Position) * (double(Influence.RawWeight) / 65535.0);
            }
        }
        return Result;
    }

    bool WantsSample(const TArray<FM07ReadInfluence>& Influences)
    {
        int32 Dominant = INDEX_NONE;
        uint16 MaximumWeight = 0;
        for (const FM07ReadInfluence& Influence : Influences)
        {
            if (Influence.RawWeight > MaximumWeight)
            {
                MaximumWeight = Influence.RawWeight;
                Dominant = Influence.BoneIndex;
            }
        }
        if (Dominant < 0 || Dominant >= Reference.GetNum()) return false;
        const FName Name = Reference.GetBoneName(Dominant);
        const FString Text = Name.ToString();
        const bool bRelevant = Text == TEXT("head") || Text == TEXT("pelvis") ||
            Text.StartsWith(TEXT("upperarm_")) || Text.StartsWith(TEXT("lowerarm_")) ||
            Text.StartsWith(TEXT("hand_")) || Text.StartsWith(TEXT("thigh_")) ||
            Text.StartsWith(TEXT("calf_")) || Text.StartsWith(TEXT("foot_"));
        if (!bRelevant) return false;
        int32& Count = SampleCounts.FindOrAdd(Name);
        return Count++ < 4;
    }

    TSharedRef<FJsonObject> Sample(int32 VertexIndex, const FVector& Position,
        const TArray<FM07ReadInfluence>& Influences) const
    {
        const TSharedRef<FJsonObject> Object = MakeShared<FJsonObject>();
        Object->SetNumberField(TEXT("vertex_index"), VertexIndex);
        Object->SetArrayField(TEXT("position_cm"), VectorJson(Position));
        Object->SetArrayField(TEXT("animated_cached_cm"), VectorJson(Skin(Position, Influences, CachedInverse)));
        Object->SetArrayField(TEXT("animated_calculated_cm"), VectorJson(Skin(Position, Influences, CalculatedInverse)));
        Object->SetArrayField(TEXT("reference_roundtrip_cm"), VectorJson(Skin(Position, Influences, CachedInverse, true)));
        TArray<TSharedPtr<FJsonValue>> WeightValues;
        int32 WeightSum = 0;
        for (const FM07ReadInfluence& Influence : Influences)
        {
            const TSharedRef<FJsonObject> Weight = MakeShared<FJsonObject>();
            Weight->SetNumberField(TEXT("palette_index"), Influence.PaletteIndex);
            Weight->SetNumberField(TEXT("bone_index"), Influence.BoneIndex);
            Weight->SetStringField(TEXT("bone_name"), Influence.BoneIndex >= 0 && Influence.BoneIndex < Reference.GetNum()
                ? Reference.GetBoneName(Influence.BoneIndex).ToString() : TEXT("INVALID"));
            Weight->SetNumberField(TEXT("raw_weight_u16"), Influence.RawWeight);
            Weight->SetNumberField(TEXT("weight"), double(Influence.RawWeight) / 65535.0);
            WeightValues.Add(MakeShared<FJsonValueObject>(Weight));
            WeightSum += Influence.RawWeight;
        }
        Object->SetNumberField(TEXT("raw_weight_sum"), WeightSum);
        Object->SetArrayField(TEXT("influences"), WeightValues);
        return Object;
    }
};

TArray<TSharedPtr<FJsonValue>> PaletteJson(TConstArrayView<FBoneIndexType> Palette,
    const FReferenceSkeleton& Reference)
{
    TArray<TSharedPtr<FJsonValue>> Values;
    for (int32 Index = 0; Index < Palette.Num(); ++Index)
    {
        const int32 Bone = Palette[Index];
        const TSharedRef<FJsonObject> Value = MakeShared<FJsonObject>();
        Value->SetNumberField(TEXT("palette_index"), Index);
        Value->SetNumberField(TEXT("bone_index"), Bone);
        Value->SetStringField(TEXT("bone_name"), Bone < Reference.GetNum()
            ? Reference.GetBoneName(Bone).ToString() : TEXT("INVALID"));
        Values.Add(MakeShared<FJsonValueObject>(Value));
    }
    return Values;
}

TArray<FM07ReadInfluence> SourceInfluences(const FSoftSkinVertex& Vertex,
    TConstArrayView<FBoneIndexType> Palette)
{
    TArray<FM07ReadInfluence> Result;
    for (int32 Index = 0; Index < MAX_TOTAL_INFLUENCES; ++Index)
    {
        if (Vertex.InfluenceWeights[Index] == 0) continue;
        const int32 LocalBone = Vertex.InfluenceBones[Index];
        Result.Add({ LocalBone, Palette.IsValidIndex(LocalBone) ? int32(Palette[LocalBone]) : INDEX_NONE,
            Vertex.InfluenceWeights[Index] });
    }
    return Result;
}

TArray<FM07ReadInfluence> RenderInfluences(const FSkinWeightVertexBuffer& Weights, uint32 VertexIndex,
    TConstArrayView<FBoneIndexType> Palette)
{
    uint32 Offset = 0;
    uint32 Count = 0;
    Weights.GetVertexInfluenceOffsetCount(VertexIndex, Offset, Count);
    TArray<FM07ReadInfluence> Result;
    for (uint32 Index = 0; Index < Count; ++Index)
    {
        const uint16 Weight = Weights.GetBoneWeight(VertexIndex, Index);
        if (Weight == 0) continue;
        const int32 LocalBone = int32(Weights.GetBoneIndex(VertexIndex, Index));
        Result.Add({ LocalBone, Palette.IsValidIndex(LocalBone) ? int32(Palette[LocalBone]) : INDEX_NONE, Weight });
    }
    return Result;
}

bool SameGlobalInfluences(const TArray<FM07ReadInfluence>& A, const TArray<FM07ReadInfluence>& B)
{
    TMap<int32, int32> ValuesA;
    TMap<int32, int32> ValuesB;
    for (const FM07ReadInfluence& Influence : A) ValuesA.FindOrAdd(Influence.BoneIndex) += Influence.RawWeight;
    for (const FM07ReadInfluence& Influence : B) ValuesB.FindOrAdd(Influence.BoneIndex) += Influence.RawWeight;
    if (ValuesA.Num() != ValuesB.Num()) return false;
    for (const TPair<int32, int32>& Value : ValuesA)
    {
        const int32* Other = ValuesB.Find(Value.Key);
        // The render buffer may quantize a 16-bit source weight to 8-bit.
        if (!Other || FMath::Abs(*Other - Value.Value) > 257) return false;
    }
    return true;
}
#endif
}

FString UM07SkinReadback::ReadSkinData(USkeletalMesh* Mesh, UAnimSequence* Animation)
{
    const TSharedRef<FJsonObject> Root = MakeShared<FJsonObject>();
    Root->SetBoolField(TEXT("read_only"), true);
#if WITH_EDITOR
    if (!Mesh)
    {
        Root->SetStringField(TEXT("error"), TEXT("A skeletal mesh is required."));
        return WriteSkinJson(Root);
    }
    Root->SetStringField(TEXT("mesh"), Mesh->GetPathName());
    Root->SetStringField(TEXT("animation"), Animation ? Animation->GetPathName() : TEXT(""));
    Root->SetStringField(TEXT("units"), TEXT("centimeters"));
    Root->SetStringField(TEXT("matrix_layout"), TEXT("row-major; local * parent; inverse_reference * animated_component"));
    const FReferenceSkeleton& Reference = Mesh->GetRefSkeleton();
    FM07ReadContext Context(Reference);
    const TArray<FTransform>& LocalReference = Reference.GetRefBonePose();
    const TArray<FMatrix44f>& CachedInverses = Mesh->GetRefBasesInvMatrix();
    const IAnimationDataModel* Model = Animation ? Animation->GetDataModel() : nullptr;
    Root->SetNumberField(TEXT("reference_bone_count"), Reference.GetNum());
    Root->SetNumberField(TEXT("cached_inverse_count"), CachedInverses.Num());
    Root->SetBoolField(TEXT("has_animation_data_model"), Model != nullptr);
    TArray<TSharedPtr<FJsonValue>> BoneValues;
    double MaximumResidual = 0.0;
    for (int32 BoneIndex = 0; BoneIndex < Reference.GetNum(); ++BoneIndex)
    {
        const int32 Parent = Reference.GetParentIndex(BoneIndex);
        const FName Name = Reference.GetBoneName(BoneIndex);
        const bool bHasTrack = Model && Model->IsValidBoneTrackName(Name);
        const FTransform LocalAnimation = bHasTrack ? Model->GetBoneTrackTransform(Name, FFrameNumber(0)) : LocalReference[BoneIndex];
        const FMatrix RefComponent = LocalReference[BoneIndex].ToMatrixWithScale() *
            (Parent >= 0 ? Context.ReferenceComponent[Parent] : FMatrix::Identity);
        const FMatrix AnimComponent = LocalAnimation.ToMatrixWithScale() *
            (Parent >= 0 ? Context.AnimationComponent[Parent] : FMatrix::Identity);
        Context.ReferenceComponent.Add(RefComponent);
        Context.AnimationComponent.Add(AnimComponent);
        Context.CalculatedInverse.Add(RefComponent.Inverse());
        // An absent cache is reported explicitly; use the calculated inverse only for bounded readback.
        const bool bHasCachedInverse = CachedInverses.IsValidIndex(BoneIndex);
        Context.CachedInverse.Add(bHasCachedInverse ? FMatrix(CachedInverses[BoneIndex]) : RefComponent.Inverse());
        const double Residual = MatrixIdentityResidual(Context.CachedInverse.Last() * RefComponent);
        MaximumResidual = FMath::Max(MaximumResidual, Residual);
        const TSharedRef<FJsonObject> Bone = MakeShared<FJsonObject>();
        Bone->SetNumberField(TEXT("index"), BoneIndex);
        Bone->SetNumberField(TEXT("parent_index"), Parent);
        Bone->SetStringField(TEXT("name"), Name.ToString());
        Bone->SetBoolField(TEXT("animation_track_present"), bHasTrack);
        Bone->SetBoolField(TEXT("cached_inverse_present"), bHasCachedInverse);
        Bone->SetArrayField(TEXT("reference_local_matrix"), MatrixJson(LocalReference[BoneIndex].ToMatrixWithScale()));
        Bone->SetArrayField(TEXT("reference_component_matrix"), MatrixJson(RefComponent));
        Bone->SetArrayField(TEXT("animation_local_matrix"), MatrixJson(LocalAnimation.ToMatrixWithScale()));
        Bone->SetArrayField(TEXT("animation_component_matrix"), MatrixJson(AnimComponent));
        Bone->SetArrayField(TEXT("cached_inverse_matrix"), MatrixJson(Context.CachedInverse.Last()));
        Bone->SetNumberField(TEXT("cached_inverse_reference_identity_max_residual"), Residual);
        BoneValues.Add(MakeShared<FJsonValueObject>(Bone));
    }
    Root->SetNumberField(TEXT("cached_inverse_reference_identity_max_residual"), MaximumResidual);
    Root->SetArrayField(TEXT("bones"), BoneValues);

    const FSkeletalMeshModel* Imported = Mesh->GetImportedModel();
    const FSkeletalMeshLODModel* Source = Imported && Imported->LODModels.Num() > 0 ? &Imported->LODModels[0] : nullptr;
    Root->SetBoolField(TEXT("has_imported_lod0"), Source != nullptr);
    TMap<uint32, const FSoftSkinVertex*> SourceByIndex;
    TMap<uint32, int32> SourceSectionByIndex;
    TArray<TSharedPtr<FJsonValue>> SourceSections;
    if (Source)
    {
        for (int32 SectionIndex = 0; SectionIndex < Source->Sections.Num(); ++SectionIndex)
        {
            const FSkelMeshSection& Section = Source->Sections[SectionIndex];
            const TSharedRef<FJsonObject> Value = MakeShared<FJsonObject>();
            Value->SetNumberField(TEXT("section_index"), SectionIndex);
            Value->SetNumberField(TEXT("material_index"), Section.MaterialIndex);
            Value->SetNumberField(TEXT("base_vertex_index"), Section.BaseVertexIndex);
            Value->SetNumberField(TEXT("num_vertices"), Section.NumVertices);
            Value->SetNumberField(TEXT("soft_vertices_count"), Section.SoftVertices.Num());
            Value->SetBoolField(TEXT("disabled"), Section.bDisabled);
            Value->SetBoolField(TEXT("has_clothing"), Section.ClothingData.IsValid());
            Value->SetArrayField(TEXT("bone_map"), PaletteJson(Section.BoneMap, Reference));
            FBox ReferenceBounds(ForceInit), AnimatedCachedBounds(ForceInit), AnimatedCalculatedBounds(ForceInit);
            double MaximumRoundTripError = 0.0;
            int32 InvalidInfluences = 0;
            int32 NonNormalizedVertices = 0;
            TArray<TSharedPtr<FJsonValue>> Samples;
            Context.SampleCounts.Reset();
            for (int32 VertexIndex = 0; VertexIndex < Section.SoftVertices.Num(); ++VertexIndex)
            {
                const FSoftSkinVertex& Vertex = Section.SoftVertices[VertexIndex];
                const uint32 GlobalVertex = Section.BaseVertexIndex + uint32(VertexIndex);
                SourceByIndex.Add(GlobalVertex, &Vertex);
                SourceSectionByIndex.Add(GlobalVertex, SectionIndex);
                const FVector Position(Vertex.Position);
                const TArray<FM07ReadInfluence> Influences = SourceInfluences(Vertex, Section.BoneMap);
                int32 WeightSum = 0;
                for (const FM07ReadInfluence& Influence : Influences)
                {
                    WeightSum += Influence.RawWeight;
                    if (Influence.BoneIndex < 0 || Influence.BoneIndex >= Reference.GetNum()) ++InvalidInfluences;
                }
                if (FMath::Abs(WeightSum - 65535) > 1) ++NonNormalizedVertices;
                ReferenceBounds += Position;
                AnimatedCachedBounds += Context.Skin(Position, Influences, Context.CachedInverse);
                AnimatedCalculatedBounds += Context.Skin(Position, Influences, Context.CalculatedInverse);
                MaximumRoundTripError = FMath::Max(MaximumRoundTripError,
                    FVector::Distance(Position, Context.Skin(Position, Influences, Context.CachedInverse, true)));
                if (Context.WantsSample(Influences)) Samples.Add(MakeShared<FJsonValueObject>(Context.Sample(GlobalVertex, Position, Influences)));
            }
            Value->SetNumberField(TEXT("invalid_influence_count"), InvalidInfluences);
            Value->SetNumberField(TEXT("non_normalized_vertex_count"), NonNormalizedVertices);
            Value->SetNumberField(TEXT("reference_roundtrip_max_error_cm"), MaximumRoundTripError);
            Value->SetObjectField(TEXT("reference_bounds"), BoundsJson(ReferenceBounds));
            Value->SetObjectField(TEXT("animated_cached_bounds"), BoundsJson(AnimatedCachedBounds));
            Value->SetObjectField(TEXT("animated_calculated_bounds"), BoundsJson(AnimatedCalculatedBounds));
            Value->SetArrayField(TEXT("samples"), Samples);
            SourceSections.Add(MakeShared<FJsonValueObject>(Value));
        }
    }
    Root->SetArrayField(TEXT("imported_sections"), SourceSections);

    const FSkeletalMeshRenderData* RenderData = Mesh->GetResourceForRendering();
    const FSkeletalMeshLODRenderData* Render = RenderData && RenderData->LODRenderData.Num() > 0 ? &RenderData->LODRenderData[0] : nullptr;
    Root->SetBoolField(TEXT("has_render_lod0"), Render != nullptr);
    TArray<TSharedPtr<FJsonValue>> RenderSections;
    if (Render)
    {
        const FPositionVertexBuffer& Positions = Render->StaticVertexBuffers.PositionVertexBuffer;
        const FSkinWeightVertexBuffer* Weights = Render->GetSkinWeightVertexBuffer();
        const bool bCPUPositions = Positions.GetVertexData() != nullptr;
        const bool bCPUWeights = Weights && Weights->GetDataVertexBuffer()->GetWeightData() != nullptr;
        Root->SetBoolField(TEXT("render_position_cpu_data_available"), bCPUPositions);
        Root->SetBoolField(TEXT("render_skin_cpu_data_available"), bCPUWeights);
        Root->SetNumberField(TEXT("render_vertex_count"), Positions.GetNumVertices());
        Root->SetBoolField(TEXT("render_lod_has_unified_bone_map"), Render->HasUnifiedBoneMap());
        Root->SetArrayField(TEXT("render_unified_bone_map"), PaletteJson(Render->GetUnifiedBoneMap(), Reference));
        if (Weights)
        {
            Root->SetNumberField(TEXT("render_skin_vertex_count"), Weights->GetNumVertices());
            Root->SetNumberField(TEXT("render_skin_max_influences"), Weights->GetMaxBoneInfluences());
            Root->SetBoolField(TEXT("render_skin_16bit_indices"), Weights->Use16BitBoneIndex());
            Root->SetBoolField(TEXT("render_skin_16bit_weights"), Weights->Use16BitBoneWeight());
            Root->SetBoolField(TEXT("render_skin_variable_influences"), Weights->GetVariableBonesPerVertex());
        }
        for (int32 SectionIndex = 0; SectionIndex < Render->RenderSections.Num(); ++SectionIndex)
        {
            const FSkelMeshRenderSection& Section = Render->RenderSections[SectionIndex];
            const TConstArrayView<FBoneIndexType> Palette = Section.HasUnifiedBoneMap()
                ? Render->GetUnifiedBoneMap() : TConstArrayView<FBoneIndexType>(Section.BoneMap);
            const TSharedRef<FJsonObject> Value = MakeShared<FJsonObject>();
            Value->SetNumberField(TEXT("section_index"), SectionIndex);
            Value->SetNumberField(TEXT("material_index"), Section.MaterialIndex);
            Value->SetNumberField(TEXT("base_vertex_index"), Section.BaseVertexIndex);
            Value->SetNumberField(TEXT("num_vertices"), Section.NumVertices);
            Value->SetBoolField(TEXT("has_unified_bone_map"), Section.HasUnifiedBoneMap());
            Value->SetArrayField(TEXT("section_bone_map"), PaletteJson(Section.BoneMap, Reference));
            Value->SetArrayField(TEXT("effective_bone_map"), PaletteJson(Palette, Reference));
            FBox ReferenceBounds(ForceInit), AnimatedCachedBounds(ForceInit), AnimatedCalculatedBounds(ForceInit);
            TArray<TSharedPtr<FJsonValue>> Samples;
            int32 InvalidInfluences = 0, ComparableVertices = 0, PositionMismatches = 0, InfluenceMismatches = 0;
            double MaximumRoundTripError = 0.0, MaximumSourcePositionError = 0.0;
            Context.SampleCounts.Reset();
            if (bCPUPositions && bCPUWeights)
            {
                for (uint32 LocalVertex = 0; LocalVertex < Section.NumVertices; ++LocalVertex)
                {
                    const uint32 GlobalVertex = Section.BaseVertexIndex + LocalVertex;
                    if (GlobalVertex >= Positions.GetNumVertices() || GlobalVertex >= Weights->GetNumVertices()) break;
                    const FVector Position(Positions.VertexPosition(GlobalVertex));
                    const TArray<FM07ReadInfluence> Influences = RenderInfluences(*Weights, GlobalVertex, Palette);
                    for (const FM07ReadInfluence& Influence : Influences)
                        if (Influence.BoneIndex < 0 || Influence.BoneIndex >= Reference.GetNum()) ++InvalidInfluences;
                    ReferenceBounds += Position;
                    AnimatedCachedBounds += Context.Skin(Position, Influences, Context.CachedInverse);
                    AnimatedCalculatedBounds += Context.Skin(Position, Influences, Context.CalculatedInverse);
                    MaximumRoundTripError = FMath::Max(MaximumRoundTripError,
                        FVector::Distance(Position, Context.Skin(Position, Influences, Context.CachedInverse, true)));
                    if (Context.WantsSample(Influences)) Samples.Add(MakeShared<FJsonValueObject>(Context.Sample(GlobalVertex, Position, Influences)));
                    const FSoftSkinVertex* const* SourceVertex = SourceByIndex.Find(GlobalVertex);
                    const int32* SourceSectionIndex = SourceSectionByIndex.Find(GlobalVertex);
                    if (SourceVertex && SourceSectionIndex && Source)
                    {
                        const FSkelMeshSection& SourceSection = Source->Sections[*SourceSectionIndex];
                        if (SourceSection.MaterialIndex != Section.MaterialIndex) continue;
                        const double PositionError = FVector::Distance(Position, FVector((*SourceVertex)->Position));
                        MaximumSourcePositionError = FMath::Max(MaximumSourcePositionError, PositionError);
                        if (PositionError > 0.001)
                        {
                            ++PositionMismatches;
                            continue;
                        }
                        ++ComparableVertices;
                        if (!SameGlobalInfluences(SourceInfluences(**SourceVertex, SourceSection.BoneMap), Influences)) ++InfluenceMismatches;
                    }
                }
            }
            Value->SetNumberField(TEXT("invalid_influence_count"), InvalidInfluences);
            Value->SetNumberField(TEXT("reference_roundtrip_max_error_cm"), MaximumRoundTripError);
            Value->SetNumberField(TEXT("source_position_max_error_cm_at_same_index"), MaximumSourcePositionError);
            Value->SetNumberField(TEXT("source_position_mismatches_at_same_index"), PositionMismatches);
            Value->SetNumberField(TEXT("source_render_comparable_vertex_count"), ComparableVertices);
            Value->SetNumberField(TEXT("source_render_influence_mismatch_count"), InfluenceMismatches);
            Value->SetObjectField(TEXT("reference_bounds"), BoundsJson(ReferenceBounds));
            Value->SetObjectField(TEXT("animated_cached_bounds"), BoundsJson(AnimatedCachedBounds));
            Value->SetObjectField(TEXT("animated_calculated_bounds"), BoundsJson(AnimatedCalculatedBounds));
            Value->SetArrayField(TEXT("samples"), Samples);
            RenderSections.Add(MakeShared<FJsonValueObject>(Value));
        }
    }
    Root->SetArrayField(TEXT("render_sections"), RenderSections);
#else
    Root->SetStringField(TEXT("error"), TEXT("Imported skin readback requires an editor build."));
#endif
    return WriteSkinJson(Root);
}
