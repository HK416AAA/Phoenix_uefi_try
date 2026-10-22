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
  DirectLog ("CHR-FIQ-RUN\n");

  /*
   * Keep SError and FIQ masked while the secure-world watchdog/FIQ
   * routing is not yet characterized on 9010.
   */
  __asm__ __volatile__ ("msr daifset, #0x5" ::: "memory");
  __asm__ __volatile__ ("isb" ::: "memory");

  DirectLog ("CHR-FIQ-MASKED\n");
  return EFI_SUCCESS;
}
