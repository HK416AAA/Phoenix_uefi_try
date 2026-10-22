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
  volatile UINT32  *Gicr;
  volatile UINT32  *Gicd;
  UINTN             Index;

  DirectLog ("TAS-GIC-RUN\n");

  /* GICR_IGROUPR0: all PPIs belong to group 1. */
  Gicr = (volatile UINT32 *)(UINTN)0xFE450080;
  *Gicr = 0xFFFFFFFF;

  /* GICD_IGROUPR0..31: all SPIs belong to group 1. */
  Gicd = (volatile UINT32 *)(UINTN)0xFE400080;
  for (Index = 0; Index < 32; Index++) {
    Gicd[Index] = 0xFFFFFFFF;
  }

  __asm__ __volatile__ ("dsb sy" ::: "memory");
  DirectLog ("TAS-GIC-DONE\n");

  __asm__ __volatile__ ("msr daifset, #1" ::: "memory");
  __asm__ __volatile__ ("isb" ::: "memory");
  DirectLog ("TAS-DAIF-DONE\n");

  return EFI_SUCCESS;
}
