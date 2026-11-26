// Included by the editor-only oil review. Lit, offscreen captures use the production meshes and materials.
#include "Engine/SceneCapture2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/TextureCube.h"
#include "Engine/StaticMesh.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Materials/MaterialInterface.h"
#include "ImageUtils.h"
#include "RenderingThread.h"

namespace
{
struct FOilReviewCapture
{
    UWorld* World=nullptr;
    ASceneCapture2D* Camera=nullptr;
    UTextureRenderTarget2D* Target=nullptr;
    UDynamicMeshComponent* Ground=nullptr;
    FString Dir;
    TArray<UPrimitiveComponent*> Scenery;
    void Start(UWorld* W,const FString& Out)
    {
        World=W;Dir=Out;
        auto* Stage=W->SpawnActor<AActor>();
        auto Light=[&](FRotator Angle,float Power,FLinearColor Color)
        {
            auto* L=NewObject<UDirectionalLightComponent>(Stage);Stage->AddInstanceComponent(L);
            L->SetMobility(EComponentMobility::Movable);L->SetIntensity(Power);L->SetLightColor(Color);
            L->SetWorldRotation(Angle);L->RegisterComponent();
        };
        Light(FRotator(-52,37,0),5.2f,FLinearColor(1.,.89,.75));
        Light(FRotator(-46,-130,0),1.65f,FLinearColor(.83,.89,1.));
        auto* Sky=NewObject<USkyLightComponent>(Stage);Stage->AddInstanceComponent(Sky);
        Sky->SetMobility(EComponentMobility::Movable);Sky->SourceType=SLS_SpecifiedCubemap;
        Sky->SetCubemap(LoadObject<UTextureCube>(nullptr,TEXT("/Game/UI/GunsmithWorkbench/T_StudioEnvironment")));
        Sky->SetIntensity(.8f);Sky->RegisterComponent();Sky->RecaptureSky();USkyLightComponent::UpdateSkyCaptureContents(W);
        Ground=NewObject<UDynamicMeshComponent>(Stage);Stage->AddInstanceComponent(Ground);Ground->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        using namespace UE::Geometry;
        FDynamicMesh3 M;M.EnableAttributes();
        auto* UV=M.Attributes()->PrimaryUV();auto* N=M.Attributes()->PrimaryNormals();
        for(FVector2D P:{FVector2D(-1800,-1800),FVector2D(1800,-1800),FVector2D(1800,1800),FVector2D(-1800,1800)})
        {M.AppendVertex(FVector(P,-.2));UV->AppendElement(FVector2f(P.X/165.,P.Y/165.));N->AppendElement(FVector3f::UnitZ());}
        for(FIndex3i V:{FIndex3i(0,2,1),FIndex3i(0,3,2)}){int T=M.AppendTriangle(V);UV->SetTriangle(T,V);N->SetTriangle(T,V);}
        Ground->SetMesh(MoveTemp(M));
        Ground->SetMaterial(0,LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WorldGeneration/TemperateHills/VillageWindmill/Yard/Materials/MI_MillEarth")));
        Ground->RegisterComponent();
        auto* Stone=W->SpawnActor<AStaticMeshActor>();Stone->SetMobility(EComponentMobility::Movable);
        auto* StoneMesh=Stone->GetStaticMeshComponent();
        StoneMesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
        StoneMesh->SetMaterial(0,LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelFooting")));
        Stone->SetActorScale3D(FVector(.58,1.8,1.45));Stone->SetActorLocation(FVector(414,55,72.5));Scenery.Add(StoneMesh);
        auto* Grass=NewObject<UInstancedStaticMeshComponent>(Stage);Stage->AddInstanceComponent(Grass);
        Grass->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Game/WorldGeneration/TemperateHills/RiverEcologyDense/SM_RiverDense_lowGrass_07_02_SM")));
        if(Grass->GetStaticMesh())
        {
            Grass->SetCollisionEnabled(ECollisionEnabled::NoCollision);Grass->RegisterComponent();
            FRandomStream Scatter(4817);
            const double BaseScale=22./FMath::Max(1.,Grass->GetStaticMesh()->GetBoundingBox().GetSize().Z);
            for(int I=0;I<65;++I)
            {
                const FVector At(Scatter.FRandRange(-60,850),Scatter.FRandRange(130,560),0.);
                Grass->AddInstance(FTransform(FRotator(0,Scatter.FRandRange(-180,180),0),At,FVector(BaseScale*Scatter.FRandRange(.65,1.3))));
            }
            Scenery.Add(Grass);
        }
        Camera=W->SpawnActor<ASceneCapture2D>();
        auto* C=Camera->GetCaptureComponent2D();
        C->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
        C->bCaptureEveryFrame=false;C->bCaptureOnMovement=false;C->CaptureSource=SCS_FinalColorLDR;
        C->ShowFlags.SetMotionBlur(false);C->ShowFlags.SetTemporalAA(false);C->ShowFlags.SetBloom(true);
        auto& PP=C->PostProcessSettings;PP.bOverride_AutoExposureMethod=true;PP.AutoExposureMethod=AEM_Manual;
        PP.bOverride_AutoExposureApplyPhysicalCameraExposure=true;PP.AutoExposureApplyPhysicalCameraExposure=false;
        PP.bOverride_AutoExposureBias=true;PP.AutoExposureBias=0.;
        Target=NewObject<UTextureRenderTarget2D>(Camera);Target->InitCustomFormat(864,486,PF_B8G8R8A8,false);
        Target->UpdateResourceImmediate(true);C->TextureTarget=Target;
    }
    void Shot(const TCHAR* Label,FVector From,FRotator Rot,float FOV,TArray<UPrimitiveComponent*> Parts,AActor* Actor=nullptr)
    {
        if(!Camera)return;
        auto* C=Camera->GetCaptureComponent2D();C->ClearShowOnlyComponents();C->ShowOnlyComponent(Ground);
        for(auto* Component:Scenery)C->ShowOnlyComponent(Component);
        if(Actor)C->ShowOnlyActorComponents(Actor);
        TArray<bool> Flags;
        for(auto* Part:Parts){Flags.Add(Part->bOnlyOwnerSee);Part->SetOnlyOwnerSee(false);C->ShowOnlyComponent(Part);}
        Camera->SetActorLocationAndRotation(From,Rot);C->FOVAngle=FOV;
        FAssetCompilingManager::Get().FinishAllCompilation();
        World->SendAllEndOfFrameUpdates();FlushRenderingCommands();C->CaptureScene();FlushRenderingCommands();
        TArray<FColor> Pixels;
        if(Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels))
        {
            for(auto& Pixel:Pixels)Pixel.A=255;
            TArray64<uint8> PNG;FImageUtils::PNGCompressImageArray(864,486,Pixels,PNG);
            FFileHelper::SaveArrayToFile(PNG,*(Dir/(FString(Label)+TEXT(".png"))));
        }
        for(int I=0;I<Parts.Num();++I)Parts[I]->SetOnlyOwnerSee(Flags[I]);
    }
};
}
