#pragma once
#include "CoreMinimal.h"

// Network content identity is separate from the saved world's generation version.
namespace TemperateHillsCompatibility
{
void Register();
const TCHAR* Signature();
}
