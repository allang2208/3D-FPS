#include "TemperateHillsCompatibility.h"
#include "TemperateHillsBuildSignature.h"
#include "Misc/NetworkVersion.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

namespace TemperateHillsCompatibility
{
const TCHAR* Signature(){return TEXT(FPS_HILLS_CONTENT_SIGNATURE);}
void Register()
{
    int32 Revision=FPS_HILLS_CONTENT_REVISION;
#if !UE_BUILD_SHIPPING
    // Opt-in negative transport case; never changes the player's world/save.
    if(FParse::Param(FCommandLine::Get(),TEXT("HillsCompatibilityMismatch")))Revision^=1;
#endif
    FNetworkVersion::RegisterNetworkCustomVersion(
        FGuid(0x9FF5703C,0x1B76474C,0xAD81CC5D,0x72298E13),Revision,Revision,TEXT("HillsContent"));
    UE_LOG(LogTemp,Display,TEXT("HILLS_CONTENT signature=%s revision=%d"),Signature(),Revision);
}
}
