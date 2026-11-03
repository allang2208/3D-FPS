#pragma once
#include "CoreMinimal.h"

// Authored from the current five hammer-head meshes, at GroundPitch=135.
// Mesh-local centimetres; apply the installed module transform and CenterZ.
// Regenerate with SourceAssets/ThunderGodHammer20261028/GroundEmbed20261101/author_contacts.py
namespace ThunderHammerThrow {
inline FVector GroundHeadContact(const FString& MeshPath)
{
    if(MeshPath.EndsWith(TEXT(".SM_ThunderGodHammer_hammer_heads_heavy_forged")))return FVector(-20.594520867,-0.032995637,6.476837397);
    if(MeshPath.EndsWith(TEXT(".SM_ThunderGodHammer_hammer_heads_flanged_breaker")))return FVector(-19.544520974,0.133467185,6.026430242);
    if(MeshPath.EndsWith(TEXT(".SM_ThunderGodHammer_hammer_heads_light_drum")))return FVector(-18.244521320,-0.081514321,4.154428569);
    if(MeshPath.EndsWith(TEXT(".SM_ThunderGodHammer_hammer_heads_pointed_hammer")))return FVector(-23.845249911,0.090018305,0.476966686);
    return FVector(-15.942867845,0.068590360,4.723412395);
}
}
