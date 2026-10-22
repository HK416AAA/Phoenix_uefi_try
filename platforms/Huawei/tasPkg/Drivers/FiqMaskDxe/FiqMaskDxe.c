#include <Uefi.h>
#include <Library/BaseLib.h>
#include <Library/DebugLib.h>
#include <Library/SerialPortLib.h>

STATIC
VOID
DirectLog (
  IN CONST CHAR8  *Text
  )
{
  SerialPortWrite ((UINT8 *)Text, AsciiStrLen (Text));
}

EFI_STATUS
EFIAPI
FiqMaskInitialize (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  UINT64           Hppir0;
  UINT64           Hppir1;
  UINT64           Daif;
  UINT64           Igrp0;
  UINT64           Igrp1;
  volatile UINT32  *GicrGroup;

  DirectLog ("TAS-FIQ-RUN\n");

  GicrGroup = (volatile UINT32 *)(UINTN)0xFE450080;
  *GicrGroup = 0xFFFFFFFF;

  __asm__ __volatile__ ("mrs %0, ICC_HPPIR0_EL1" : "=r" (Hppir0));
  __asm__ __volatile__ ("mrs %0, ICC_HPPIR1_EL1" : "=r" (Hppir1));
  __asm__ __volatile__ ("mrs %0, DAIF" : "=r" (Daif));
  __asm__ __volatile__ ("mrs %0, ICC_IGRPEN0_EL1" : "=r" (Igrp0));
  __asm__ __volatile__ ("mrs %0, ICC_IGRPEN1_EL1" : "=r" (Igrp1));

  DEBUG ((
    DEBUG_ERROR,
    "TAS-FIQ: HPPIR0=%lx HPPIR1=%lx DAIF=%lx IGRP0=%lx IGRP1=%lx\n",
    Hppir0, Hppir1, Daif, Igrp0, Igrp1
    ));

  __asm__ __volatile__ ("msr ICC_IGRPEN0_EL1, xzr" ::: "memory");
  __asm__ __volatile__ ("msr daifset, #1" ::: "memory");
  __asm__ __volatile__ ("isb" ::: "memory");

  __asm__ __volatile__ ("mrs %0, DAIF" : "=r" (Daif));
  __asm__ __volatile__ ("mrs %0, ICC_IGRPEN0_EL1" : "=r" (Igrp0));
  DEBUG ((DEBUG_ERROR, "TAS-FIQ: after DAIF=%lx IGRP0=%lx\n", Daif, Igrp0));

  DirectLog ("TAS-FIQ-MASKED\n");
  return EFI_SUCCESS;
}
