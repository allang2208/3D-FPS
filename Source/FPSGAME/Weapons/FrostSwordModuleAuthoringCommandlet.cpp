#include "FrostSwordModuleAuthoringCommandlet.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "StaticMeshResources.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "AssetCompilingManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

// Asset authoring: derive exact static-to-bone placement from the already
// imported original sword. No world, profile, rendering or gameplay is run.
int32 UFrostSwordModuleAuthoringCommandlet::Main(const FString& Params)
{
    const FString Folder=FPaths::ProjectDir()/TEXT("SourceAssets/FrostSwordModules20260915");
    FString Text;TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*(Folder/TEXT("catalog_base.json")))||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root))return 1;
    auto* Static=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Weapons/FrostCrystalSword20260915/SM_FrostCrystalSword"));
    auto* Skin=LoadObject<USkeletalMesh>(nullptr,TEXT("/Game/Weapons/FrostCrystalSword20260915/SK_FrostCrystalSword_Manny"));
    auto* Arms=LoadObject<USkeletalMesh>(nullptr,*Root->GetStringField(TEXT("arms_mesh")));
    if(!Static||!Skin||!Arms)return 2;
    FAssetCompilingManager::Get().FinishAllCompilation();
    const auto& S=Static->GetRenderData()->LODResources[0];
    const auto& K=Skin->GetResourceForRendering()->LODRenderData[0];
    auto UVKey=[](FVector2f UV){return FString::Printf(TEXT("%d:%d"),FMath::RoundToInt(UV.X*100000),FMath::RoundToInt(UV.Y*100000));};
    TMap<FString,FVector> Positions;
    for(const auto& Section:K.RenderSections)
    {
        const auto& Slot=Skin->GetMaterials()[Section.MaterialIndex];
        if(!Slot.MaterialSlotName.ToString().Contains(TEXT("FrostCrystalSword")))continue;
        for(uint32 V=Section.BaseVertexIndex;V<Section.BaseVertexIndex+Section.NumVertices;++V)
            Positions.Add(UVKey(K.StaticVertexBuffers.StaticMeshVertexBuffer.GetVertexUV(V,0)),FVector(K.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(V)));
    }
    TArray<TPair<FVector,FVector>> Matched;
    for(uint32 V=0;V<S.VertexBuffers.PositionVertexBuffer.GetNumVertices();++V)
        if(const auto* P=Positions.Find(UVKey(S.VertexBuffers.StaticMeshVertexBuffer.GetVertexUV(V,0))))
            Matched.Add({FVector(S.VertexBuffers.PositionVertexBuffer.VertexPosition(V)),*P});
    if(Matched.Num()<3)return 3;
    int32 A=0,B=0,C=0;double Distance=-1,Area=-1;
    for(int32 I=0;I<Matched.Num();++I)if(Matched[I].Key.Z>Matched[A].Key.Z)A=I;
    for(int32 I=0;I<Matched.Num();++I){const double D=FVector::DistSquared(Matched[I].Key,Matched[A].Key);if(D>Distance){Distance=D;B=I;}}
    for(int32 I=0;I<Matched.Num();++I){const double V=FVector::CrossProduct(Matched[B].Key-Matched[A].Key,Matched[I].Key-Matched[A].Key).SizeSquared();if(V>Area){Area=V;C=I;}}
    if(Area<1e-6)return 4;
    const FVector SX=Matched[B].Key-Matched[A].Key,SY=Matched[C].Key-Matched[A].Key;
    const FVector KX=Matched[B].Value-Matched[A].Value,KY=Matched[C].Value-Matched[A].Value;
    const FTransform StaticFrame(FRotationMatrix::MakeFromXY(SX,SY).ToQuat(),Matched[A].Key);
    const FTransform SkinFrame(FRotationMatrix::MakeFromXY(KX,KY).ToQuat(),Matched[A].Value,FVector(KX.Length()/SX.Length()));
    const FTransform Canonical=StaticFrame.Inverse()*SkinFrame;
    auto RefTransform=[](USkeletalMesh* Mesh,FName Bone){
        FTransform Result=FTransform::Identity;const auto& Ref=Mesh->GetRefSkeleton();
        for(int32 I=Ref.FindBoneIndex(Bone);I>=0;I=Ref.GetParentIndex(I))Result=Result*Ref.GetRefBonePose()[I];
        return Result;
    };
    if(Arms->GetRefSkeleton().FindBoneIndex(TEXT("WPN_root"))==INDEX_NONE)return 5;
    const FTransform Mount=Canonical.GetRelativeTransform(RefTransform(Arms,TEXT("WPN_root")));
    auto Array=[](std::initializer_list<double> Values){TArray<TSharedPtr<FJsonValue>> Out;for(double V:Values)Out.Add(MakeShared<FJsonValueNumber>(V));return Out;};
    auto SetVector=[&](TSharedPtr<FJsonObject> Obj,const TCHAR* Field,FVector V){Obj->SetArrayField(Field,Array({V.X,V.Y,V.Z}));};
    auto MountObject=MakeShared<FJsonObject>();SetVector(MountObject,TEXT("location_cm"),Mount.GetLocation());SetVector(MountObject,TEXT("scale"),Mount.GetScale3D());
    const FQuat Q=Mount.GetRotation();MountObject->SetArrayField(TEXT("rotation_xyzw"),Array({Q.X,Q.Y,Q.Z,Q.W}));Root->SetObjectField(TEXT("bone_mount"),MountObject);
    auto Blade=Root->GetObjectField(TEXT("slots"))->GetObjectField(TEXT("blade_1"))->GetObjectField(TEXT("factory"));
    SetVector(Blade,TEXT("trace_base_cm"),Canonical.InverseTransformPosition(RefTransform(Skin,TEXT("Blade_Base")).GetLocation()));
    SetVector(Blade,TEXT("trace_tip_cm"),Canonical.InverseTransformPosition(RefTransform(Skin,TEXT("Blade_Tip")).GetLocation()));
    Text.Reset();FJsonSerializer::Serialize(Root.ToSharedRef(),TJsonWriterFactory<>::Create(&Text));
    const FString Target=FPaths::ProjectContentDir()/TEXT("ColdSteelData/frost-sword-modules.json");
    if(!FFileHelper::SaveStringToFile(Text,*Target))return 6;
    FFileHelper::SaveStringToFile(FString::Printf(TEXT("source_vertex_pairs=%d\ncanonical_to_component=%s\ncanonical_to_WPN_root=%s\n"),Matched.Num(),*Canonical.ToString(),*Mount.ToString()),*(Folder/TEXT("mount_authoring.txt")));
    UE_LOG(LogTemp,Display,TEXT("FROST_SWORD_MODULE_CATALOG_AUTHORED %s"),*Target);return 0;
}
