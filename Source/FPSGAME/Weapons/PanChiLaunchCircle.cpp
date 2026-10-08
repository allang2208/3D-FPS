#include "PanChiGuardComponent.h"
#include "PanChiUppercutTuning.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInstanceDynamic.h"

bool PanChiUppercut::TraceSurface(UWorld* World,AActor* Owner,const FVector& Start,const FVector& End,FHitResult& Hit)
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(PanChiLaunchGround),false,Owner);
    for(int32 I=0;I<16;++I)
    {
        if(!World->LineTraceSingleByChannel(Hit,Start,End,ECC_Visibility,Query))return false;
        AActor* Body=Hit.GetActor();
        if(!Body||(!Body->IsA<APawn>()&&!Body->FindComponentByClass<UMonsterCombatComponent>()))return true;
        Query.AddIgnoredActor(Body);
    }
    return false;
}

void UPanChiGuardComponent::BuildLaunchCircle()
{
    if(!CircleMaterial||CircleBuiltAt==ReleaseAt||GetNetMode()==NM_DedicatedServer)return;
    if(!CircleMesh)
    {
        CircleMesh=NewObject<UDynamicMeshComponent>(GetOwner(),TEXT("PanChiUppercutCircle"));
        CircleMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);CircleMesh->SetGenerateOverlapEvents(false);
        CircleMesh->SetCanEverAffectNavigation(false);CircleMesh->SetCastShadow(false);CircleMesh->SetReceivesDecals(false);
        CircleMesh->bAffectDistanceFieldLighting=false;CircleMesh->SetVisibleInRayTracing(false);
        GetOwner()->AddInstanceComponent(CircleMesh);CircleMesh->RegisterComponent();
        CircleMID=UMaterialInstanceDynamic::Create(CircleMaterial,this);CircleMesh->SetMaterial(0,CircleMID);
    }
    using namespace UE::Geometry;
    constexpr int32 Cells=12,Stride=Cells+1;
    bool Valid[Stride*Stride]{};
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    const FVector Center=ReleaseOrigin-FVector(0,0,PanChiUppercut::LaunchLiftCM);
    const FTransform Frame(FRotator(0,ReleaseRotation.Yaw,0),Center);
    for(int32 Y=0;Y<=Cells;++Y)for(int32 X=0;X<=Cells;++X)
    {
        const FVector2f UV(float(X)/Cells,float(Y)/Cells);
        FVector P((UV.X*2.f-1.f)*PanChiUppercut::CircleRadiusCM,(UV.Y*2.f-1.f)*PanChiUppercut::CircleRadiusCM,2.f);
        const FVector WorldP=Frame.TransformPosition(P);FHitResult Floor;
        const int32 I=Y*Stride+X;
        Valid[I]=PanChiUppercut::TraceSurface(GetWorld(),GetOwner(),WorldP+FVector(0,0,55),WorldP-FVector(0,0,60),Floor)
            &&Floor.ImpactNormal.Z>=.6f;
        if(Valid[I])P.Z=Floor.ImpactPoint.Z-Center.Z+2.f;
        Mesh.AppendVertex(FVector3d(P));Mesh.Attributes()->PrimaryUV()->AppendElement(UV);
        Mesh.Attributes()->PrimaryNormals()->AppendElement(FVector3f(0,0,1));
    }
    const auto Add=[&](int32 A,int32 B,int32 C)
    {
        if(!Valid[A]||!Valid[B]||!Valid[C])return;
        const double ZA=Mesh.GetVertex(A).Z,ZB=Mesh.GetVertex(B).Z,ZC=Mesh.GetVertex(C).Z;
        if(FMath::Max3(ZA,ZB,ZC)-FMath::Min3(ZA,ZB,ZC)>35.)return;
        const FIndex3i V(A,B,C);const int32 T=Mesh.AppendTriangle(V);
        if(T>=0){Mesh.Attributes()->PrimaryUV()->SetTriangle(T,V);Mesh.Attributes()->PrimaryNormals()->SetTriangle(T,V);}
    };
    for(int32 Y=0;Y<Cells;++Y)for(int32 X=0;X<Cells;++X)
    {const int32 A=Y*Stride+X;Add(A,A+1,A+Stride);Add(A+1,A+Stride+1,A+Stride);}
    CircleMesh->SetMesh(MoveTemp(Mesh));CircleMesh->SetWorldTransform(Frame);CircleBuiltAt=ReleaseAt;
    CircleMID->SetScalarParameterValue(TEXT("Charge"),ReleaseCharges);
}

void UPanChiGuardComponent::TickLaunchCircle(float Age)
{
    const bool Live=Age>=0.f&&Age<PanChiUppercut::CircleSeconds;
    if(CircleMesh)CircleMesh->SetVisibility(Live&&CircleBuiltAt==ReleaseAt);
    if(!Live||!CircleMID)return;
    const float Fade=FMath::SmoothStep(0.f,.045f,Age)*(1.f-FMath::SmoothStep(PanChiUppercut::CircleFadeStart,PanChiUppercut::CircleSeconds,Age));
    CircleMID->SetScalarParameterValue(TEXT("Seconds"),Age);
    CircleMID->SetScalarParameterValue(TEXT("Opacity"),Fade);
}
