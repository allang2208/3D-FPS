#include "PanChiGuardComponent.h"
#include "PanChiUppercutTuning.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "UDynamicMesh.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace PanChiFlightVisual
{
constexpr int32 Rows=40,Columns=8,Motes=40;
float Seed(int32 I,int32 Salt=0)
{
    uint32 V=uint32(I+1)*747796405u+uint32(Salt+1)*2891336453u;
    V=((V>>((V>>28)+4))^V)*277803737u;V=(V>>22)^V;
    return float(V&0xffffffu)/16777216.f;
}
void Setup(AActor* Owner,UDynamicMeshComponent* Mesh)
{
    Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetGenerateOverlapEvents(false);
    Mesh->SetCanEverAffectNavigation(false);Mesh->SetCastShadow(false);Mesh->SetReceivesDecals(false);
    Mesh->bAffectDistanceFieldLighting=false;Mesh->SetVisibleInRayTracing(false);
    Owner->AddInstanceComponent(Mesh);Mesh->RegisterComponent();Mesh->SetVisibility(false);
}
void Vertex(UE::Geometry::FDynamicMesh3& Mesh,const FVector3d& P,const FVector2f& UV,const FVector2f& Meta)
{
    Mesh.AppendVertex(P);Mesh.Attributes()->PrimaryNormals()->AppendElement(FVector3f(0,0,1));
    Mesh.Attributes()->PrimaryUV()->AppendElement(UV);Mesh.Attributes()->GetUVLayer(1)->AppendElement(Meta);
}
void Triangle(UE::Geometry::FDynamicMesh3& Mesh,int32 A,int32 B,int32 C)
{
    const UE::Geometry::FIndex3i V(A,B,C);const int32 T=Mesh.AppendTriangle(V);if(T<0)return;
    Mesh.Attributes()->PrimaryNormals()->SetTriangle(T,V);Mesh.Attributes()->PrimaryUV()->SetTriangle(T,V);
    Mesh.Attributes()->GetUVLayer(1)->SetTriangle(T,V);
}
}

void UPanChiGuardComponent::BuildSpiritMeshes()
{
    BuildLaunchCircle();
    using namespace PanChiFlightVisual;
    using namespace UE::Geometry;
    if(!SpiritMaterial||!MoteMaterial||GetNetMode()==NM_DedicatedServer)return;
    if(!SpiritMesh)
    {
        SpiritMesh=NewObject<UDynamicMeshComponent>(GetOwner(),TEXT("PanChiFlyingDragon"));Setup(GetOwner(),SpiritMesh);
        SpiritMID=UMaterialInstanceDynamic::Create(SpiritMaterial,this);SpiritMesh->SetMaterial(0,SpiritMID);
        FDynamicMesh3 Mesh;Mesh.EnableAttributes();Mesh.Attributes()->SetNumUVLayers(2);
        // Two rolled surfaces describe a single forward-facing head and body.
        // They curve in three dimensions; they are not ground-projected images.
        for(int32 Plane=0;Plane<2;++Plane)
        {
            const int32 Start=Mesh.MaxVertexID();
            for(int32 Row=0;Row<=Rows;++Row)for(int32 Col=0;Col<=Columns;++Col)
                Vertex(Mesh,FVector3d(Row,Col,Plane),FVector2f(float(Row)/Rows,float(Col)/Columns),FVector2f(Plane,1));
            for(int32 Row=0;Row<Rows;++Row)for(int32 Col=0;Col<Columns;++Col)
            {
                const int32 A=Start+Row*(Columns+1)+Col,B=A+Columns+1;
                Triangle(Mesh,A,B,A+1);Triangle(Mesh,A+1,B,B+1);
            }
        }
        SpiritMesh->SetMesh(MoveTemp(Mesh));
    }
    if(!MoteMesh)
    {
        MoteMesh=NewObject<UDynamicMeshComponent>(GetOwner(),TEXT("PanChiFlightEmbers"));Setup(GetOwner(),MoteMesh);
        MoteMID=UMaterialInstanceDynamic::Create(MoteMaterial,this);MoteMesh->SetMaterial(0,MoteMID);
        FDynamicMesh3 Mesh;Mesh.EnableAttributes();Mesh.Attributes()->SetNumUVLayers(2);
        for(int32 I=0;I<Motes*2;++I)
        {
            const int32 Start=Mesh.MaxVertexID();
            for(int32 C=0;C<4;++C)Vertex(Mesh,FVector3d(C&1,C>>1,I),FVector2f(C&1,C>>1),FVector2f(1,0));
            Triangle(Mesh,Start,Start+1,Start+2);Triangle(Mesh,Start+1,Start+3,Start+2);
        }
        MoteMesh->SetMesh(MoveTemp(Mesh));
    }
    SpiritMID->SetScalarParameterValue(TEXT("Charge"),ReleaseCharges);
    MoteMID->SetScalarParameterValue(TEXT("Charge"),ReleaseCharges);
}

void UPanChiGuardComponent::TickReleaseVisual()
{
    if(GetNetMode()==NM_DedicatedServer)return;
    const float Age=float(Clock()-ReleaseAt);
    TickLaunchCircle(Age);
    const bool bLive=Age>=0.f&&Age<ReleaseVisualSeconds;
    if(SpiritMesh)SpiritMesh->SetVisibility(bLive);
    if(MoteMesh)MoteMesh->SetVisibility(bLive);
    if(!bLive){SetComponentTickInterval(.04f);return;}
    if(!SpiritMesh||!MoteMesh)return;
    using namespace PanChiFlightVisual;
    const float Fade=1.f-FMath::SmoothStep(PanChiUppercut::DragonFadeStart,PanChiUppercut::DragonSeconds,Age);
    const float Visible=FMath::SmoothStep(0.f,.055f,Age)*Fade;
    // Keep the growing tail above its launch plane as the dragon emerges.
    const float Length=FMath::Min(PanChiUppercut::DragonLengthCM,FlightTravelCM);
    const float WidthScale=PanChiUppercut::DragonWidthScale;
    const FTransform Frame(ReleaseRotation,ReleaseOrigin+ReleaseRotation.Vector()*FlightTravelCM);
    SpiritMesh->SetWorldTransform(Frame);MoteMesh->SetWorldTransform(Frame);
    SpiritMID->SetScalarParameterValue(TEXT("Seconds"),Age);
    SpiritMID->SetScalarParameterValue(TEXT("Opacity"),Visible);
    SpiritMID->SetScalarParameterValue(TEXT("Dissolve"),1.f-Fade);
    SpiritMesh->GetDynamicMesh()->EditMesh([&](UE::Geometry::FDynamicMesh3& Mesh)
    {
        for(int32 Plane=0;Plane<2;++Plane)for(int32 Row=0;Row<=Rows;++Row)
        {
            const float U=float(Row)/Rows,Tail=1.f-U;
            const float Wave=Age*15.f-Tail*8.f;
            const float Sway=FMath::Sin(Wave)*37.f*WidthScale*FMath::Sin(Tail*PI);
            const float Lift=FMath::Cos(Wave*.8f)*19.f*WidthScale*FMath::Sin(Tail*PI);
            const float Roll=(Plane==0?.40f:1.97f)+FMath::Sin(Wave)*.18f;
            for(int32 Col=0;Col<=Columns;++Col)
            {
                const float V=float(Col)/Columns,Offset=(V-.5f)*(118.f+ReleaseCharges*4.f)*WidthScale;
                const float Camber=8.f*WidthScale*(1.f-FMath::Square(2.f*V-1.f));
                const FVector3d P(-Tail*Length,Sway+FMath::Cos(Roll)*Offset,Lift+FMath::Sin(Roll)*Offset+Camber);
                Mesh.SetVertex((Plane*(Rows+1)+Row)*(Columns+1)+Col,P);
            }
        }
    },EDynamicMeshChangeType::DeformationEdit,EDynamicMeshAttributeChangeFlags::VertexPositions);
    MoteMesh->GetDynamicMesh()->EditMesh([&](UE::Geometry::FDynamicMesh3& Mesh)
    {
        auto* Meta=Mesh.Attributes()->GetUVLayer(1);
        for(int32 I=0;I<Motes;++I)
        {
            const float S=Seed(I),S2=Seed(I,1),S3=Seed(I,2);
            const float Life=FMath::Frac(Age*2.8f+S),Angle=S2*2.f*PI+Age*2.f;
            const float Radius=(13.f+25.f*S3)*Life*WidthScale;
            const FVector3d Center(-Length*(.20f+.78f*Life),FMath::Cos(Angle)*Radius,FMath::Sin(Angle)*Radius+Life*18.f);
            const float Size=(1.8f+2.8f*S2)*Visible*1.35f;
            for(int32 Cross=0;Cross<2;++Cross)for(int32 C=0;C<4;++C)
            {
                const int32 ID=(I*2+Cross)*4+C;
                const FVector3d Across(0,Cross==0?1:0,Cross==1?1:0);
                Mesh.SetVertex(ID,Center+(Across*((C&1)-.5f)+FVector3d(2,0,0)*((C>>1)-.5f))*Size);
                Meta->SetElement(ID,FVector2f(Life,S));
            }
        }
    },EDynamicMeshChangeType::DeformationEdit,EDynamicMeshAttributeChangeFlags::VertexPositions|EDynamicMeshAttributeChangeFlags::UVs);
}
