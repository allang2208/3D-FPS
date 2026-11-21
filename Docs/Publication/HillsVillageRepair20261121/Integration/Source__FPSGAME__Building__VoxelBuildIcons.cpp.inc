// Source/FPSGAME/Building/VoxelBuildIcons.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 2-4 | file scope
#include "VillageBuildDefense.h"
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../WorldGeneration/HighVillageDefense.h"

// Lines 207-239 | bool UVoxelBuildIcons::Prepare(const FVoxelBuildIconRequest& Request)
    if(Request.PieceId==VillageBuildDefense::WoodGate||Request.PieceId==VillageBuildDefense::StoneGate)
    {
        auto AddPart=[this,&Used](UStaticMesh* Part,const FTransform& Pose)
        {
            auto* Component=TakePoolComponent();
            Component->SetStaticMesh(Part);
            Component->SetWorldTransform(Pose);
            Component->SetVisibility(true);Component->UpdateComponentToWorld();Used.Add(Component);
        };
        if(Request.PieceId==VillageBuildDefense::StoneGate)
        {
            auto* Grille=Cast<UStaticMesh>(AHighVillageGate::PlacedGrilleMeshPath().TryLoad());
            if(!Mesh||!Grille)return false;
            AddPart(Mesh,FTransform::Identity);
            AddPart(Grille,FTransform::Identity);
        }
        else
        {
            constexpr double HingeOffset=AVillageDefenseGate::NarrowHingeOffset;
            for(const TCHAR* Role:{TEXT("GateNarrow"),TEXT("GateNarrowRight"),TEXT("GateHingeMount"),TEXT("GateHingeMountRight")})
            {
                const FString Path=FString::Printf(TEXT("/Game/WorldGeneration/TemperateHills/VillageDefenses/SM_%s.SM_%s"),Role,Role);
                UStaticMesh* Part=LoadObject<UStaticMesh>(nullptr,*Path);
                if(!Part)return false;
                const double HingeX=FCString::Strstr(Role,TEXT("Right"))?HingeOffset:-HingeOffset;
                AddPart(Part,FTransform(FVector(HingeX,0.,0.)));
            }
            auto* PostMesh=Cast<UStaticMesh>(AVillageDefenseGate::PlacedPostMeshPath().TryLoad());
            if(!PostMesh)return false;
            for(bool bRight:{false,true})AddPart(PostMesh,AVillageDefenseGate::PlacedPostTransform(bRight));
        }
    }
    else if(Request.Cells.IsEmpty()&&!Request.ActorClass.IsNull()&&!VillageBuildDefense::IsVillageRecipe(Request.PieceId))

// Lines 273-276 | bool UVoxelBuildIcons::Prepare(const FVoxelBuildIconRequest& Request)
        const FVector Scale=Request.PieceId==VillageBuildDefense::StoneWall
            ?VillageBuildDefense::Placement(Request.PieceId,FIntVector::ZeroValue,FIntVector::ZeroValue,0).GetScale3D()
            :FVector::OneVector;
        Component->SetWorldScale3D(Scale);
