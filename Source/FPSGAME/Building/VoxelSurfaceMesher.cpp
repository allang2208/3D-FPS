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
    // 2026-10-15 楔形切割：Cuts 与 Slots 平行，非 0 条目按 VoxelCut 对角平面裁掉空侧半格；
    // 同一坡刷的相邻切割格拼成一张连续斜面（推导见 VoxelBuildTypes.h）。
    // bAnyCut=false 时 Value/Normal/Material 走原路径（逐位一致），无楔形的块零开销。
    struct FField
    {
        int32 Halo;
        double Radius;
        TArray<int32> Slots;
        TArray<uint8> Cuts;
        bool bAnyCut=false;
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
        uint8 Cut(int32 X,int32 Y,int32 Z) const
        {
            ++X;++Y;++Z;
            if(X<0||Y<0||Z<0||X>=Halo||Y>=Halo||Z>=Halo)return 0;
            return Cuts[X+Halo*(Y+Halo*Z)];
        }
        /** 该格在采样点 P（块局部 cm）处是否实心：占用 ∧ 切割面正确一侧。 */
        int32 SolidSlot(int32 X,int32 Y,int32 Z,const FVector3d& P) const
        {
            const int32 S=Slot(X,Y,Z);
            if(S==INDEX_NONE)return INDEX_NONE;
            const uint8 C=Cut(X,Y,Z);
            if(!C||VoxelCut::Solid(C,P.X-double(X)*CellSize,P.Y-double(Y)*CellSize,P.Z-double(Z)*CellSize))return S;
            return INDEX_NONE;
        }
        double Value(const FBlend& X,const FBlend& Y,const FBlend& Z) const
        {
            double Result=0;
            for(int32 K=0;K<2;++K)for(int32 J=0;J<2;++J)for(int32 I=0;I<2;++I)
                if(Slot(X.Cell[I],Y.Cell[J],Z.Cell[K])!=INDEX_NONE)
                    Result+=X.Weight[I]*Y.Weight[J]*Z.Weight[K];
            return Result;
        }
        double ValueCut(const FBlend& X,const FBlend& Y,const FBlend& Z,const FVector3d& P) const
        {
            double Result=0;
            for(int32 K=0;K<2;++K)for(int32 J=0;J<2;++J)for(int32 I=0;I<2;++I)
                if(SolidSlot(X.Cell[I],Y.Cell[J],Z.Cell[K],P)!=INDEX_NONE)
                    Result+=X.Weight[I]*Y.Weight[J]*Z.Weight[K];
            return Result;
        }
        double ValueAt(const FVector3d& P) const
        {
            const FBlend X=Blend(P.X),Y=Blend(P.Y),Z=Blend(P.Z);
            return bAnyCut?ValueCut(X,Y,Z,P):Value(X,Y,Z);
        }
        FVector3d Normal(const FVector3d& P) const
        {
            if(bAnyCut)
            {
                // 切割面没有可分离的解析梯度；数值差分给出斜面法线（斜面内部权重≈1，
                // 方向即切割面法向）。eps=1.5cm：小于格径与圆角半径，不会跨到远邻格。
                // 符号约定与下方解析路径一致＝**负梯度**（指向实心外）：差分值沿"更实心"方向
                // 增大，直接返回会让 Emit 的绕向判定翻转、斜面整体背面剔除（2026-10-16
                // 用户截图"屋顶空壳、看不到表面"的根因）。
                constexpr double E=1.5;
                const double Dx=ValueAt(P+FVector3d(E,0,0))-ValueAt(P-FVector3d(E,0,0));
                const double Dy=ValueAt(P+FVector3d(0,E,0))-ValueAt(P+FVector3d(0,-E,0));
                const double Dz=ValueAt(P+FVector3d(0,0,E))-ValueAt(P+FVector3d(0,0,-E));
                return FVector3d(-Dx,-Dy,-Dz).GetSafeNormal();
            }
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
            const int32 Direct=SolidSlot(FMath::FloorToInt(Inside.X/CellSize),FMath::FloorToInt(Inside.Y/CellSize),FMath::FloorToInt(Inside.Z/CellSize),Inside);
            if(Direct!=INDEX_NONE)return Direct;
            const FBlend X=Blend(P.X),Y=Blend(P.Y),Z=Blend(P.Z);
            double Best=-1;int32 Result=0;
            for(int32 K=0;K<2;++K)for(int32 J=0;J<2;++J)for(int32 I=0;I<2;++I)
            {
                const int32 Candidate=bAnyCut?SolidSlot(X.Cell[I],Y.Cell[J],Z.Cell[K],P):Slot(X.Cell[I],Y.Cell[J],Z.Cell[K]);
                const double W=X.Weight[I]*Y.Weight[J]*Z.Weight[K];
                if(Candidate!=INDEX_NONE&&W>Best){Best=W;Result=Candidate;}
            }
            return Result;
        }
    };

    void Build(UE::Geometry::FDynamicMesh3& Mesh,FIntVector Origin,int32 Side,double Radius,
        TFunctionRef<int32(FIntVector)> SampleSlot)
    {
        Build(Mesh,Origin,Side,Radius,SampleSlot,[](FIntVector){return uint8(0);});
    }

    void Build(UE::Geometry::FDynamicMesh3& Mesh,FIntVector Origin,int32 Side,double Radius,
        TFunctionRef<int32(FIntVector)> SampleSlot,TFunctionRef<uint8(FIntVector)> SampleCut)
    {
        using namespace UE::Geometry;
        Mesh.Clear();Mesh.EnableAttributes();Mesh.Attributes()->EnableMaterialID();
        FField Field;Field.Halo=Side+2;Field.Radius=FMath::Clamp(Radius,.25,3.0);
        Field.Slots.SetNumUninitialized(Field.Halo*Field.Halo*Field.Halo);
        Field.Cuts.Init(0,Field.Halo*Field.Halo*Field.Halo);
        int32 Occupied=0;
        FIntVector First(Side),Last(-1);
        for(int32 Z=-1;Z<=Side;++Z)for(int32 Y=-1;Y<=Side;++Y)for(int32 X=-1;X<=Side;++X)
        {
            const FIntVector Cell=Origin+FIntVector(X,Y,Z);
            const int32 Slot=SampleSlot(Cell);
            const uint8 Cut=SampleCut(Cell);
            Field.Slots[X+1+Field.Halo*(Y+1+Field.Halo*(Z+1))]=Slot;
            Field.Cuts[X+1+Field.Halo*(Y+1+Field.Halo*(Z+1))]=Cut;
            Occupied+=Slot!=INDEX_NONE;
            Field.bAnyCut|=Cut!=0;
            if(Slot!=INDEX_NONE)
            {
                First=First.ComponentMin(FIntVector(X,Y,Z));Last=Last.ComponentMax(FIntVector(X,Y,Z));
            }
        }
        if(Occupied==0||Occupied==Field.Slots.Num())return;
        // Sparse free-placement volumes must not evaluate all 512,000 sample
        // cubes of an otherwise empty 16^3 chunk.
        First=(First-FIntVector(1)).ComponentMax(FIntVector(0))*Subdivisions;
        Last=(Last+FIntVector(2)).ComponentMin(FIntVector(Side))*Subdivisions;
        const int32 Steps=Side*Subdivisions,Nodes=Steps+1;
        TArray<double> Coordinates;TArray<FBlend> Blends;
        const double R=Field.Radius,Offsets[]={0,R*.5,R,CellSize-R,CellSize-R*.5};
        for(int32 I=0;I<=Steps;++I)
        {
            const double P=(I/Subdivisions)*CellSize+Offsets[I%Subdivisions];
            Coordinates.Add(P);Blends.Add(Field.Blend(P));
        }
        // 审计 P12：Values 是 Nodes³ 个 float（Side=16、Subdivisions=5 时 81³ = 531 441 ≈ 2.03 MB），
        // 原来每个块重建都重新分配一次。改成线程局部可复用缓冲。
        // 必须用 thread_local：本函数由 VoxelGeometry::Batch 在 EAsyncExecution::ThreadPool 上执行，
        // 多个网格作业可并发，跨线程共享缓冲会数据竞争。
        // 尺寸与写入位置与原来完全一致（用绝对下标 X+Nodes*(Y+Nodes*Z)，未被写入的槽位不会被读到，
        // 因为后面的方块循环只扫 [First,Last) 范围）。
        static thread_local TArray<float> Values;
        // 只在需要变大时才重分配（SetNum 不改变已有元素的值，原始代码在这里本来也不初始化）。
        if(Values.Num()!=Nodes*Nodes*Nodes)Values.SetNum(Nodes*Nodes*Nodes,EAllowShrinking::No);
        for(int32 Z=First.Z;Z<=Last.Z;++Z)for(int32 Y=First.Y;Y<=Last.Y;++Y)for(int32 X=First.X;X<=Last.X;++X)
            Values[X+Nodes*(Y+Nodes*Z)]=float(Field.bAnyCut
                ?Field.ValueCut(Blends[X],Blends[Y],Blends[Z],FVector3d(Coordinates[X],Coordinates[Y],Coordinates[Z]))
                :Field.Value(Blends[X],Blends[Y],Blends[Z]));

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
        for(int32 Z=First.Z;Z<Last.Z;++Z)for(int32 Y=First.Y;Y<Last.Y;++Y)for(int32 X=First.X;X<Last.X;++X)
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

    void AppendCutCells(FDynamicMesh3& Mesh,FIntVector Origin,int32 Side,
        TFunctionRef<int32(FIntVector)> SampleSlot,TFunctionRef<uint8(FIntVector)> SampleCut)
    {
        using namespace UE::Geometry;
        if(!Mesh.HasAttributes())return;
        auto* Normals=Mesh.Attributes()->PrimaryNormals();
        auto* UVs=Mesh.Attributes()->PrimaryUV();
        auto* MaterialIDs=Mesh.Attributes()->GetMaterialID();
        if(!Normals||!UVs||!MaterialIDs)return;
        const FVector3d WorldOrigin=FVector3d(Origin)*CellSize;
        auto EmitTri=[&](FVector3d A,FVector3d B,FVector3d C,const FVector3d& N,int32 Slot,
            FVector3d UAxis,FVector3d VAxis)
        {
            const FVector3d Cross=FVector3d::CrossProduct(B-A,C-A);
            if(Cross.SizeSquared()<1.e-14)return;
            if(FVector3d::DotProduct(Cross,N)>0)Swap(B,C);
            UAxis=UAxis.GetSafeNormal();VAxis=VAxis.GetSafeNormal();
            if(UAxis.IsNearlyZero()||VAxis.IsNearlyZero())return;
            // 2026-10-19：切线基与面法线同手性。旧世界投影在 45° 坡上让 U 恒定、切线退化，
            // 法线贴图会翻绿/发黑；按面的真实切向投影后，坡面 U=横向、V=沿坡弧长。
            // 只翻 U：V 保持"由檐口向脊线"，瓦片行不会上下颠倒。
            if(FVector3d::DotProduct(FVector3d::CrossProduct(UAxis,VAxis),N)<0)UAxis=-UAxis;
            const FVector3d Points[]={A,B,C};
            int32 V[3],NIds[3],UVIds[3];
            for(int32 I=0;I<3;++I)
            {
                V[I]=Mesh.AppendVertex(Points[I]);
                NIds[I]=Normals->AppendElement(FVector3f(N));
                const FVector3d World=Points[I]+WorldOrigin;
                UVIds[I]=UVs->AppendElement(FVector2f(
                    float(FVector3d::DotProduct(World,UAxis)/80.),
                    float(FVector3d::DotProduct(World,VAxis)/80.)));
            }
            const int32 T=Mesh.AppendTriangle(V[0],V[1],V[2]);
            Normals->SetTriangle(T,FIndex3i(NIds[0],NIds[1],NIds[2]));
            UVs->SetTriangle(T,FIndex3i(UVIds[0],UVIds[1],UVIds[2]));
            MaterialIDs->SetValue(T,Slot);
        };
        for(int32 Z=0;Z<Side;++Z)for(int32 Y=0;Y<Side;++Y)for(int32 X=0;X<Side;++X)
        {
            const FIntVector P=Origin+FIntVector(X,Y,Z);
            const uint8 Cut=SampleCut(P);
            if(!Cut)continue;
            const int32 Slot=SampleSlot(P);
            if(Slot==INDEX_NONE)continue;
            const uint8 Pat=VoxelCut::Pattern(Cut),Dir=VoxelCut::Dir(Cut);
            const bool bUIsX=Dir<=2;                 // 坡沿 X（挤出 Y）或沿 Y（挤出 X）
            TArray<FVector2D> Poly;                  // 截面 (u,v=z)，CCW；v=0 为格底
            if(Pat==3){Poly.Add(FVector2D(0,0));Poly.Add(FVector2D(20,0));Poly.Add(FVector2D(10,10));}
            else
            {
                const double Rise=Pat==0?1.:.5,Base=Pat==2?10.:0.;
                double V0,V20;
                if(Dir==1||Dir==3){V0=Base;V20=Base+Rise*20.;}
                else{V0=Base+Rise*20.;V20=Base;}
                Poly.Add(FVector2D(0,0));Poly.Add(FVector2D(20,0));
                if(V20>1e-6)Poly.Add(FVector2D(20,V20));
                if(V0>1e-6)Poly.Add(FVector2D(0,V0));
            }
            if(Poly.Num()<3)continue;
            const FVector3d Min(X*CellSize,Y*CellSize,Z*CellSize);
            auto P3=[&](const FVector2D& Q,double W)
            {
                return bUIsX?Min+FVector3d(Q.X,W,Q.Y):Min+FVector3d(W,Q.X,Q.Y);
            };
            auto N3=[&](const FVector2D& N2){return bUIsX?FVector3d(N2.X,0,N2.Y):FVector3d(0,N2.X,N2.Y);};
            const auto SlotAt=[&](FIntVector Q){return SampleSlot(Q);};
            const FIntVector AxisStep=bUIsX?FIntVector(0,1,0):FIntVector(1,0,0);
            const FVector3d ExtrudeAxis=bUIsX?FVector3d(0,1,0):FVector3d(1,0,0);
            const FVector3d CapU=bUIsX?FVector3d(1,0,0):FVector3d(0,1,0);
            // 挤出轴两端的三角形/多边形封头（1 格宽坡面的山墙面）。
            if(SlotAt(P-AxisStep)==INDEX_NONE)
            {
                const FVector3d N=bUIsX?FVector3d(0,-1,0):FVector3d(-1,0,0);
                for(int32 I=1;I+1<Poly.Num();++I)EmitTri(P3(Poly[0],0),P3(Poly[I],0),P3(Poly[I+1],0),N,Slot,CapU,FVector3d(0,0,1));
            }
            if(SlotAt(P+AxisStep)==INDEX_NONE)
            {
                const FVector3d N=bUIsX?FVector3d(0,1,0):FVector3d(1,0,0);
                for(int32 I=1;I+1<Poly.Num();++I)EmitTri(P3(Poly[0],20),P3(Poly[I],20),P3(Poly[I+1],20),N,Slot,CapU,FVector3d(0,0,1));
            }
            // 截面每条边拉出的面：坡面（法线朝上）、底面（朝下）、竖直面（朝 ±U）。
            // 邻格为空才出面；邻格是整格时由步进场渲染（它把切格当空），邻格是切格时视为
            // 共面/脊线内部——脊线两侧的楔形正好面贴面，不需要额外竖直面。
            for(int32 I=0;I<Poly.Num();++I)
            {
                const FVector2D A=Poly[I],B=Poly[(I+1)%Poly.Num()];
                const FVector2D D=B-A;
                FVector2D Out(D.Y,-D.X);             // CCW 多边形的外法线
                if(Out.IsNearlyZero())continue;
                Out=Out.GetSafeNormal();
                bool bExposed;
                if(Out.Y>0.5)bExposed=SlotAt(P+FIntVector(0,0,1))==INDEX_NONE;
                else if(Out.Y<-0.5)bExposed=SlotAt(P-FIntVector(0,0,1))==INDEX_NONE;
                else
                {
                    const int32 S=Out.X>0?1:-1;
                    const FIntVector Q=bUIsX?P+FIntVector(S,0,0):P+FIntVector(0,S,0);
                    bExposed=SlotAt(Q)==INDEX_NONE;
                }
                if(!bExposed)continue;
                const FVector3d N=N3(Out);
                const FVector3d A3=P3(A,0),B3=P3(B,0);
                const FVector3d EdgeDir=(B3-A3).GetSafeNormal();
                // 坡面/竖面统一按"横向=挤出轴、纵向=沿边向上"展开：坡面 V 是真实弧长，
                // 相邻楔形格共享同一条 U/V 基线，砖瓦不会被拉成一条竖线。
                FVector3d SlopeUp=EdgeDir;if(SlopeUp.Z<0)SlopeUp=-SlopeUp;
                EmitTri(A3,B3,P3(B,20),N,Slot,ExtrudeAxis,SlopeUp);
                EmitTri(A3,P3(B,20),P3(A,20),N,Slot,ExtrudeAxis,SlopeUp);
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

UDynamicMesh* UVoxelSurfaceLibrary::CreateExampleMeshCut(float EdgeRadiusCm,int32 Cut)
{
    UE::Geometry::FDynamicMesh3 Mesh;
    const uint8 Encoded=uint8(FMath::Clamp(Cut,0,255));
    // 3x3 单层：中心格带切割，四周留空；切割格走解析棱柱（与放置后同一真源），
    // 不再经过步进场的粗采样切割。平移口径与旧资产一致。
    const FIntVector Origin(-1,-1,0);
    VoxelSurface::Build(Mesh,Origin,3,EdgeRadiusCm,[](FIntVector){return INDEX_NONE;});
    VoxelSurface::AppendCutCells(Mesh,Origin,3,
        [](FIntVector P){return P==FIntVector::ZeroValue?0:INDEX_NONE;},
        [Encoded](FIntVector P){return P==FIntVector::ZeroValue?Encoded:uint8(0);});
    for(int32 Vertex:Mesh.VertexIndicesItr())Mesh.SetVertex(Vertex,Mesh.GetVertex(Vertex)-FVector3d(10,10,10));
    auto* Result=NewObject<UDynamicMesh>();Result->SetMesh(MoveTemp(Mesh));return Result;
}
