#include "ChapelNavigationGeometry.h"
#include "AI/NavigationSystemHelpers.h"
#include "AI/NavigationModifier.h"
#include "NavAreas/NavArea_Null.h"
#include "PhysicsEngine/BodySetup.h"
#include "Engine/StaticMesh.h"

void UChapelFoundationNavMesh::OnRegister()
{
    if (!NavigationBody && CanEverAffectNavigation())
    {
        NavigationBody=NewObject<UBodySetup>(this,NAME_None,RF_Transient);
        NavigationBody->CollisionTraceFlag=CTF_UseSimpleAsComplex;
        auto Box=[this](double X0,double X1,double Y0,double Y1,double Z0,double Z1)
        {
            FKBoxElem Part(X1-X0,Y1-Y0,Z1-Z0);
            Part.Center=FVector((X0+X1)*.5,(Y0+Y1)*.5,(Z0+Z1)*.5);
            NavigationBody->AggGeom.BoxElems.Add(Part);
        };
        // OldChapel/author_kit.py: slab, two footing courses, ten buttress feet and the low entry treads.
        Box(-799,799,-399,399,-136,-2);
        for (int32 Tier=0;Tier<2;++Tier)
        {
            const double X=Tier?813.:820.,Y=Tier?416.:423.;
            const double Low=Tier?-17.3:-51.,High=Tier?.25:-16.8;
            Box(-X,X,-Y,-368,Low,High);Box(-X,X,368,Y,Low,High);
            Box(773,X,-Y,Y,Low,High);
            Box(-X,-773,-Y,-88,Low,High);Box(-X,-773,88,Y,Low,High);
        }
        for(double X : {-754.,-400.,0.,400.,754.})
            for(double Side : {-1.,1.})
            {
                Box(X-48,X+48,FMath::Min(420.*Side,504.*Side),FMath::Max(420.*Side,504.*Side),-47,-18);
                Box(X-44,X+44,FMath::Min(414.*Side,498.*Side),FMath::Max(414.*Side,498.*Side),-18.5,-6);
            }
        Box(-837,-732,-89,89,-36,.15);Box(-876,-834,-93,93,-37,-11);Box(-920,-873,-98,98,-40,-23);
        Box(-970,-926,-46,10,-43,-31.6);Box(-1017,-981,-11,33,-43,-32.3);Box(-1050,-1022,-39,-5,-43,-32.8);
    }
    Super::OnRegister();
}

bool UChapelFoundationNavMesh::DoCustomNavigableGeometryExport(FNavigableGeometryExport& Export) const
{
    if (!NavigationBody) return Super::DoCustomNavigableGeometryExport(Export);
    for (int32 I=0;I<GetInstanceCount();++I)
    {
        FTransform World;
        if (GetInstanceTransform(I,World,true)) Export.ExportRigidBodySetup(*NavigationBody,World);
    }
    return false;
}

bool UChapelStatueNavMesh::DoCustomNavigableGeometryExport(FNavigableGeometryExport& Export) const
{
    if (const UStaticMesh* Mesh=GetStaticMesh())
    {
        // The actual pedestal supplies the walkable/blocking stone base. Mark only the
        // statue footprint above it as unavailable, independent of the randomly chosen scan.
        FBox Obstacle=Mesh->GetBoundingBox();Obstacle.Min.Z-=4.;
        FCompositeNavModifier Modifiers;
        Modifiers.Add(FAreaNavModifier(Obstacle,GetComponentTransform(),UNavArea_Null::StaticClass()));
        Export.AddNavModifiers(Modifiers);
    }
    return false;
}
