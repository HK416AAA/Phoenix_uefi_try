#include <Uefi.h>
#include <Library/BaseLib.h>
#include <Library/DebugLib.h>

EFI_STATUS
EFIAPI
FiqMaskInitialize (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  UINT64  Hppir0;
  UINT64  Hppir1;

  Hppir0 = 0;
  Hppir1 = 0;
  asm volatile ("mrs %0, ICC_HPPIR0_EL1" : "=r" (Hppir0));
  asm volatile ("mrs %0, ICC_HPPIR1_EL1" : "=r" (Hppir1));
  DEBUG ((DEBUG_INFO, "TAS-FIQ: HPPIR0=%lx HPPIR1=%lx\n", Hppir0, Hppir1));

  asm volatile ("msr ICC_IGRPEN0_EL1, xzr" ::: "memory");
  asm volatile ("msr daifset, #1" ::: "memory");
  asm volatile ("isb" ::: "memory");

  DEBUG ((DEBUG_INFO, "TAS-FIQ: masked\n"));
  return EFI_SUCCESS;
}
