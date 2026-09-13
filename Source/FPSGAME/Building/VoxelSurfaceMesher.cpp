#include "VoxelSurfaceMesher.h"
#include "VoxelBuildWorld.h"
#include "UDynamicMesh.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"

namespace VoxelSurface
{
    constexpr double CellSize=AVoxelBuildWorld::CellSizeCm;
    constexpr int32 Subdivisions=5;
    struct FBlend
    {
        int32 Cell[2];
        double Weight[2],Derivative[2];
    };

    // Compact, smooth occupancy filter. It only changes a narrow band around
    // grid edges; a continuous planar wall stays on its exact original plane.
    struct FField
    {
        int32 Halo;
        double Radius;
        TArray<int32> Slots;
        FBlend Blend(double P) const
        {
            const int32 Boundary=FMath::RoundToInt(P/CellSize);
            const double Distance=P-Boundary*CellSize;
            if(FMath::Abs(Distance)>=Radius)
            {
                const int32 Cell=FMath::FloorToInt(P/CellSize);
                return {{Cell,Cell},{1,0},{0,0}};
            }
            const double T=.5+.5*Distance/Radius;
            const double W=T*T*(3-2*T),D=3*T*(1-T)/Radius;
            return {{Boundary-1,Boundary},{1-W,W},{-D,D}};
        }
        int32 Slot(int32 X,int32 Y,int32 Z) const
        {
            ++X;++Y;++Z;
            if(X<0||Y<0||Z<0||X>=Halo||Y>=Halo||Z>=Halo)return INDEX_NONE;
            return Slots[X+Halo*(Y+Halo*Z)];
        }
        double Value(const FBlend& X,const FBlend& Y,const FBlend& Z) const
        {
            double Result=0;
            for(int32 K=0;K<2;++K)for(int32 J=0;J<2;++J)for(int32 I=0;I<2;++I)
                if(Slot(X.Cell[I],Y.Cell[J],Z.Cell[K])!=INDEX_NONE)
                    Result+=X.Weight[I]*Y.Weight[J]*Z.Weight[K];
            return Result;
        }
        FVector3d Normal(const FVector3d& P) const
        {
            const FBlend X=Blend(P.X),Y=Blend(P.Y),Z=Blend(P.Z);
            FVector3d Gradient=FVector3d::ZeroVector;
            for(int32 K=0;K<2;++K)for(int32 J=0;J<2;++J)for(int32 I=0;I<2;++I)
                if(Slot(X.Cell[I],Y.Cell[J],Z.Cell[K])!=INDEX_NONE)
                {
                    Gradient.X-=X.Derivative[I]*Y.Weight[J]*Z.Weight[K];
                    Gradient.Y-=X.Weight[I]*Y.Derivative[J]*Z.Weight[K];
                    Gradient.Z-=X.Weight[I]*Y.Weight[J]*Z.Derivative[K];
                }
            return Gradient.GetSafeNormal();
        }
        int32 Material(const FVector3d& P,const FVector3d& N) const
        {
            const FVector3d Inside=P-N*(Radius+.01);
            const int32 Direct=Slot(FMath::FloorToInt(Inside.X/CellSize),FMath::FloorToInt(Inside.Y/CellSize),FMath::FloorToInt(Inside.Z/CellSize));
            if(Direct!=INDEX_NONE)return Direct;
            const FBlend X=Blend(P.X),Y=Blend(P.Y),Z=Blend(P.Z);
            double Best=-1;int32 Result=0;
            for(int32 K=0;K<2;++K)for(int32 J=0;J<2;++J)for(int32 I=0;I<2;++I)
            {
                const int32 Candidate=Slot(X.Cell[I],Y.Cell[J],Z.Cell[K]);
                const double W=X.Weight[I]*Y.Weight[J]*Z.Weight[K];
                if(Candidate!=INDEX_NONE&&W>Best){Best=W;Result=Candidate;}
            }
            return Result;
        }
    };

    void Build(UE::Geometry::FDynamicMesh3& Mesh,FIntVector Origin,int32 Side,double Radius,
        TFunctionRef<int32(FIntVector)> SampleSlot)
    {
        using namespace UE::Geometry;
        Mesh.Clear();Mesh.EnableAttributes();Mesh.Attributes()->EnableMaterialID();
        FField Field;Field.Halo=Side+2;Field.Radius=FMath::Clamp(Radius,.25,3.0);
        Field.Slots.SetNumUninitialized(Field.Halo*Field.Halo*Field.Halo);
        int32 Occupied=0;
        for(int32 Z=-1;Z<=Side;++Z)for(int32 Y=-1;Y<=Side;++Y)for(int32 X=-1;X<=Side;++X)
        {
            const int32 Slot=SampleSlot(Origin+FIntVector(X,Y,Z));
            Field.Slots[X+1+Field.Halo*(Y+1+Field.Halo*(Z+1))]=Slot;
            Occupied+=Slot!=INDEX_NONE;
        }
        if(Occupied==0||Occupied==Field.Slots.Num())return;
        const int32 Steps=Side*Subdivisions,Nodes=Steps+1;
        TArray<double> Coordinates;TArray<FBlend> Blends;
        const double R=Field.Radius,Offsets[]={0,R*.5,R,CellSize-R,CellSize-R*.5};
        for(int32 I=0;I<=Steps;++I)
        {
            const double P=(I/Subdivisions)*CellSize+Offsets[I%Subdivisions];
            Coordinates.Add(P);Blends.Add(Field.Blend(P));
        }
        TArray<float> Values;Values.SetNumUninitialized(Nodes*Nodes*Nodes);
        for(int32 Z=0;Z<Nodes;++Z)for(int32 Y=0;Y<Nodes;++Y)for(int32 X=0;X<Nodes;++X)
            Values[X+Nodes*(Y+Nodes*Z)]=float(Field.Value(Blends[X],Blends[Y],Blends[Z]));

        auto* Normals=Mesh.Attributes()->PrimaryNormals();auto* UVs=Mesh.Attributes()->PrimaryUV();
        const FVector3d WorldOrigin=FVector3d(Origin)*CellSize;
        auto Emit=[&](FVector3d A,FVector3d B,FVector3d C,FVector3d NA,FVector3d NB,FVector3d NC,int32 Slot)
        {
            const FVector3d Cross=FVector3d::CrossProduct(B-A,C-A);
            if(Cross.SizeSquared()<1.e-14)return;
            if(FVector3d::DotProduct(Cross,NA+NB+NC)>0){Swap(B,C);Swap(NB,NC);}
            const FVector3d Points[]={A,B,C},Directions[]={NA,NB,NC};
            int32 Vertices[3],NIds[3],UVIds[3];
            for(int32 I=0;I<3;++I)
            {
                Vertices[I]=Mesh.AppendVertex(Points[I]);NIds[I]=Normals->AppendElement(FVector3f(Directions[I]));
                const FVector3d P=Points[I]+WorldOrigin,N=Directions[I].GetAbs();
                const int32 Axis=N.Z>=N.X&&N.Z>=N.Y?2:(N.X>=N.Y?0:1);
                UVIds[I]=UVs->AppendElement(FVector2f(P[Axis==0?1:0]/80,P[Axis==2?1:2]/80));
            }
            const int32 T=Mesh.AppendTriangle(Vertices[0],Vertices[1],Vertices[2]);
            Normals->SetTriangle(T,FIndex3i(NIds[0],NIds[1],NIds[2]));
            UVs->SetTriangle(T,FIndex3i(UVIds[0],UVIds[1],UVIds[2]));
            Mesh.Attributes()->GetMaterialID()->SetValue(T,Slot);
        };
        auto CurvedTriangle=[&](const FVector3d& A,const FVector3d& B,const FVector3d& C)
        {
            const FVector3d Center=(A+B+C)/3,Normal=Field.Normal(Center);
            Emit(A,B,C,Field.Normal(A),Field.Normal(B),Field.Normal(C),Field.Material(Center,Normal));
        };
        // Most of a wall is planar. Keep those areas greedily merged instead
        // of retaining the fine edge tessellation across the whole building.
        TMap<FIntVector,TArray<int32>> FlatMasks;
        constexpr int32 Tets[6][4]={{0,1,3,7},{0,3,2,7},{0,2,6,7},{0,6,4,7},{0,4,5,7},{0,5,1,7}};
        for(int32 Z=0;Z<Steps;++Z)for(int32 Y=0;Y<Steps;++Y)for(int32 X=0;X<Steps;++X)
        {
            float F[8];int32 InsideCount=0;
            for(int32 I=0;I<8;++I)
            {F[I]=Values[X+(I&1)+Nodes*(Y+((I>>1)&1)+Nodes*(Z+((I>>2)&1)))];InsideCount+=F[I]>.5f;}
            if(InsideCount==0||InsideCount==8)continue;
            const FIntVector Grid(X,Y,Z);
            bool Flat=false;
            for(int32 Axis=0;Axis<3&&!Flat;++Axis)
            {
                const int32 Bit=1<<Axis;bool Equal=true;
                for(int32 I=0;I<8;++I)if(F[I]!=F[I&Bit]){Equal=false;break;}
                if(!Equal||(F[0]!=.5f&&F[Bit]!=.5f))continue;
                const int32 Sign=F[0]>F[Bit]?1:-1,Plane=Grid[Axis]+(F[Bit]==.5f?1:0);
                const int32 U=Axis==0?1:0,V=Axis==2?1:2;
                FVector3d Center((Coordinates[X]+Coordinates[X+1])*.5,(Coordinates[Y]+Coordinates[Y+1])*.5,(Coordinates[Z]+Coordinates[Z+1])*.5);
                Center[Axis]=Coordinates[Plane];FVector3d N=FVector3d::ZeroVector;N[Axis]=Sign;
                auto& Mask=FlatMasks.FindOrAdd(FIntVector(Axis,Plane,Sign));if(Mask.IsEmpty())Mask.Init(0,Steps*Steps);
                Mask[Grid[U]+Steps*Grid[V]]=Field.Material(Center,N)+1;Flat=true;
            }
            if(Flat)continue;
            FVector3d Points[8];
            for(int32 I=0;I<8;++I)Points[I]=FVector3d(Coordinates[X+(I&1)],Coordinates[Y+((I>>1)&1)],Coordinates[Z+((I>>2)&1)]);
            auto Cut=[&](int32 A,int32 B){return FMath::Lerp(Points[A],Points[B],double((.5f-F[A])/(F[B]-F[A])));};
            for(const auto& Tet:Tets)
            {
                int32 In[4],Out[4],NI=0,NO=0;
                for(int32 I:Tet){if(F[I]>.5f)In[NI++]=I;else Out[NO++]=I;}
                if(NI==1)CurvedTriangle(Cut(In[0],Out[0]),Cut(In[0],Out[1]),Cut(In[0],Out[2]));
                else if(NI==3)CurvedTriangle(Cut(Out[0],In[0]),Cut(Out[0],In[1]),Cut(Out[0],In[2]));
                else if(NI==2)
                {
                    const FVector3d A=Cut(In[0],Out[0]),B=Cut(In[0],Out[1]),C=Cut(In[1],Out[1]),D=Cut(In[1],Out[0]);
                    CurvedTriangle(A,B,C);CurvedTriangle(A,C,D);
                }
            }
        }
        for(auto& Entry:FlatMasks)
        {
            const int32 Axis=Entry.Key.X,U=Axis==0?1:0,V=Axis==2?1:2;
            FVector3d N=FVector3d::ZeroVector;N[Axis]=Entry.Key.Z;
            auto& Mask=Entry.Value;
            for(int32 Y=0;Y<Steps;++Y)for(int32 X=0;X<Steps;)
            {
                const int32 Slot=Mask[X+Steps*Y];if(Slot==0){++X;continue;}
                int32 Width=1,Height=1;while(X+Width<Steps&&Mask[X+Width+Steps*Y]==Slot)++Width;
                bool Extend=true;
                while(Y+Height<Steps&&Extend)
                {
                    for(int32 I=0;I<Width;++I)if(Mask[X+I+Steps*(Y+Height)]!=Slot){Extend=false;break;}
                    if(Extend)++Height;
                }
                FVector3d A=FVector3d::ZeroVector;A[Axis]=Coordinates[Entry.Key.Y];A[U]=Coordinates[X];A[V]=Coordinates[Y];
                FVector3d B=A,C=A,D=A;B[U]=Coordinates[X+Width];C[U]=B[U];C[V]=Coordinates[Y+Height];D[V]=C[V];
                Emit(A,B,C,N,N,N,Slot-1);Emit(A,C,D,N,N,N,Slot-1);
                for(int32 J=0;J<Height;++J)for(int32 I=0;I<Width;++I)Mask[X+I+Steps*(Y+J)]=0;
                X+=Width;
            }
        }
    }
}

UDynamicMesh* UVoxelSurfaceLibrary::CreateExampleMesh(float EdgeRadiusCm)
{
    UE::Geometry::FDynamicMesh3 Mesh;
    VoxelSurface::Build(Mesh,FIntVector::ZeroValue,1,EdgeRadiusCm,[](FIntVector P){return P==FIntVector::ZeroValue?0:INDEX_NONE;});
    for(int32 Vertex:Mesh.VertexIndicesItr())Mesh.SetVertex(Vertex,Mesh.GetVertex(Vertex)-FVector3d(10,10,10));
    auto* Result=NewObject<UDynamicMesh>();Result->SetMesh(MoveTemp(Mesh));return Result;
}
