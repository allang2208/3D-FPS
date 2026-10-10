#include "SpellbookComponent.h"
#include "SpellbookFocusMotion.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace
{
using namespace UE::Geometry;
void GoldVertex(FDynamicMesh3& Mesh,const FVector3d& Position,const FVector2f& UV)
{
    Mesh.AppendVertex(Position);
    Mesh.Attributes()->PrimaryNormals()->AppendElement(FVector3f(0,0,1));
    Mesh.Attributes()->PrimaryUV()->AppendElement(UV);
}
void GoldTriangle(FDynamicMesh3& Mesh,int32 A,int32 B,int32 C)
{
    const int32 Id=Mesh.AppendTriangle(A,B,C);
    Mesh.Attributes()->PrimaryNormals()->SetTriangle(Id,FIndex3i(A,B,C));
    Mesh.Attributes()->PrimaryUV()->SetTriangle(Id,FIndex3i(A,B,C));
}
FDynamicMesh3 GoldOrbits()
{
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();constexpr int32 Segments=96;
    // Build once on equip. The shader moves the light; no per-frame mesh uploads.
    for(int32 Layer=0;Layer<2;++Layer)
    {
        const int32 Start=Mesh.VertexCount();
        for(int32 I=0;I<=Segments;++I)
        {
            const float U=float(I)/Segments,A=U*2.f*PI;
            for(int32 Side=0;Side<2;++Side)
            {
                const float Width=(Side-.5f)*.85f;
                const float X=(21.f+Layer*1.8f+Width)*FMath::Cos(A);
                const float Y=(16.f+Layer*1.2f+Width)*FMath::Sin(A);
                const float Z=Layer?3.5f+5.5f*FMath::Cos(A):2.4f+2.f*FMath::Sin(A);
                GoldVertex(Mesh,FVector3d(X,Y,Z),FVector2f(U+Layer*2.f,Side));
            }
        }
        for(int32 I=0;I<Segments;++I)
        {
            const int32 V=Start+I*2;
            GoldTriangle(Mesh,V,V+2,V+3);GoldTriangle(Mesh,V,V+3,V+1);
        }
    }
    for(int32 I=0;I<16;++I)
    {
        const float A=I*2.f*PI/16.f+.13f;
        const FVector3d Center((21.8f+(I%3)*.6f)*FMath::Cos(A),17.5f*FMath::Sin(A),4.f+3.f*FMath::Sin(A*3.f));
        const float Size=.38f+(I%3)*.12f;const int32 Start=Mesh.VertexCount();
        GoldVertex(Mesh,Center+FVector3d(-Size,-Size,0),FVector2f(I*2.f,2));
        GoldVertex(Mesh,Center+FVector3d(Size,-Size,0),FVector2f(I*2.f+1,2));
        GoldVertex(Mesh,Center+FVector3d(Size,Size,0),FVector2f(I*2.f+1,3));
        GoldVertex(Mesh,Center+FVector3d(-Size,Size,0),FVector2f(I*2.f,3));
        GoldTriangle(Mesh,Start,Start+1,Start+2);GoldTriangle(Mesh,Start,Start+2,Start+3);
    }
    return Mesh;
}
}

void USpellbookComponent::CreateFocusGold(UMaterialInterface* Material)
{
    if(FocusGold||!Material||!FocusBook)return;
    auto* Pawn=GetOwner();FocusGold=NewObject<UDynamicMeshComponent>(Pawn,TEXT("SpellbookGoldOrbits"));
    Pawn->AddInstanceComponent(FocusGold);FocusGold->SetupAttachment(FocusBook);
    FocusGold->SetCollisionEnabled(ECollisionEnabled::NoCollision);FocusGold->SetGenerateOverlapEvents(false);
    FocusGold->SetCanEverAffectNavigation(false);FocusGold->SetCastShadow(false);
    FocusGold->bReceivesDecals=false;FocusGold->SetVisibility(false);FocusGold->RegisterComponent();
    FocusGold->SetComponentTickEnabled(false);FocusGold->SetMesh(GoldOrbits());
    FocusGoldMaterial=UMaterialInstanceDynamic::Create(Material,this);
    FocusGoldMaterial->SetScalarParameterValue(TEXT("Fade"),0.f);FocusGold->SetMaterial(0,FocusGoldMaterial);
}

void USpellbookComponent::ShowFocusGold(bool Visible)
{
    if(FocusGold&&FocusGold->IsVisible()!=Visible)FocusGold->SetVisibility(Visible);
}

void USpellbookComponent::PresentFocusGold()
{
    if(!FocusGoldMaterial)return;
    namespace Motion=SpellbookFocusMotion;
    GoldFade=Motion::Ease(.18f,.85f,OpenAlpha);
    const float Activity=FMath::Abs(FMath::Sin(2.f*PI*PagePhase/Motion::PageCycle));
    FocusGoldMaterial->SetScalarParameterValue(TEXT("GoldAge"),FocusAge+(bFocusClosing?CloseAge:0.f));
    FocusGoldMaterial->SetScalarParameterValue(TEXT("Fade"),GoldFade);
    FocusGoldMaterial->SetScalarParameterValue(TEXT("PageActivity"),Activity);
}
