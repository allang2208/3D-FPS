#include "BlizzardEnvironment.h"
#include "../Combat/RangedAttackQuery.h"
#include "MagicOcclusion.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace BlizzardEnvironment
{
float VerticalReach(float RadiusY){return RadiusY*2.3f+150.f;}

void SightOrigins(APawn* Caster,const FVector& Center,TArray<FVector,TInlineAllocator<3>>& Origins)
{
    Origins.Reset();FHitResult Roof;
    float Height=150.f;
    if(Trace(Caster,Center+FVector(0,0,4),Center+FVector(0,0,156),Roof))
        Height=FMath::Max(0.f,float(Roof.ImpactPoint.Z-Center.Z)-6.f);
    for(float H:{35.f,90.f,150.f})
        if(Height>=8.f)Origins.AddUnique(Center+FVector(0,0,FMath::Min(H,Height)));
}

bool VolumeExposure(APawn* Caster,const AActor* Target,const FVector& Center,const FVector& Axis,
    float RadiusX,float RadiusY,const TArray<FVector,TInlineAllocator<3>>& Origins)
{
    MagicOcclusion::FBodySamples Samples;MagicOcclusion::BodySamples(Target,Center,Samples);
    if(const auto* Body=Cast<UPrimitiveComponent>(Target->GetRootComponent()))
    {
        FVector Closest;
        if(Body->GetClosestPointOnCollision(Center,Closest)>=0)Samples.Add(Closest);
    }
    const FVector Side=FVector::CrossProduct(FVector::UpVector,Axis);
    const float Height=VerticalReach(RadiusY);
    for(const FVector& Sample:Samples)
    {
        const FVector Offset=Sample-Center;
        const float X=FVector::DotProduct(Offset,Axis)/RadiusX,Y=FVector::DotProduct(Offset,Side)/RadiusY;
        if(X*X+Y*Y>1.f||FMath::Abs(Offset.Z)>Height)continue;
        for(const FVector& Start:Origins)
        {
            FHitResult Block;
            // Trace skips living bodies/open rails, but not walls or floor slabs.
            if(!Trace(Caster,Start,Sample,Block,true))return true;
        }
    }
    return false;
}

void BuildVolumeCells(APawn* Caster,const FVector& Center,const FVector& Axis,float RadiusX,float RadiusY,TArray<FVector>& Cells)
{
    Cells.Init(FVector::ZeroVector,VolumeCellCount);
    TArray<FVector,TInlineAllocator<3>> Origins;SightOrigins(Caster,Center,Origins);
    const float Height=VerticalReach(RadiusY),Bottom=Center.Z-Height,CloudLimit=Center.Z+Height*2.f;
    const FVector Side=FVector::CrossProduct(FVector::UpVector,Axis);
    for(int32 I=0;I<CellCount;++I)
    {
        const FVector XY=Center+CellOffset(I,RadiusX,RadiusY,Axis);
        TArray<FVector,TInlineAllocator<4>> Floors;
        float ProbeZ=Center.Z+Height+4.f;
        // Bounded descending probes retain separate surfaces of the same mesh;
        // ignoring that mesh after one hit would discard all its other floors.
        for(int32 Probe=0;Probe<12&&ProbeZ>Bottom&&Floors.Num()<4;++Probe)
        {
            FHitResult FloorHit;
            if(!Trace(Caster,FVector(XY.X,XY.Y,ProbeZ),FVector(XY.X,XY.Y,Bottom),FloorHit,true))break;
            if(FloorHit.bStartPenetrating){ProbeZ-=32.f;continue;}
            ProbeZ=FMath::Min(ProbeZ-4.f,float(FloorHit.ImpactPoint.Z)-4.f);
            if(FloorHit.ImpactNormal.Z<.45f)continue;
            const FVector Ground=FloorHit.ImpactPoint;
            bool Duplicate=false;for(const FVector& F:Floors)Duplicate|=FMath::Abs(F.X-(Ground.Z-Center.Z))<24.f;
            if(Duplicate)continue;
            FHitResult Roof;
            float Headroom=CloudLimit-Ground.Z;
            if(Trace(Caster,Ground+FVector(0,0,4),FVector(Ground.X,Ground.Y,CloudLimit),Roof,true))
                Headroom=Roof.bStartPenetrating?0.f:FMath::Max(0.f,float(Roof.ImpactPoint.Z-Ground.Z)-8.f);
            if(Headroom<12.f)continue;
            bool Visible=false;
            const FVector Inside=Ground+FVector(0,0,FMath::Min(150.f,Headroom*.5f));
            for(const FVector& Start:Origins)
            {FHitResult Block;if(!Trace(Caster,Start,Inside,Block,true)){Visible=true;break;}}
            if(!Visible)continue;
            float Width=1.f;
            const FVector Mid=Ground+FVector(0,0,FMath::Min(90.f,Headroom*.5f));
            for(const FVector Edge:{Axis*(RadiusX*.2f),-Axis*(RadiusX*.2f),Side*(RadiusY*.2f),-Side*(RadiusY*.2f)})
            {FHitResult Wall;if(Trace(Caster,Mid,Mid+Edge,Wall,true))Width=FMath::Min(Width,FMath::Max(0.f,float(Wall.Distance-4.f)/float(Edge.Size())));}
            if(Width>0.f)Floors.Add(FVector(Ground.Z-Center.Z,Headroom,Width));
        }
        // Keep the main surface first; extra visible decks reuse the same FX
        // assets with independent room parameters, never an extra damage tick.
        Floors.Sort([](const FVector& A,const FVector& B){return FMath::Abs(A.X)<FMath::Abs(B.X);});
        for(int32 Layer=0;Layer<FMath::Min(MaxLayers,Floors.Num());++Layer)Cells[Layer*CellCount+I]=Floors[Layer];
    }
}

FName CellParameter(int32 Index,bool bNiagara)
{
    static const TArray<FName> Names=[](){TArray<FName> Result;for(int32 I=0;I<50;++I)
        Result.Emplace(*FString::Printf(TEXT("%sRoomCell%d"),I<25?TEXT(""):TEXT("User."),I%25));return Result;}();
    return Names[Index+(bNiagara?25:0)];
}
FVector CellOffset(int32 Index,float RadiusX,float RadiusY,const FVector& Axis)
{return Axis*((Index%5-2)*.4f*RadiusX)+FVector::CrossProduct(FVector::UpVector,Axis)*((Index/5-2)*.4f*RadiusY);}
int32 CellAt(const FVector& Offset,float RadiusX,float RadiusY,const FVector& Axis)
{
    const float X=FVector::DotProduct(Offset,Axis)/RadiusX,Y=FVector::DotProduct(Offset,FVector::CrossProduct(FVector::UpVector,Axis))/RadiusY;
    if(FMath::Abs(X)>1||FMath::Abs(Y)>1)return INDEX_NONE;
    return FMath::Clamp(FMath::FloorToInt((Y+1)*2.5f),0,4)*5+FMath::Clamp(FMath::FloorToInt((X+1)*2.5f),0,4);
}
void BuildCells(APawn* Caster,const FVector& Center,const FVector& Axis,float RadiusX,float RadiusY,TArray<FVector>& Cells)
{
    Cells.Init(FVector::ZeroVector,CellCount);
    const float Top=RadiusY*2.3f+150;
    // Visit outward from the legal landing point. A floor probe starts within
    // known headroom, never above the ceiling of the previous cell.
    for(int32 Ring=0;Ring<=4;++Ring)for(int32 I=0;I<CellCount;++I)
    {
        if(FMath::Abs(I%5-2)+FMath::Abs(I/5-2)!=Ring)continue;
        const FVector Offset=CellOffset(I,RadiusX,RadiusY,Axis);
        FVector Ground=Center;float Ceiling=Top;
        if(I!=12)
        {
            int32 Nearest=INDEX_NONE;float Best=MAX_flt;
            for(int32 J=0;J<CellCount;++J)if(Cells[J].Z>0)
            {const float D=FVector::DistSquared(Offset,CellOffset(J,RadiusX,RadiusY,Axis));if(D<Best){Best=D;Nearest=J;}}
            if(Nearest==INDEX_NONE)continue;
            FHitResult FloorHit;
            const FVector Seed=Center+Offset+FVector(0,0,Cells[Nearest].X);
            const float Rise=FMath::Min(180.f,FMath::Max(4.f,float(Cells[Nearest].Y)-8.f));
            if(!Floor(Caster,Seed,Rise,200.f,FloorHit))continue;
            Ground=FloorHit.ImpactPoint;
            if(!GroundRoute(Caster,Center,Ground))continue;
        }
        FHitResult Roof;
        if(Trace(Caster,Ground+FVector(0,0,4),Ground+FVector(0,0,Top+8),Roof))
            Ceiling=Roof.bStartPenetrating?0.f:FMath::Max(0.f,float(Roof.ImpactPoint.Z-Ground.Z)-8.f);
        if(Ceiling<12)continue;
        float Width=1.f;
        const FVector Mid=Ground+FVector(0,0,FMath::Min(90.f,Ceiling*.5f));
        const FVector Side=FVector::CrossProduct(FVector::UpVector,Axis);
        for(const FVector Edge:{Axis*(RadiusX*.2f),-Axis*(RadiusX*.2f),Side*(RadiusY*.2f),-Side*(RadiusY*.2f)})
        {FHitResult Wall;if(Trace(Caster,Mid,Mid+Edge,Wall,true))Width=FMath::Min(Width,FMath::Max(0.f,float(Wall.Distance-4.f)/float(Edge.Size())));}
        Cells[I]=FVector(Ground.Z-Center.Z,Ceiling,Width);
    }
}
void MaterialCells(UMaterialInstanceDynamic* Material,const FVector& Center,const FVector& Axis,float RadiusX,float RadiusY,const TArray<FVector>& Cells)
{
    if(!Material||Cells.Num()!=CellCount)return;
    Material->SetVectorParameterValue(TEXT("RoomCenter"),FLinearColor(Center));
    Material->SetVectorParameterValue(TEXT("RoomSide"),FLinearColor(Axis));
    Material->SetVectorParameterValue(TEXT("RoomForward"),FLinearColor(FVector::CrossProduct(FVector::UpVector,Axis)));
    Material->SetScalarParameterValue(TEXT("RadiusX"),RadiusX);Material->SetScalarParameterValue(TEXT("RadiusY"),RadiusY);
    for(int32 I=0;I<CellCount;++I)Material->SetVectorParameterValue(CellParameter(I),FLinearColor(Cells[I]));
}
bool Trace(APawn* Caster,const FVector& Start,const FVector& End,FHitResult& Hit,bool bAreaSight)
{
    if(!Caster||!Caster->GetWorld())return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(BlizzardEnvironment),true,Caster);
    while(bAreaSight?MagicOcclusion::TraceBlocker(Caster->GetWorld(),Start,End,Query,Hit,Caster):
        RangedAttackQuery::LineTraceSingle(Caster->GetWorld(),Caster,Hit,Start,End,ECC_Visibility,Query))
    {
        auto* Actor=Hit.GetActor();auto* Component=Hit.GetComponent();
        if(Actor&&(Actor->IsA<APawn>()||Actor->IsAttachedTo(Caster)||Actor->FindComponentByClass<UMonsterCombatComponent>()))
        {Query.AddIgnoredActor(Actor);continue;}
        // Opt-in for non-blocking decoration only; hidden meshes and dynamic
        // actors can still be real walls/doors and are never ignored wholesale.
        if(Component&&Component->ComponentHasTag(TEXT("BlizzardNonBlocking")))
        {Query.AddIgnoredComponent(Component);continue;}
        return true;
    }
    return false;
}
bool Floor(APawn* Caster,const FVector& Near,float Rise,float Drop,FHitResult& Hit)
{
    return Trace(Caster,Near+FVector(0,0,Rise),Near-FVector(0,0,Drop),Hit)&&
        !Hit.bStartPenetrating&&Hit.ImpactNormal.Z>=.45f;
}
bool GroundRoute(APawn* Caster,const FVector& From,const FVector& To)
{
    for(float Height:{35.f,90.f,150.f})
    {
        FVector A=From+FVector(0,0,Height),B=To+FVector(0,0,Height);FHitResult Block;
        // Cap each vertical leg below its first overhead obstruction. Even a
        // very low cell keeps a route, without raising a ray through a floor.
        if(Trace(Caster,From+FVector(0,0,4),A,Block))
        {if(Block.bStartPenetrating||Block.ImpactPoint.Z<From.Z+10)continue;A.Z=Block.ImpactPoint.Z-6;}
        if(Trace(Caster,To+FVector(0,0,4),B,Block))
        {if(Block.bStartPenetrating||Block.ImpactPoint.Z<To.Z+10)continue;B.Z=Block.ImpactPoint.Z-6;}
        if(!Trace(Caster,A,B,Block,true))return true;
    }
    return false;
}
bool Validate(APawn* Caster,float Range,FVector& Point,FVector& Normal,FVector& Axis,FString& Failure)
{
    if(!Caster||Point.ContainsNaN()||Normal.ContainsNaN()||Axis.ContainsNaN())
    {Failure=TEXT("落点无效");return false;}
    if(FVector::Dist2D(Caster->GetActorLocation(),Point)>Range)
    {Failure=TEXT("超出施法距离");return false;}
    FHitResult Ground;
    if(!Floor(Caster,Point,24.f,24.f,Ground)||FVector::DistSquared(Ground.ImpactPoint,Point)>FMath::Square(20.f))
    {Failure=TEXT("未找到可施法地面");return false;}
    const FVector Eye=Caster->GetPawnViewLocation();bool Visible=false;
    for(float Height:{12.f,60.f,120.f})
    {
        const FVector End=Ground.ImpactPoint+FVector(0,0,Height);FHitResult Block;
        if(!Trace(Caster,Ground.ImpactPoint+FVector(0,0,4),End,Block)&&!Trace(Caster,Eye,End,Block,true))
        {Visible=true;break;}
    }
    if(!Visible){Failure=TEXT("落点被墙体或楼板挡住");return false;}
    Point=Ground.ImpactPoint;Normal=Ground.ImpactNormal.GetSafeNormal();
    Axis=FVector::VectorPlaneProject(Axis,FVector::UpVector).GetSafeNormal();
    if(Axis.IsNearlyZero())Axis=FVector::RightVector;
    return true;
}
bool Select(APawn* Caster,float Range,const FVector& View,const FVector& Direction,FVector& Point,FVector& Normal,FVector& Axis,FString& Failure)
{
    const FVector Ray=Direction.GetSafeNormal();FHitResult Aim;
    const bool Hit=Trace(Caster,View,View+Ray*(Range+250.f),Aim,true);
    if(Hit&&!Aim.bStartPenetrating&&Aim.ImpactNormal.Z>=.45f)
    {Point=Aim.ImpactPoint;Normal=Aim.ImpactNormal;return Validate(Caster,Range,Point,Normal,Axis,Failure);}
    // Project down from the near side of the obstruction, inside this room.
    // No upward search from outside a roof and no snapping through a wall.
    const float Distance=Hit?float(Aim.Distance):Range;
    for(float Back:{32.f,72.f,128.f})
    {
        const FVector Seed=View+Ray*FMath::Max(0.f,Distance-Back);FHitResult Ground;
        if(!Floor(Caster,Seed,0.f,FMath::Min(Range,1200.f),Ground))continue;
        Point=Ground.ImpactPoint;Normal=Ground.ImpactNormal;
        if(Validate(Caster,Range,Point,Normal,Axis,Failure))return true;
    }
    if(Failure.IsEmpty())Failure=TEXT("未找到室内可见地面");
    return false;
}
}
