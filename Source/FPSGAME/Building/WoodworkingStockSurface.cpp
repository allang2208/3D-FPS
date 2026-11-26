#include "WoodworkingStockSurface.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"

namespace WoodworkingStockSurface
{
using FMesh=UE::Geometry::FDynamicMesh3;

void Quad(FMesh& Mesh,FVector3d A,FVector3d B,FVector3d C,FVector3d D,FVector3f Normal,FVector4f Color,double UVScale)
{
    if(FVector3d::DotProduct(FVector3d::CrossProduct(B-A,C-A),FVector3d(Normal))>0)Swap(B,D);
    auto* Normals=Mesh.Attributes()->PrimaryNormals();auto* UVs=Mesh.Attributes()->PrimaryUV();auto* Colors=Mesh.Attributes()->PrimaryColors();
    const int32 Start=Mesh.VertexCount();
    for(const FVector3d P:{A,B,C,D})
    {
        // Grain follows the board's X axis; vertical faces must include thickness.
        const FVector2d UV=FMath::Abs(Normal.Z)>=.5f?FVector2d(P.X,P.Y):
            FMath::Abs(Normal.X)>.5f?FVector2d(P.Y,P.Z):FVector2d(P.X,P.Z);
        Mesh.AppendVertex(P);Normals->AppendElement(Normal);UVs->AppendElement(FVector2f(UV/UVScale));Colors->AppendElement(Color);
    }
    for(const auto Indices:{UE::Geometry::FIndex3i(Start,Start+1,Start+2),UE::Geometry::FIndex3i(Start,Start+2,Start+3)})
    {
        const int32 ID=Mesh.AppendTriangle(Indices);Normals->SetTriangle(ID,Indices);UVs->SetTriangle(ID,Indices);Colors->SetTriangle(ID,Indices);
    }
}

bool Build(FMesh& Mesh,const TArray<uint8>& Wood,int32 W,int32 H,double Units,double Thickness,
    const WoodworkingStockGeometry::FPlan& Plan,int32 QuadBudget)
{
    const int32 BaseQuads=int32(Plan.Faces.size()*2+Plan.Edges.size());
    if(!Plan.Valid||QuadBudget<BaseQuads)return false;
    auto Solid=[&](int32 X,int32 Y){return X>=0&&Y>=0&&X<W&&Y<H&&Wood[Y*W+X]!=0;};
    auto P=[&](double X,double Y,double Z){return FVector3d((X-W*.5)*Units,-(Y-H*.5)*Units,Z);};
    // Stock vertex color is surface data: R=end grain, G=fresh cut, B=reserved.
    const FVector4f Face(0,0,0,1);
    TArray<uint8> Interior;Interior.Init(0,W*H);
    TArray<FIntPoint> Boundary;Boundary.Reserve(FMath::Min(Plan.Perimeter*2,4096));
    bool Detailed=true;
    for(int32 Y=0;Y<H&&Detailed;++Y)for(int32 X=0;X<W;++X)
    {
        if(!Solid(X,Y))continue;
        bool Inside=true;
        for(int32 DY=-1;DY<=1&&Inside;++DY)for(int32 DX=-1;DX<=1;++DX)
            if(!Solid(X+DX,Y+DY)){Inside=false;break;}
        if(Inside)Interior[Y*W+X]=1;
        else
        {
            Boundary.Emplace(X,Y);
            // Optional surface detail must not cause the world view to fall back to 2D.
            if(Boundary.Num()*9+BaseQuads>QuadBudget){Detailed=false;break;}
        }
    }
    WoodworkingStockGeometry::FPlan Core;
    if(Detailed)
    {
        Core=WoodworkingStockGeometry::Plan(Interior.GetData(),Interior.Num(),W,H);
        Detailed=Core.Valid&&int32(Core.Faces.size()+Plan.Faces.size()+Plan.Edges.size())+Boundary.Num()*9<=QuadBudget;
    }
    const double Bevel=Detailed?FMath::Min3(.045,Units*.22,Thickness*.1):0.;
    auto TopRect=[&](const WoodworkingStockGeometry::FRect& R,double Z,FVector3f N)
    {Quad(Mesh,P(R.X0,R.Y0,Z),P(R.X1,R.Y0,Z),P(R.X1,R.Y1,Z),P(R.X0,R.Y1,Z),N,Face,40);};
    for(const auto& R:Plan.Faces)TopRect(R,0,FVector3f(0,0,-1));
    for(const auto& R:(Detailed?Core.Faces:Plan.Faces))TopRect(R,Thickness,FVector3f(0,0,1));
    if(Detailed)
    {
        const double B=Bevel/Units,Steps[]={0.,B,1.-B,1.};
        for(const auto Cell:Boundary)
        {
            FVector3d Points[4][4];
            for(int32 V=0;V<4;++V)for(int32 U=0;U<4;++U)
            {
                const double X=Steps[U],Y=Steps[V];double Distance=B;
                if(!Solid(Cell.X-1,Cell.Y))Distance=FMath::Min(Distance,X);
                if(!Solid(Cell.X+1,Cell.Y))Distance=FMath::Min(Distance,1-X);
                if(!Solid(Cell.X,Cell.Y-1))Distance=FMath::Min(Distance,Y);
                if(!Solid(Cell.X,Cell.Y+1))Distance=FMath::Min(Distance,1-Y);
                // Diagonal vacancies share the same corner height across adjacent cells.
                for(int32 SY:{-1,1})for(int32 SX:{-1,1})if(!Solid(Cell.X+SX,Cell.Y+SY))
                {
                    const double DX=SX<0?X:1-X,DY=SY<0?Y:1-Y;
                    Distance=FMath::Min(Distance,FMath::Sqrt(DX*DX+DY*DY));
                }
                Points[V][U]=P(Cell.X+X,Cell.Y+Y,Thickness-Bevel+Distance*Units);
            }
            for(int32 V=0;V<3;++V)for(int32 U=0;U<3;++U)
            {
                const auto A=Points[V][U],B0=Points[V][U+1],C=Points[V+1][U+1],D=Points[V+1][U];
                FVector3d N=FVector3d::CrossProduct(D-A,B0-A)+FVector3d::CrossProduct(D-B0,C-B0);
                N.Normalize();
                Quad(Mesh,A,B0,C,D,FVector3f(N),Face,40);
            }
        }
    }
    for(const auto& E:Plan.Edges)
    {
        const bool OriginalEdge=(E.X0==0&&E.X1==0)||(E.X0==W&&E.X1==W)||(E.Y0==0&&E.Y1==0)||(E.Y0==H&&E.Y1==H);
        const FVector4f Cut(E.NX!=0?1.f:0.f,OriginalEdge?.18f:1.f,0,1);
        Quad(Mesh,P(E.X0,E.Y0,0),P(E.X1,E.Y1,0),P(E.X1,E.Y1,Thickness-Bevel),P(E.X0,E.Y0,Thickness-Bevel),
            FVector3f(float(E.NX),float(-E.NY),0),Cut,40);
    }
    return true;
}
}
