#include "TemperateHillsWorld.h"
#include "Engine/StaticMesh.h"
#include "Components/InstancedStaticMeshComponent.h"

void ATemperateHillsWorld::GetWhiteCliffPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!Assets||!RiverPlan||!RiverPlan->WhiteCliffs.Valid)return;
    const auto& Region=RiverPlan->WhiteCliffs;
    const double Yaw=FMath::RadiansToDegrees(FMath::Atan2(Region.Axis.Y,Region.Axis.X));
    auto Place=[&](int32 Id,const TSoftObjectPtr<UStaticMesh>& Ref,double X,double Y,FVector Target,double Angle,double Burial)
    {
        auto* Mesh=Ref.Get();if(!Mesh)return;
        const FVector2D P=Region.World(X,Y);
        FBox Box=Mesh->GetBoundingBox();
        Box.Min+=Mesh->GetNegativeBoundsExtension();Box.Max-=Mesh->GetPositiveBoundsExtension();
        const FVector Size=Box.GetSize();
        const FVector Scale(Target.X/FMath::Max(1.,Size.X),Target.Y/FMath::Max(1.,Size.Y),Target.Z/FMath::Max(1.,Size.Z));
        const FQuat Rotation=FRotator(0,Yaw+Angle,0).Quaternion();
        const FVector Center=Rotation.RotateVector(FVector(Box.GetCenter().X*Scale.X,Box.GetCenter().Y*Scale.Y,0));
        if(RiverPlan->Protection(P.X,P.Y)>.001)return;
        for(const double SX:{-.5,.5})for(const double SY:{-.5,.5})
        {
            const FVector D=Rotation.RotateVector(FVector(Target.X*SX,Target.Y*SY,0));
            if(RiverPlan->Protection(P.X+D.X,P.Y+D.Y)>.001||
                FMath::Abs(P.X+D.X)>SizeMeters*50.-100.||FMath::Abs(P.Y+D.Y)>SizeMeters*50.-100.)return;
        }
        double Ground=Height(P.X,P.Y);
        for(const double SX:{-.4,.4})for(const double SY:{-.4,.4})
        {
            const FVector D=Rotation.RotateVector(FVector(Target.X*SX,Target.Y*SY,0));
            Ground=FMath::Min(Ground,Height(P.X+D.X,P.Y+D.Y));
        }
        FTemperatePlacement Item;
        Item.Mesh=Ref.ToSoftObjectPath();Item.Key=TemperateHillsSurface::Key(Id,0,Seed,3593);
        Item.CandidateId=0x5000000000000000ULL|uint64(Id);
        Item.Transform=FTransform(Rotation,FVector(P.X-Center.X,P.Y-Center.Y,Ground-Box.Min.Z*Scale.Z-Burial),Scale);
        if(!Box.TransformBy(Item.Transform).Intersect(Bounds))return;
        Out.Add(Item);
    };
    if(Assets->WhiteCliffMeshes.Num()>=3)
    {
        int32 Id=0;
        // Broken outer limestone fins. A clear central haul ramp remains between
        // the left and right groups; real scanned faces carry the near silhouette.
        for(int32 Row=0;Row<3;++Row)for(int32 Side:{-1,1})
        {
            const double Y=-2000.+Row*3000.;
            Place(Id,Assets->WhiteCliffMeshes[Id%2],Side*(6200.+Row*450.),Y,
                FVector(1750.+Row*180.,1050.,2100.+Row*240.),Side<0?-72.:102.,250.);++Id;
        }
        for(int32 I=0;I<6;++I)
        {
            const double X=(I-2.5)*3000.;
            if(FMath::Abs(X)<2000.)continue;
            Place(20+I,Assets->WhiteCliffMeshes[I%2],X,6100.,FVector(2000.,1300.,2400.),175.+I*3.,300.);
        }
        // Small, irregular quarry spoil piles; never cover the accessible haul ramp.
        for(int32 I=0;I<28;++I)
        {
            const uint32 K=TemperateHillsSurface::Key(I,0,Seed,3599);
            const double X=(I%2?-1.:1.)*(3200.+TemperateHillsSurface::Unit(K)*4200.);
            const double Y=-3600.+TemperateHillsSurface::Unit(K+1)*7800.;
            const double Span=220.+TemperateHillsSurface::Unit(K+2)*370.;
            Place(100+I,Assets->WhiteCliffMeshes[2],X,Y,FVector(Span,Span*.65,Span*.30),
                TemperateHillsSurface::Unit(K+3)*360.,25.);
        }
    }
    if(Assets->QuarryProps.Num()>=2)
    {
        Place(300,Assets->QuarryProps[0],4700.,1450.,FVector(520.,420.,580.),-25.,15.);
        Place(301,Assets->QuarryProps[1],-4600.,-1000.,FVector(1100.,720.,420.),5.,30.);
        if(Assets->QuarryProps.Num()>2)
            Place(302,Assets->QuarryProps[2],4900.,950.,FVector(145.,130.,85.),-25.,3.);
    }
}
bool ATemperateHillsWorld::AssembleWhiteCliffs()
{
    if(!RiverPlan||!RiverPlan->bRiverLake)return false;
    if(!RiverPlan->WhiteCliffs.Valid)return true;
    if(!Assets||Assets->WhiteCliffMeshes.Num()<3||Assets->QuarryProps.Num()<2)return false;
    for(const auto& Ref:Assets->WhiteCliffMeshes)if(!Ref.IsValid())return false;
    for(const auto& Ref:Assets->QuarryProps)if(!Ref.IsValid())return false;
    TArray<FTemperatePlacement> Items;
    GetWhiteCliffPlacements(FBox(FVector(-SizeMeters*50,-SizeMeters*50,-100000),FVector(SizeMeters*50,SizeMeters*50,100000)),Items);
    TMap<FSoftObjectPath,UInstancedStaticMeshComponent*> Groups;
    for(const auto& Item:Items)
    {
        auto*& Component=Groups.FindOrAdd(Item.Mesh);
        if(!Component)
        {
            Component=NewObject<UInstancedStaticMeshComponent>(this);
            AddInstanceComponent(Component);Component->SetupAttachment(RootComponent);
            // Match the session root: UE rejects a static child of WorldBounds.
            Component->SetMobility(RootComponent->Mobility);
            Component->SetStaticMesh(Cast<UStaticMesh>(Item.Mesh.ResolveObject()));
            Component->SetCollisionProfileName(TEXT("BlockAll"));
            Component->SetCanEverAffectNavigation(HasAuthority());
            Component->SetCullDistances(75000,95000);
            Component->ComponentTags.Add(TEXT("HillsWhiteCliffs"));
            Component->RegisterComponent();
        }
        Component->AddInstance(Item.Transform,true);
    }
    UE_LOG(LogTemp,Display,TEXT("HILLS_WHITE_CLIFFS assembled groups=%d instances=%d"),Groups.Num(),Items.Num());
    return true;
}
