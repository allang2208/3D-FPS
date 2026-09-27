#include "StaffAssemblyAuditCommandlet.h"
#include "StaffAssembly.h"
#include "StaffCatalog.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Actor.h"
#include "Components/StaticMeshComponent.h"
#include "StaticMeshResources.h"
#include "AssetCompilingManager.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace
{
TSharedPtr<FJsonValue> V(const FVector& P)
{
    return MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{
        MakeShared<FJsonValueNumber>(P.X),MakeShared<FJsonValueNumber>(P.Y),MakeShared<FJsonValueNumber>(P.Z)});
}
void Write(const TSharedPtr<FJsonObject>& O,const FString& Path)
{
    FString S;FJsonSerializer::Serialize(O.ToSharedRef(),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&S));
    FFileHelper::SaveStringToFile(S,*Path,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}
}
int32 UStaffAssemblyAuditCommandlet::Main(const FString& Params)
{
    const FString Out=FPaths::ProjectDir()/TEXT("SourceAssets/ApprenticeStaff20260927/Audit");
    IFileManager::Get().MakeDirectory(*Out,true);
    TArray<TSharedPtr<FJsonValue>> Failures,MeshRows;
    auto Check=[&](bool OK,const FString& Message){if(!OK)Failures.Add(MakeShared<FJsonValueString>(Message));};
    FString Source;TSharedPtr<FJsonObject> Definitions;
    if(!FFileHelper::LoadFileToString(Source,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/staffs.json")))||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Source),Definitions))return 2;
    const auto Definition=Definitions->GetObjectField(TEXT("ue_apprentice_staff"));
    FColdSteelItem Base;Base.Definition=TEXT("ue_apprentice_staff");Base.InstanceId=TEXT("isolated_staff_audit");
    FJsonSerializer::Serialize(Definition.ToSharedRef(),TJsonWriterFactory<>::Create(&Base.Data));
    const auto Catalog=ColdSteelStaff::Catalog();if(!Catalog)return 3;
    TArray<FString> Slots;TArray<TArray<FString>> Options;TArray<TArray<FString>> MeshPaths;
    TSet<FString> AllMeshes;AllMeshes.Add(Definition->GetStringField(TEXT("staff_body_mesh")));AllMeshes.Add(Definition->GetStringField(TEXT("world_mesh")));
    for(const auto& Value:Catalog->GetArrayField(TEXT("columns")))
    {
        const auto Column=Value->AsObject();Slots.Add(Column->GetStringField(TEXT("key")));
        Options.Add({TEXT("")});MeshPaths.Add({Column->GetStringField(TEXT("factory_mesh"))});
        for(const auto& Option:Column->GetArrayField(TEXT("options")))
        {Options.Last().Add(Option->AsObject()->GetStringField(TEXT("id")));MeshPaths.Last().Add(Option->AsObject()->GetStringField(TEXT("mesh")));}
        for(const auto& Path:MeshPaths.Last())if(!Path.IsEmpty())AllMeshes.Add(Path);
    }
    TArray<UStaticMesh*> Loaded;
    for(const FString& Path:AllMeshes)
    {auto* M=LoadObject<UStaticMesh>(nullptr,*Path);Check(M!=nullptr,TEXT("Missing mesh: ")+Path);if(M)Loaded.Add(M);}
    FAssetCompilingManager::Get().FinishAllCompilation();
    for(UStaticMesh* Mesh:Loaded)
    {
        const auto* Data=Mesh->GetRenderData();Check(Data&&Data->LODResources.Num()>0,TEXT("No render data: ")+Mesh->GetName());if(!Data||!Data->LODResources.Num())continue;
        const auto& LOD=Data->LODResources[0];auto O=MakeShared<FJsonObject>();O->SetStringField(TEXT("name"),Mesh->GetName());
        O->SetStringField(TEXT("path"),Mesh->GetPathName());O->SetField(TEXT("min"),V(Mesh->GetBoundingBox().Min));O->SetField(TEXT("max"),V(Mesh->GetBoundingBox().Max));
        TArray<TSharedPtr<FJsonValue>> Vertices,Triangles,UVs,Materials;
        for(uint32 I=0;I<LOD.VertexBuffers.PositionVertexBuffer.GetNumVertices();++I)
        {
            Vertices.Add(V(FVector(LOD.VertexBuffers.PositionVertexBuffer.VertexPosition(I))));
            const auto UV=LOD.VertexBuffers.StaticMeshVertexBuffer.GetVertexUV(I,0);
            UVs.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(UV.X),MakeShared<FJsonValueNumber>(UV.Y)}));
        }
        for(const auto& Section:LOD.Sections)for(uint32 T=0;T<Section.NumTriangles;++T)
        {TArray<TSharedPtr<FJsonValue>> Row;for(int32 I=0;I<3;++I)Row.Add(MakeShared<FJsonValueNumber>(LOD.IndexBuffer.GetIndex(Section.FirstIndex+T*3+I)));Row.Add(MakeShared<FJsonValueNumber>(Section.MaterialIndex));Triangles.Add(MakeShared<FJsonValueArray>(Row));}
        for(const auto& Slot:Mesh->GetStaticMaterials()){Check(Slot.MaterialInterface!=nullptr,TEXT("Missing material: ")+Mesh->GetName());Materials.Add(MakeShared<FJsonValueString>(GetPathNameSafe(Slot.MaterialInterface)));}
        O->SetArrayField(TEXT("vertices"),Vertices);O->SetArrayField(TEXT("uvs"),UVs);O->SetArrayField(TEXT("triangles"),Triangles);O->SetArrayField(TEXT("materials"),Materials);MeshRows.Add(MakeShared<FJsonValueObject>(O));
    }
    auto Geometry=MakeShared<FJsonObject>();Geometry->SetArrayField(TEXT("meshes"),MeshRows);Write(Geometry,Out/TEXT("ue_meshes.json"));
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false).RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::GamePreview,false,TEXT("StaffAssemblyAudit"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    auto* Actor=World->SpawnActor<AActor>();auto* Root=NewObject<UStaticMeshComponent>(Actor,NAME_None,RF_Transient);
    Actor->SetRootComponent(Root);Actor->AddInstanceComponent(Root);Root->RegisterComponentWithWorld(World);
    Root->SetOnlyOwnerSee(true);Root->SetOwnerNoSee(false);Root->SetCastShadow(false);
    Root->SetWorldTransform(FTransform(FRotator(23,41,-15),FVector(51,22,-18),FVector(.7)));
    auto* Unrelated=NewObject<USceneComponent>(Actor,NAME_None,RF_Transient);Actor->AddInstanceComponent(Unrelated);Unrelated->SetupAttachment(Root);Unrelated->RegisterComponentWithWorld(World);
    int32 Count=1;for(const auto& Row:Options)Count*=Row.Num();int32 Checked=0;
    auto Case=[&](int32 Id,const ColdSteelStaff::FParts& Draft,const TArray<int32>& Choice)
    {
        const FColdSteelItem Item=ColdSteelStaff::Resolve(Base,&Draft);const FString Prefix=FString::Printf(TEXT("case %d: "),Id);
        const auto Parts=ColdSteelStaff::Installed(Item);Check(Parts.Num()==Draft.Num(),Prefix+TEXT("normalized selection count"));
        TArray<FString> Expected;Expected.Add(Definition->GetStringField(TEXT("staff_body_mesh")));
        for(int32 S=0;S<Slots.Num();++S)
        {
            const FString P=ColdSteelInventory::Text(Item,*(TEXT("staff_part_")+Slots[S]+TEXT("_mesh")));
            Check(P==MeshPaths[S][Choice[S]],Prefix+TEXT("wrong mesh for ")+Slots[S]);if(!P.IsEmpty())Expected.Add(P);
        }
        Check(ColdSteelStaffAssembly::Apply(Root,Item),Prefix+TEXT("Apply failed"));const auto Components=ColdSteelStaffAssembly::Components(Root);
        Check(Components.Num()==Expected.Num(),Prefix+TEXT("stale or missing components"));
        for(auto* C:Components)
        {
            const FString P=GetPathNameSafe(C->GetStaticMesh());Check(Expected.RemoveSingle(P)==1,Prefix+TEXT("unexpected/duplicate mesh: ")+P);
            if(C!=Root){Check(C->GetAttachParent()==Root&&C->GetRelativeTransform().Equals(FTransform::Identity),Prefix+TEXT("attachment mismatch"));Check(C->bOnlyOwnerSee&&!C->bOwnerNoSee&&!C->CastShadow,Prefix+TEXT("visibility mismatch"));}
        }
        Check(Expected.IsEmpty(),Prefix+TEXT("missing expected mesh"));Check(IsValid(Unrelated)&&Unrelated->GetAttachParent()==Root,Prefix+TEXT("unrelated child destroyed"));++Checked;
    };
    for(int32 Id=0;Id<Count;++Id)
    {
        int32 N=Id;ColdSteelStaff::FParts Draft;TArray<int32> Choice;
        for(int32 S=0;S<Slots.Num();++S){const int32 I=N%Options[S].Num();N/=Options[S].Num();Choice.Add(I);if(I)Draft.Add(Slots[S],Options[S][I]);}
        Case(Id,Draft,Choice);
    }
    Case(Count,ColdSteelStaff::FParts(),TArray<int32>{0,0,0,0,0,0});
    Check(FMath::IsNearlyEqual(ColdSteelStaffAssembly::Bounds(Root).GetSize().Z,160.,.01),TEXT("factory assembled length not 160 cm"));
    ColdSteelStaffAssembly::Clear(Root);Check(ColdSteelStaffAssembly::Components(Root).Num()==1,TEXT("Clear left staff parts"));Check(IsValid(Unrelated),TEXT("Clear removed unrelated component"));
    auto Report=MakeShared<FJsonObject>();Report->SetNumberField(TEXT("combinations"),Count);Report->SetNumberField(TEXT("applies_including_final_factory_restore"),Checked);
    Report->SetNumberField(TEXT("loaded_meshes"),Loaded.Num());Report->SetArrayField(TEXT("failures"),Failures);Report->SetBoolField(TEXT("player_save_loaded_or_written"),false);
    Write(Report,Out/TEXT("ue_assembly_report.json"));UE_LOG(LogTemp,Display,TEXT("STAFF_AUDIT_DONE combinations=%d apply=%d meshes=%d failures=%d"),Count,Checked,Loaded.Num(),Failures.Num());
    World->DestroyWorld(false);return Failures.IsEmpty()?0:1;
}
