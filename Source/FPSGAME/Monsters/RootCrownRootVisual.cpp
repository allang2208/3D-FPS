#include "RootCrownRootField.h"
#include "RootCrownRigPreview.h"
#include "RootCrownSlashTiming.h"
#include "BellowSacCameraShake.h"
#include "../Weapons/FPSImpactFXSubsystem.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundAttenuation.h"
#include "Engine/World.h"

namespace RootCrownMineVisual
{
using namespace UE::Geometry;
void Vertex(FDynamicMesh3& Geometry,const FVector& P,const FVector2f& UV)
{
    Geometry.AppendVertex(FVector3d(P));Geometry.Attributes()->PrimaryUV()->AppendElement(UV);
    Geometry.Attributes()->PrimaryNormals()->AppendElement(FVector3f(0,0,1));
}
void Triangle(FDynamicMesh3& Geometry,int32 A,int32 B,int32 C)
{
    const FIndex3i Indices(A,C,B);const int32 T=Geometry.AppendTriangle(Indices);
    if(T<0)return;
    Geometry.Attributes()->PrimaryUV()->SetTriangle(T,Indices);
    const FVector3d N=FVector3d::CrossProduct(Geometry.GetVertex(C)-Geometry.GetVertex(A),Geometry.GetVertex(B)-Geometry.GetVertex(A)).GetSafeNormal();
    auto* Normals=Geometry.Attributes()->PrimaryNormals();
    const int32 NA=Normals->AppendElement(FVector3f(N)),NB=Normals->AppendElement(FVector3f(N)),NC=Normals->AppendElement(FVector3f(N));
    Normals->SetTriangle(T,FIndex3i(NA,NB,NC));
}
FDynamicMesh3 Vein(const FRootCrownGroundPath& Path,const FVector& Origin)
{
    FDynamicMesh3 Geometry;Geometry.EnableAttributes();const int32 Count=Path.Points.Num();
    for(int32 I=0;I<Count;++I)
    {
        const FVector P=FVector(Path.Points[I])-Origin;
        const FVector Along=FVector(Path.Points[FMath::Min(I+1,Count-1)])-FVector(Path.Points[FMath::Max(0,I-1)]);
        const FVector Side=FVector::CrossProduct(Along.GetSafeNormal2D(),FVector::UpVector)*4.f;
        const float U=float(I)/FMath::Max(1,Count-1);
        Vertex(Geometry,P-Side+FVector(0,0,1.5f),FVector2f(U,0));
        Vertex(Geometry,P+Side+FVector(0,0,1.5f),FVector2f(U,1));
    }
    for(int32 I=1;I<Count;++I){const int32 A=(I-1)*2,B=I*2;Triangle(Geometry,A,B,B+1);Triangle(Geometry,A,B+1,A+1);}
    return Geometry;
}
}
void ARootCrownRootField::BuildSignal(int32 Index)
{
    using namespace RootCrownMineVisual;
    if(!Signals.IsValidIndex(Index)||!Mines.IsValidIndex(Index))return;
    const FVector Center=Mines[Index].Position,Normal=Mines[Index].Normal,Origin=GetActorLocation();
    FVector Tangent,Bitangent;Normal.FindBestAxisVectors(Tangent,Bitangent);
    FDynamicMesh3 Geometry;Geometry.EnableAttributes();Vertex(Geometry,Center-Origin+Normal*2.f,FVector2f(.5f,.5f));
    constexpr int32 Segments=32;
    for(int32 I=0;I<=Segments;++I)
    {
        const float Angle=I*2.f*PI/Segments;const FVector Direction=Tangent*FMath::Cos(Angle)+Bitangent*FMath::Sin(Angle);
        FVector Point=Center+Direction*BlastRadius;FHitResult Block;
        if(TraceScene(Center+Normal*8.f,Point+Normal*8.f,Block))Point=Block.ImpactPoint-Normal*8.f-Direction*3.f;
        FVector Floor;if(!FloorAt(Point,Floor)||FMath::Abs(Floor.Z-Center.Z)>60.f)Floor=Center;
        const FVector Delta=Floor-Center;
        const FVector2f UV(.5f+.5f*FVector::DotProduct(Delta,Tangent)/BlastRadius,.5f+.5f*FVector::DotProduct(Delta,Bitangent)/BlastRadius);
        Vertex(Geometry,Floor-Origin+Normal*2.f,UV);
    }
    for(int32 I=1;I<=Segments;++I)Triangle(Geometry,0,I,I+1);
    Signals[Index]->SetMesh(MoveTemp(Geometry));
}
void ARootCrownRootField::BuildPresentation()
{
    if(!Source||Paths.Num()!=3||Mines.Num()!=3||!Source->RootFleshMaterial||!Source->RootWarningMaterial||!Source->MineSignalMaterial)return;
    const FVector Origin=GetActorLocation();
    auto Make=[&](const TCHAR* Prefix,int32 Index,UMaterialInterface* Material)
    {
        auto* Component=NewObject<UDynamicMeshComponent>(this,*FString::Printf(TEXT("%s%d"),Prefix,Index));
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);Component->SetCanEverAffectNavigation(false);
        Component->SetCastShadow(false);Component->SetReceivesDecals(false);Component->SetVisibleInRayTracing(false);
        Component->SetComponentTickEnabled(false);Component->bAffectDistanceFieldLighting=false;
        AddInstanceComponent(Component);Component->RegisterComponent();Component->SetWorldLocation(Origin);Component->SetMaterial(0,Material);
        return Component;
    };
    for(int32 I=0;I<3;++I)
    {
        auto* Vein=Make(TEXT("PlantVein"),I,Source->RootWarningMaterial);
        Vein->SetMesh(RootCrownMineVisual::Vein(Paths[I],Origin));Veins.Add(Vein);
        auto* VeinMaterial=UMaterialInstanceDynamic::Create(Source->RootWarningMaterial,this);Vein->SetMaterial(0,VeinMaterial);VeinMIDs.Add(VeinMaterial);
        auto* Signal=Make(TEXT("MineSignal"),I,Source->MineSignalMaterial);Signals.Add(Signal);
        auto* SignalMaterial=UMaterialInstanceDynamic::Create(Source->MineSignalMaterial,this);Signal->SetMaterial(0,SignalMaterial);SignalMIDs.Add(SignalMaterial);BuildSignal(I);
        auto* Flesh=UMaterialInstanceDynamic::Create(Source->RootFleshMaterial,this);Knots[I]->SetMaterial(0,Flesh);KnotMIDs.Add(Flesh);
        auto* Pieces=NewObject<UInstancedStaticMeshComponent>(this,*FString::Printf(TEXT("MineFragments%d"),I));
        Pieces->SetStaticMesh(Source->RootKnotMesh);Pieces->SetMaterial(0,Source->RootFleshMaterial);
        Pieces->SetCollisionEnabled(ECollisionEnabled::NoCollision);Pieces->SetCanEverAffectNavigation(false);
        Pieces->SetCastShadow(false);Pieces->SetVisibleInRayTracing(false);Pieces->bAffectDistanceFieldLighting=false;
        Pieces->bReceivesDecals=false;Pieces->SetComponentTickEnabled(false);AddInstanceComponent(Pieces);Pieces->RegisterComponent();
        for(int32 J=0;J<10;++J)Pieces->AddInstance(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector));
        Pieces->SetVisibility(false);Fragments.Add(Pieces);
    }
    bPresentationBuilt=true;
}
void ARootCrownRootField::PresentBurst(int32 Index,bool Damaging)
{
    if(Clock()-Mines[Index].ChangedAt>.35)return;
    const FVector Origin=Mines[Index].Position,Normal=Mines[Index].Normal;
    auto* FX=GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>();
    if(!Damaging)
    {
        if(Source->RootBreakSound)
        {
            auto* Attenuation=NewObject<USoundAttenuation>(this);Attenuation->Attenuation.bAttenuate=true;Attenuation->Attenuation.bSpatialize=true;
            Attenuation->Attenuation.FalloffDistance=1000.f;
            UGameplayStatics::PlaySoundAtLocation(this,Source->RootBreakSound,Origin,.8f,1.f,0.f,Attenuation);
        }
        return;
    }
    if(FX)FX->PlaySacImpact(Origin,true);
    bool Spawned=false;
    for(FConstPlayerControllerIterator It=GetWorld()->GetPlayerControllerIterator();It;++It)
    {
        auto* PC=It->Get();APawn* Player=PC?PC->GetPawn():nullptr;
        if(!PC||!PC->IsLocalController()||!Player)continue;
        if(FX&&!Spawned)if(auto* Camera=Player->FindComponentByClass<UCameraComponent>())
        {FX->SpawnSacRupture(Origin,Normal,BlastRadius,Camera);Spawned=true;}
        float Distance;
        if(ExposureTo(Index,Player,Distance)&&Distance<450.f&&PC->PlayerCameraManager)
            PC->PlayerCameraManager->StartCameraShake(UBellowSacCameraShake::StaticClass(),.55f*FMath::Square(1.f-Distance/450.f));
    }
}
void ARootCrownRootField::UpdatePresentation(float T)
{
    if(!bPresentationBuilt||Mines.Num()!=3)return;
    const double Now=Clock();
    for(int32 I=0;I<3;++I)
    {
        const auto Phase=Mines[I].Phase;const float Since=FMath::Max(0.f,float(Now-Mines[I].ChangedAt));
        if(Presented[I]!=Phase)
        {
            Presented[I]=Phase;
            if(Phase==ERootCrownMinePhase::Triggered)BuildSignal(I);
            if(Phase==ERootCrownMinePhase::Exploded||Phase==ERootCrownMinePhase::Disarmed)PresentBurst(I,Phase==ERootCrownMinePhase::Exploded);
        }
        const bool Live=Phase<=ERootCrownMinePhase::Triggered;
        const float PlantFade=1.f-FMath::SmoothStep(RootCrownRootTiming::Warning,RootCrownRootTiming::Warning+.6f,T);
        Veins[I]->SetVisibility(Phase!=ERootCrownMinePhase::Expired&&PlantFade>0.f);
        VeinMIDs[I]->SetScalarParameterValue(TEXT("Opacity"),PlantFade*(.75f+.25f*FMath::Sin(T*12.f-I*1.8f)));
        VeinMIDs[I]->SetScalarParameterValue(TEXT("Growth"),FMath::SmoothStep(0.f,.7f,T));VeinMIDs[I]->SetScalarParameterValue(TEXT("Seconds"),T);
        const float Fuse=Phase==ERootCrownMinePhase::Triggered?FMath::Clamp(Since/FuseSeconds,0.f,1.f):0.f;
        const float Pulse=1.f+.025f*FMath::Sin(T*5.f-I*2.1f)+Fuse*.3f+Fuse*.025f*FMath::Sin(Since*42.f);
        const float Fade=Phase==ERootCrownMinePhase::Expired?1.f-FMath::SmoothStep(0.f,.35f,Since):1.f;
        const float Growth=FMath::SmoothStep(.05f,1.6f,T);
        Knots[I]->SetWorldScale3D(FVector(Pulse,Pulse,1.f+Fuse*.4f)*FMath::Max(.001f,Fade*Growth));
        Knots[I]->SetVisibility(Live||(Phase==ERootCrownMinePhase::Expired&&Fade>0.f));
        KnotMIDs[I]->SetScalarParameterValue(TEXT("Signal"),Phase==ERootCrownMinePhase::Triggered?.4f+Fuse*.8f:.08f+.04f*FMath::Sin(T*5.f));
        const bool Burst=Phase==ERootCrownMinePhase::Exploded;
        const bool Primed=Phase==ERootCrownMinePhase::Triggered;
        const bool Ring=Phase==ERootCrownMinePhase::Armed||Primed||(Burst&&Since<.32f);
        Signals[I]->SetVisibility(Ring);
        SignalMIDs[I]->SetScalarParameterValue(TEXT("Radius"),Burst?FMath::Clamp(Since/.22f,.01f,1.f):Primed?1.f:TriggerRadius/BlastRadius);
        SignalMIDs[I]->SetScalarParameterValue(TEXT("Opacity"),Burst?.9f*(1.f-FMath::SmoothStep(.08f,.32f,Since)):Primed?.65f+.25f*FMath::Sin(Since*18.f):.18f);
        SignalMIDs[I]->SetVectorParameterValue(TEXT("Tint"),Burst?FLinearColor(.9f,.83f,.72f):Primed?FLinearColor(.9f,.10f,.025f):FLinearColor(.5f,.025f,.018f));
        const bool Pieces=(Burst||Phase==ERootCrownMinePhase::Disarmed)&&Since<.95f;
        Fragments[I]->SetVisibility(Pieces);
        if(Pieces)
        {
            const FVector Normal=Mines[I].Normal;FVector Tangent,Bitangent;Normal.FindBestAxisVectors(Tangent,Bitangent);
            const float Strength=Burst?1.f:.35f;
            for(int32 J=0;J<10;++J)
            {
                const float Angle=(J+.17f*I)*2.f*PI/10.f;
                const FVector Velocity=(Tangent*FMath::Cos(Angle)+Bitangent*FMath::Sin(Angle))*(150.f+(J%4)*55.f)+Normal*(110.f+(J%3)*55.f);
                const FVector Offset=Velocity*Since*Strength+FVector(0,0,-350.f*Since*Since);
                const float PieceFade=FVector::DotProduct(Offset,Normal)<-4.f?0.f:1.f-FMath::SmoothStep(.5f,.95f,Since);
                Fragments[I]->UpdateInstanceTransform(J,FTransform(FRotator(Since*440.f,J*51.f,Since*260.f),
                    FVector(Mines[I].Position)+Normal*10.f+Offset,FVector(.15f,.09f,.18f)*PieceFade),true,J==9,true);
            }
        }
    }
}
