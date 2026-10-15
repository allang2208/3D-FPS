#include "M66RecoveryAuditScene.h"
#include "M66IncineratorMonster.h"
#include "M66CorpseSyncComponent.h"
#include "M66CorpseSurface.h"
#include "MonsterRagdollPhysics.h"
#include "MonsterCorpseRagdollComponent.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Materials/MaterialInterface.h"
#include "PhysicsEngine/BodyInstance.h"
#include "PhysicsEngine/SkeletalBodySetup.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

namespace M66RecoveryAuditScene
{
namespace
{
FString Room(){FString Value;FParse::Value(FCommandLine::Get(),TEXT("M66AuditRoom="),Value);return Value;}
FString Output(){FString Value;FParse::Value(FCommandLine::Get(),TEXT("M66RecoveryOutput="),Value);return FPaths::GetPath(Value);}
FVector Vector(const TArray<TSharedPtr<FJsonValue>>& A){return FVector(A[0]->AsNumber(),A[1]->AsNumber(),A[2]->AsNumber());}
void Write(const TSharedRef<FJsonObject>& Data,const TCHAR* Name)
{
    FString Text;FJsonSerializer::Serialize(Data,TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Text));
    FFileHelper::SaveStringToFile(Text+TEXT("\n"),*(Output()/Name),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM,&IFileManager::Get(),FILEWRITE_Append);
}
bool Floor(UWorld* W,const AActor* Ignore,const FVector& At,double Above,double Below,FHitResult& Hit)
{
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    return W->LineTraceSingleByObjectType(Hit,At+FVector(0,0,Above),At-FVector(0,0,Below),Objects,
        FCollisionQueryParams(SCENE_QUERY_STAT(M66StairAudit),true,Ignore))&&Hit.ImpactNormal.Z>.5;
}
TSharedRef<FJsonObject> Surface(AM66IncineratorMonster* M)
{
    auto Result=MakeShared<FJsonObject>();auto* Mesh=M->GetMesh();const auto* Data=Mesh->GetSkeletalMeshRenderData();auto* Skin=Mesh->GetSkinWeightBuffer(0);
    if(!Data||Data->LODRenderData.IsEmpty()||!Skin||!Mesh->GetSkeletalMeshAsset()->GetLODInfo(0)->bAllowCPUAccess)return Result;
    const auto& LOD=Data->LODRenderData[0];if(!LOD.GetNumVertices())return Result;
    TArray<FMatrix44f> Matrices;Mesh->GetCurrentRefToLocalMatrices(Matrices,0);
    TArray<FVector> Points;FBox Box(ForceInit);
    for(const auto& Section:LOD.RenderSections)
    {
        if(Section.bDisabled||!Section.NumVertices)continue;
        const int32 Count=FMath::Min(int32(Section.NumVertices),FMath::Max(32,int32(int64(4096)*Section.NumVertices/LOD.GetNumVertices())));
        for(int32 I=0;I<Count;++I)
        {
            const uint32 V=Section.BaseVertexIndex+uint32(int64(I)*(Section.NumVertices-1)/FMath::Max(1,Count-1));
            const FVector P=Mesh->GetComponentTransform().TransformPosition(FVector(USkinnedMeshComponent::GetSkinnedVertexPosition(Mesh,V,LOD,*Skin,Matrices)));
            Points.Add(P);Box+=P;
        }
    }
    if(Points.IsEmpty())return Result;
    FVector Lowest[144];bool Used[144]={};const FVector Cell=Box.GetSize()/12.;
    for(const auto& P:Points)
    {
        const int32 X=FMath::Clamp(FMath::FloorToInt((P.X-Box.Min.X)/FMath::Max(1.,Cell.X)),0,11),Y=FMath::Clamp(FMath::FloorToInt((P.Y-Box.Min.Y)/FMath::Max(1.,Cell.Y)),0,11),I=Y*12+X;
        if(!Used[I]||P.Z<Lowest[I].Z){Used[I]=true;Lowest[I]=P;}
    }
    double Minimum=1.e9,TreadMinimum=1.e9;int32 Penetrating=0,Contacts=0,Hits=0;FString WorstSurface,WorstPoint;
    for(int32 I=0;I<144;++I)
    {
        if(!Used[I])continue;FHitResult H;
        if(Floor(M->GetWorld(),M,Lowest[I],180,600,H))
        {
            const double Gap=Lowest[I].Z-H.ImpactPoint.Z;FString Surface=GetNameSafe(H.GetComponent());
            if(const auto* C=Cast<UStaticMeshComponent>(H.GetComponent()))Surface=GetPathNameSafe(C->GetStaticMesh());
            if(Gap<Minimum){Minimum=Gap;WorstSurface=Surface;WorstPoint=Lowest[I].ToString();}
            if(!Surface.Contains(TEXT("Rail")))TreadMinimum=FMath::Min(TreadMinimum,Gap);
            ++Hits;
            Penetrating+=Gap < -3.;Contacts+=FMath::Abs(Gap)<3.;
        }
    }
    Result->SetNumberField(TEXT("minimum_gap_cm"),Minimum);Result->SetNumberField(TEXT("penetrating_bins"),Penetrating);
    Result->SetNumberField(TEXT("contact_bins"),Contacts);Result->SetNumberField(TEXT("floor_bins"),Hits);
    Result->SetNumberField(TEXT("tread_minimum_gap_cm"),TreadMinimum);Result->SetStringField(TEXT("worst_surface"),WorstSurface);Result->SetStringField(TEXT("worst_point"),WorstPoint);
    Result->SetNumberField(TEXT("mesh_bottom_z"),Box.Min.Z);Result->SetStringField(TEXT("actor_location"),M->GetActorLocation().ToString());return Result;
}
struct FView
{
    TWeakObjectPtr<ACameraActor> Camera;
    TWeakObjectPtr<AM66IncineratorMonster> Monster;
    TSet<FString> Shots;
    double NextSample=0.;
    double PhaseStarted=0.;
    EM66Reaction LastPhase=EM66Reaction::None;
};
TMap<TWeakObjectPtr<APlayerController>,FView> Views;
}
void Create(UWorld* W)
{
    if(Room().IsEmpty())return;
    for(TActorIterator<AStaticMeshActor> It(W);It;++It)if(It->ActorHasTag(TEXT("M66AuditGeometry")))return;
    FString Path,Text;FParse::Value(FCommandLine::Get(),TEXT("M66AuditScene="),Path);
    TSharedPtr<FJsonObject> Root;
    if(!FFileHelper::LoadFileToString(Text,*Path)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root))
    {UE_LOG(LogTemp,Error,TEXT("M66_STAIR_SCENE missing snapshot %s"),*Path);return;}
    const FString Id=Room()==TEXT("Hall")?TEXT("AbandonedIncineratorHall"):TEXT("AbandonedFlueGasStation");int32 Count=0;
    for(const auto& Value:Root->GetArrayField(TEXT("modules")))
    {
        const auto Module=Value->AsObject();if(Module->GetStringField(TEXT("id"))!=Id)continue;
        for(const auto& Part:Module->GetArrayField(TEXT("parts")))
        {
            const auto P=Part->AsObject();auto* Asset=LoadObject<UStaticMesh>(nullptr,*P->GetStringField(TEXT("mesh")));if(!Asset)continue;
            auto* A=W->SpawnActor<AStaticMeshActor>();A->Tags.Add(TEXT("M66AuditGeometry"));auto* C=A->GetStaticMeshComponent();C->SetMobility(EComponentMobility::Movable);
            C->SetStaticMesh(Asset);C->SetCollisionProfileName(P->GetBoolField(TEXT("collision"))?TEXT("BlockAll"):TEXT("NoCollision"));
            A->SetActorTransform(FTransform(FRotator(0,P->GetNumberField(TEXT("yaw")),0),Vector(P->GetArrayField(TEXT("position"))),Vector(P->GetArrayField(TEXT("scale")))));
            const TArray<TSharedPtr<FJsonValue>>* Materials=nullptr;
            if(P->TryGetArrayField(TEXT("materials"),Materials))for(int32 I=0;I<Materials->Num();++I)
                if(auto* Mat=LoadObject<UMaterialInterface>(nullptr,*(*Materials)[I]->AsString()))C->SetMaterial(I,Mat);
            C->SetMobility(EComponentMobility::Static);++Count;
        }
    }
    // Only diagnostic illumination changes; the saved room meshes/transforms/collision remain intact.
    for(const FVector P:{FVector(0,-500,600),FVector(1100,-300,550),FVector(-1100,-300,550)})
    {
        auto* A=W->SpawnActor<AActor>();auto* Light=NewObject<UPointLightComponent>(A);A->SetRootComponent(Light);Light->RegisterComponent();A->SetActorLocation(P);
        Light->SetIntensity(180000.f);Light->SetAttenuationRadius(3000.f);Light->SetCastShadows(true);
    }
    UE_LOG(LogTemp,Display,TEXT("M66_STAIR_SCENE room=%s parts=%d catalog=%s"),*Id,Count,*Root->GetStringField(TEXT("catalog_sha256")));
}
FVector SpawnPoint(UWorld* W,bool Held)
{
    if(Room().IsEmpty())return FVector(Held?-500:500,0,195);
    const bool Hall=Room()==TEXT("Hall");FVector At(Held?-1:1,0,0);At.X*=Hall?950:1240;At.Y=Hall?-700:-490;At.Z=400;
    FHitResult H;if(Floor(W,nullptr,At,0,1000,H))At.Z=H.ImpactPoint.Z+195.;
    UE_LOG(LogTemp,Display,TEXT("M66_STAIR_SPAWN %s at=%s floor=%s"),Held?TEXT("held"):TEXT("subject"),*At.ToString(),*GetNameSafe(H.GetComponent()));return At;
}
void Observe(APlayerController* PC,AM66IncineratorMonster* M)
{
    if(Room().IsEmpty()||!M)return;auto& V=Views.FindOrAdd(PC);const double Now=M->GetWorld()->GetTimeSeconds();
    if(V.Monster!=M){V.Monster=M;V.Shots.Reset();}
    if(!V.Camera.IsValid())
    {
        V.Camera=M->GetWorld()->SpawnActor<ACameraActor>();auto* C=V.Camera->GetCameraComponent();C->SetFieldOfView(58.f);
        C->PostProcessSettings.bOverride_AutoExposureMethod=true;C->PostProcessSettings.AutoExposureMethod=EAutoExposureMethod::AEM_Histogram;
        C->PostProcessSettings.bOverride_AutoExposureMinBrightness=true;C->PostProcessSettings.AutoExposureMinBrightness=-4.f;
        C->PostProcessSettings.bOverride_AutoExposureMaxBrightness=true;C->PostProcessSettings.AutoExposureMaxBrightness=12.f;
        C->PostProcessSettings.bOverride_AutoExposureBias=true;C->PostProcessSettings.AutoExposureBias=0.f;
        PC->SetViewTarget(V.Camera.Get());
    }
    const FVector Focus=M->GetActorLocation()+FVector(0,0,-70),Eye=Focus+FVector(M->GetActorLocation().X>0?-400:400,600,220);
    V.Camera->SetActorLocationAndRotation(Eye,(Focus-Eye).Rotation());
    const auto Phase=M->ReactionPhase();float Age=0;bool Loop=false;M->ReactionClip(Age,Loop);
    if(V.LastPhase!=Phase){V.LastPhase=Phase;V.PhaseStarted=Now;}
    const double DeathAge=Now-V.PhaseStarted;
    FString Key;
    if(Phase==EM66Reaction::Down)Key=TEXT("down");
    if(Phase==EM66Reaction::GetUp){if(Age>.55)Key=TEXT("getup_early");if(Age>1.6)Key=TEXT("getup_mid");if(Age>2.8)Key=TEXT("getup_end");}
    if(Phase==EM66Reaction::Dying){if(DeathAge>.8)Key=TEXT("death_early");if(DeathAge>3.)Key=TEXT("death_late");if(M->CorpseSync->State().Frozen&&!M->CorpseSync->IsComponentTickEnabled())Key=TEXT("frozen");}
    const bool Shot=!Key.IsEmpty()&&!V.Shots.Contains(Key);
    if(Now>=V.NextSample||Shot)
    {
        V.NextSample=Now+.25;auto Data=Surface(M);Data->SetStringField(TEXT("actor"),M->GetName());Data->SetNumberField(TEXT("time"),Now);
        Data->SetNumberField(TEXT("phase"),uint8(Phase));Data->SetNumberField(TEXT("animation_time"),Age);Data->SetBoolField(TEXT("frozen"),M->CorpseSync->State().Frozen);
        if(Shot)
        {
            Data->SetStringField(TEXT("capture"),Key);auto Pose=MakeShared<FJsonObject>();
            for(FName Name:{FName(TEXT("Bone_000")),FName(TEXT("Bone_001")),FName(TEXT("Bone_006")),FName(TEXT("Bone_010")),FName(TEXT("Bone_015")),FName(TEXT("Bone_037"))})
            {
                const auto T=M->GetMesh()->GetSocketTransform(Name);const FVector P=T.GetLocation();const FQuat Q=T.GetRotation();
                TArray<TSharedPtr<FJsonValue>> Values;for(double N:{P.X,P.Y,P.Z,Q.X,Q.Y,Q.Z,Q.W})Values.Add(MakeShared<FJsonValueNumber>(N));Pose->SetArrayField(Name.ToString(),Values);
            }
            Data->SetObjectField(TEXT("world_pose"),Pose);
        }
        Write(Data,TEXT("surface.jsonl"));
    }
    if(Shot)
    {
        V.Shots.Add(Key);
        if(FParse::Param(FCommandLine::Get(),TEXT("M66AuditRender")))FScreenshotRequest::RequestScreenshot(Output()/(M->GetName()+TEXT("_")+Key+TEXT(".png")),false,false);
    }
}
void CorpseDetails(AM66IncineratorMonster* M)
{
    auto* Mesh=M->GetMesh();auto Data=MakeShared<FJsonObject>();Data->SetStringField(TEXT("actor"),M->GetName());Data->SetNumberField(TEXT("time"),M->GetWorld()->GetTimeSeconds());
    FHitResult OldSupport;Data->SetBoolField(TEXT("support"),MonsterRagdollPhysics::FindSupport(Mesh,OldSupport));Data->SetBoolField(TEXT("settled"),MonsterRagdollPhysics::IsSettled(Mesh,10.f,.3f));
    Data->SetBoolField(TEXT("surface_support"),M66CorpseSurface::FindPhysicalSupport(Mesh,OldSupport));
    Data->SetBoolField(TEXT("frozen"),M->CorpseRagdoll->IsFrozen());TArray<TSharedPtr<FJsonValue>> Bodies;
    for(const auto* B:Mesh->Bodies)
    {
        if(!B||!B->IsInstanceSimulatingPhysics())continue;auto D=MakeShared<FJsonObject>();
        D->SetStringField(TEXT("bone"),B->BodySetup.IsValid()?B->BodySetup->BoneName.ToString():TEXT("none"));D->SetBoolField(TEXT("collision"),B->GetCollisionEnabled()!=ECollisionEnabled::NoCollision);
        D->SetNumberField(TEXT("linear"),B->GetUnrealWorldVelocity().Size());D->SetNumberField(TEXT("angular"),B->GetUnrealWorldAngularVelocityInRadians().Size());
        const FBox Bounds=B->GetBodyBounds();double Best=1.e9,BottomGap=1.e9;FVector Contact=FVector::ZeroVector;
        for(int32 X=0;X<5;++X)for(int32 Y=0;Y<5;++Y)
        {
            const FVector At(FMath::Lerp(Bounds.Min.X,Bounds.Max.X,X/4.),FMath::Lerp(Bounds.Min.Y,Bounds.Max.Y,Y/4.),Bounds.Max.Z+1.);FHitResult H;
            if(Floor(M->GetWorld(),M,At,0,Bounds.GetSize().Z+50.,H))
            {
                FVector Nearest;const float Distance=B->GetDistanceToBody(H.ImpactPoint,Nearest);
                if(Distance>=0&&Distance<Best){Best=Distance;Contact=Nearest;}
                if(X==2&&Y==2)BottomGap=Bounds.Min.Z-H.ImpactPoint.Z;
            }
        }
        D->SetNumberField(TEXT("actual_surface_distance_cm"),Best);D->SetNumberField(TEXT("aabb_center_bottom_gap_cm"),BottomGap);D->SetStringField(TEXT("nearest"),Contact.ToString());Bodies.Add(MakeShared<FJsonValueObject>(D));
    }
    Data->SetArrayField(TEXT("bodies"),Bodies);Write(Data,TEXT("bodies.jsonl"));
}
}
