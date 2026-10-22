#include <Uefi.h>
#include <Library/BaseLib.h>
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
  DirectLog ("TAS-FIQ-RUN\n");

  __asm__ __volatile__ ("msr daifset, #0x5" ::: "memory");
  __asm__ __volatile__ ("isb" ::: "memory");

  DirectLog ("TAS-FIQ-MASKED\n");
  return EFI_SUCCESS;
}
