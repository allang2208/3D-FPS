#include "FPSOutfitStairVisibility.h"
#include "FPSModularOutfitComponent.h"
#include "FPSPlayerBodyComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "ClothingAsset.h"
#include "ClothingSystemRuntimeTypes.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace FPSRobeHem
{
FName PointName(int32 Index){return FName(*FString::Printf(TEXT("RobeHemPoint%d"),Index));}
FLinearColor Color(const FVector& P){return FLinearColor(P.X,P.Y,P.Z,1.f);}
}

void FFPSRobeHemEnvelope::Initialize(USkeletalMeshComponent* Robe)
{
    Garment=Robe;Samples.Reset();bReady=false;
    const auto* Mesh=Robe?Robe->GetSkeletalMeshAsset():nullptr;
    if(!Mesh)return;
    const auto& Ref=Mesh->GetRefSkeleton();TArray<FTransform> Rest=Ref.GetRefBonePose();
    for(int32 B=0;B<Rest.Num();++B)if(Ref.GetParentIndex(B)>=0)Rest[B]*=Rest[Ref.GetParentIndex(B)];
    const int32 Knee=Ref.FindBoneIndex(TEXT("calf_l")),Ankle=Ref.FindBoneIndex(TEXT("foot_l"));
    const int32 KneeR=Ref.FindBoneIndex(TEXT("calf_r")),AnkleR=Ref.FindBoneIndex(TEXT("foot_r"));
    if(Knee==INDEX_NONE||Ankle==INDEX_NONE||KneeR==INDEX_NONE||AnkleR==INDEX_NONE)return;
    const float Length=(FVector::Distance(Rest[Knee].GetLocation(),Rest[Ankle].GetLocation())+
        FVector::Distance(Rest[KneeR].GetLocation(),Rest[AnkleR].GetLocation()))*.5f;
    Scale=Length/40.f;
    // Same rest-space partition as author_hem_layers.py. A moving opposite
    // foot must never exempt this calf from the cloth constraint.
    AnkleCut=FMath::Max(Rest[Ankle].GetLocation().Z,Rest[AnkleR].GetLocation().Z)+Length*.15f;
    for(int32 C=0;C<Mesh->GetMeshClothingAssets().Num();++C)
    {
        const auto* Cloth=Cast<UClothingAssetCommon>(Mesh->GetMeshClothingAssets()[C]);
        if(!Cloth||Cloth->LodData.IsEmpty())continue;
        const auto& Physical=Cloth->LodData[0].PhysicalMeshData;
        if(Physical.Vertices.IsEmpty())continue;
        float Bottom=MAX_flt,Top=-MAX_flt;FVector Center=FVector::ZeroVector;
        for(const auto& V:Physical.Vertices){Bottom=FMath::Min(Bottom,V.Z);Top=FMath::Max(Top,V.Z);Center+=FVector(V);}
        Center/=Physical.Vertices.Num();const float Height=Top-Bottom;if(Height<20.f*Scale)continue;
        const float Heights[RingCount]={0.f,.4f,.75f,1.f};
        for(int32 Ring=0;Ring<RingCount;++Ring)for(int32 Angle=0;Angle<RingPoints;++Angle)
        {
            const float TargetZ=Bottom+Height*Heights[Ring];
            const float Phi=Angle*UE_TWO_PI/RingPoints;int32 Best=INDEX_NONE;float Score=MAX_flt;
            for(int32 V=0;V<Physical.Vertices.Num();++V)
            {
                const FVector P=FVector(Physical.Vertices[V])-Center;
                const float A=FMath::FindDeltaAngleRadians(Phi,static_cast<float>(FMath::Atan2(P.Y,P.X)));
                const float D=FMath::Square((Physical.Vertices[V].Z-TargetZ)/Height*64.f)+FMath::Square(A*RingPoints);
                if(D<Score){Score=D;Best=V;}
            }
            if(!Physical.BoneData.IsValidIndex(Best)){Samples.Reset();return;}
            auto& Sample=Samples.AddDefaulted_GetRef();Sample.Particle=Best;
            const auto& Binding=Physical.BoneData[Best];
            for(int32 I=0;I<Binding.NumInfluences;++I)
            {
                const int32 Used=Binding.BoneIndices[I];
                if(!Cloth->UsedBoneIndices.IsValidIndex(Used)||Binding.BoneWeights[I]<=0.f)continue;
                const int32 Bone=Cloth->UsedBoneIndices[Used];if(!Rest.IsValidIndex(Bone))continue;
                Sample.Influences.Add({Bone,Binding.BoneWeights[I],Rest[Bone].InverseTransformPosition(FVector(Physical.Vertices[Best]))});
            }
            if(Sample.Influences.IsEmpty()){Samples.Reset();return;}
        }
        ClothIndex=C;bReady=Samples.Num()==PointCount;return;
    }
}

void FFPSRobeHemEnvelope::Update(bool bOnStairs,float Delta)
{
    auto* Part=Garment.Get();if(!Part||!bReady){Strength=0.f;return;}
    const auto* Pawn=Cast<APawn>(Part->GetOwner());
    const bool Visible=Part->IsVisible()&&!Part->bHiddenInGame&&!(Pawn&&Pawn->IsLocallyControlled()&&Part->bOwnerNoSee);
    // Coverage cannot fade with last-frame render relevance: a remote pawn
    // returning to view needs a current envelope on its very first frame.
    // Update the bounded 64 samples for every logically visible robe,
    // including off-screen bodies; this does not start another cloth solve.
    Strength=Visible?1.f:0.f;
    StairBlend=FMath::FInterpConstantTo(StairBlend,bOnStairs?1.f:0.f,Delta,bOnStairs?5.5f:3.f);
    if(Strength<=0.f)return;
    const auto& Frames=Part->GetComponentSpaceTransforms();
    // The outfit tick depends on this robe's cloth completion/writeback. This
    // accessor does not itself wait or flush: use the current rendered solve.
    // Retain the bounded fallback only for a missing/suspended simulation.
    const auto& Data=Part->GetCurrentClothingData_AnyThread();const auto* Sim=Data.Find(ClothIndex);
    const bool Current=Sim&&Sim->LODIndex==0&&!Sim->Positions.IsEmpty();
    SimulationAge=Current?0.f:SimulationAge+Delta;
    for(int32 I=0;I<PointCount;++I)
    {
        FVector Skinned=FVector::ZeroVector;float Mass=0.f;
        for(const auto& W:Samples[I].Influences)if(Frames.IsValidIndex(W.Bone))
        {Skinned+=Frames[W.Bone].TransformPosition(W.Position)*W.Weight;Mass+=W.Weight;}
        if(Mass<=UE_SMALL_NUMBER){Strength=0.f;return;}
        Skinned/=Mass;
        if(Current&&Sim->Positions.IsValidIndex(Samples[I].Particle))
            SimulationResidual[I]=Sim->ComponentRelativeTransform.TransformPosition(FVector(Sim->Positions[Samples[I].Particle]))-Skinned;
        else if(SimulationAge>.12f)SimulationResidual[I]=FMath::VInterpTo(SimulationResidual[I],FVector::ZeroVector,Delta,8.f);
        Points[I]=Skinned+SimulationResidual[I]*Part->ClothBlendWeight;
    }
}

void FFPSRobeStairSections::Initialize(USkeletalMeshComponent* Part,const TArray<int32>& Covered)
{
    Mesh=Part;Sections.Reset();Materials.Reset();bApplied=false;
    const auto* Asset=Part?Part->GetSkeletalMeshAsset():nullptr;
    const auto* Data=Asset?Asset->GetResourceForRendering():nullptr;
    if(!Data)return;
    LODCount=Data->LODRenderData.Num();
    const auto& AssetMaterials=Asset->GetMaterials();
    for(int32 M=0;M<AssetMaterials.Num();++M)
    {
        const FString Name=AssetMaterials[M].MaterialSlotName.ToString();
        const bool Cap=Name.StartsWith(TEXT("RobeStairCap_"));
        const FString Prefix=Cap?TEXT("RobeStairCap_"):TEXT("RobeStairHidden_");
        if(!Name.StartsWith(Prefix))continue;
        const FString Original=Name.Mid(Prefix.Len());
        if(!Original.IsNumeric())continue;
        Sections.Add({M,Cap,Covered.Contains(FCString::Atoi(*Original))});
        if(Cap||Sections.Last().bCovered)continue;
        float Supported=0.f;auto* Material=Part->GetMaterial(M);
        if(!Material||!Material->GetScalarParameterValue(FMaterialParameterInfo(TEXT("RobeHemStrength")),Supported))continue;
        auto* MID=Part->CreateDynamicMaterialInstance(M);if(!MID)continue;
        auto& Binding=Materials.AddDefaulted_GetRef();Binding.Instance=MID;
        MID->InitializeScalarParameterAndGetIndex(TEXT("RobeHemStrength"),0.f,Binding.Strength);
        MID->InitializeVectorParameterAndGetIndex(TEXT("RobeHemShape"),FLinearColor(16,2,8,1),Binding.Shape);
        for(int32 I=0;I<FFPSRobeHemEnvelope::PointCount;++I)
        {int32 Index=INDEX_NONE;MID->InitializeVectorParameterAndGetIndex(FPSRobeHem::PointName(I),FLinearColor::Black,Index);Binding.Points.Add(Index);}
    }
}

void FFPSRobeStairSections::Apply(bool bHideCalves)
{
    if(Sections.IsEmpty()||(bApplied&&bLastHidden==bHideCalves))return;
    auto* Part=Mesh.Get();const auto* Asset=Part?Part->GetSkeletalMeshAsset():nullptr;
    const auto* Data=Asset?Asset->GetResourceForRendering():nullptr;
    if(!Data)return;
    for(int32 L=0;L<FMath::Min(LODCount,Data->LODRenderData.Num());++L)
        for(const FSection& Entry:Sections)
        {
            // Rejoin the original calf/shaft to the shoe in every state.
            // Only the old artificial ankle disks stay hidden.
            const bool Show=!Entry.bCovered&&!Entry.bStairOnly;
            const auto& RenderSections=Data->LODRenderData[L].RenderSections;
            for(int32 S=0;S<RenderSections.Num();++S)
                if(RenderSections[S].MaterialIndex==Entry.Material)
                    Part->ShowMaterialSection(Entry.Material,S,Show,L);
        }
    bApplied=true;bLastHidden=bHideCalves;
}

void FFPSRobeStairSections::Conform(const FFPSRobeHemEnvelope& Hem)
{
    for(auto& Binding:Materials)if(auto* MID=Binding.Instance.Get())
    {
        if(Hem.Strength<=0.f&&Binding.LastStrength<=0.f)continue;
        if(Hem.Strength>0.f)
        {
            for(int32 I=0;I<Binding.Points.Num();++I)MID->SetVectorParameterByIndex(Binding.Points[I],FPSRobeHem::Color(Hem.Points[I]));
            MID->SetVectorParameterByIndex(Binding.Shape,FLinearColor(Hem.AnkleCut,(1.f+Hem.StairBlend)*Hem.Scale,(6.f+2.f*Hem.StairBlend)*Hem.Scale,Hem.Scale));
        }
        MID->SetScalarParameterByIndex(Binding.Strength,Hem.Strength);Binding.LastStrength=Hem.Strength;
    }
}

bool UFPSModularOutfitComponent::WantsRobeStairSupport() const
{
    static const FName Robe(TEXT("ue_blue_mage_robe"));
    if(Equipped.FindRef(7)==Robe)return true;
    // Async equipment replacement keeps the last complete visible outfit.
    // Keep its calf policy until that presentation is actually released too.
    for(const auto& Presentation:Presentations)
        if(!Presentation.StairSections.IsEmpty())return true;
    return false;
}

void UFPSModularOutfitComponent::ObserveRobeStairSupport(const TArray<FHitResult>& Hits)
{
    if(!WantsRobeStairSupport()||!GetWorld())return;
    const auto* Character=Cast<ACharacter>(GetOwner());
    const auto* Move=Character?Character->GetCharacterMovement():nullptr;
    if(!Move||!Move->IsMovingOnGround())return;
    const float Limit=Move->MaxStepHeight+5.f;
    for(int32 A=0;A<Hits.Num();++A)for(int32 B=A+1;B<Hits.Num();++B)
    {
        // Different tread planes, not simply different world heights: a ramp
        // or moving flat platform must not masquerade as a stair.
        const auto& H0=Hits[A];const auto& H1=Hits[B];
        if(FVector::DotProduct(H0.ImpactNormal,H1.ImpactNormal)<.985f)continue;
        const float Gap=FMath::Abs(FVector::DotProduct(H1.ImpactPoint-H0.ImpactPoint,H0.ImpactNormal));
        if(Gap>=3.f&&Gap<=Limit)
        {
            RobeStairUntil=GetWorld()->GetTimeSeconds()+.55f;
            return;
        }
    }
}

void UFPSModularOutfitComponent::UpdateRobeStairVisibility()
{
    if(!WantsRobeStairSupport())
    {RobeStairUntil=-1.f;bHideRobeCalves=false;return;}
    const auto* Character=Cast<ACharacter>(GetOwner());
    const auto* Move=Character?Character->GetCharacterMovement():nullptr;
    const auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    const bool Alive=!Body||Body->GetBodyState().Action!=EFPSBodyAction::Dead;
    if(!Move||!Move->IsMovingOnGround()||!Alive)
        RobeStairUntil=-1.f;
    bHideRobeCalves=GetWorld()&&GetWorld()->GetTimeSeconds()<RobeStairUntil;
}
