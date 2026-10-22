#include <Uefi.h>
#include <Library/BaseLib.h>
#include <Library/SerialPortLib.h>
#include <Library/UefiBootServicesTableLib.h>

#define WDT_BASE     0xFA87C000UL
#define WDT_LOCKEN   0x000
#define WDT_LOCKDIS  0x004
#define WDT_KICK     0x018
#define WDT_KEY      0x1AAEE533U

STATIC EFI_EVENT  mWdtEvent;

STATIC
VOID
DirectLog (
  IN CONST CHAR8  *Text
  )
{
  SerialPortWrite ((UINT8 *)Text, AsciiStrLen (Text));
}

STATIC
VOID
TasWdtKick (
  VOID
  )
{
  volatile UINT32  *Base;

  Base = (volatile UINT32 *)(UINTN)WDT_BASE;
  Base[WDT_LOCKEN / 4]  = WDT_KEY;
  Base[WDT_KICK / 4]    = 1;
  Base[WDT_LOCKDIS / 4] = 1;
  (void)Base[WDT_LOCKEN / 4];
  (void)Base[WDT_LOCKDIS / 4];
}

STATIC
VOID
EFIAPI
TasWdtTick (
  IN EFI_EVENT  Event,
  IN VOID       *Context
  )
{
  TasWdtKick ();
}

EFI_STATUS
EFIAPI
FiqMaskInitialize (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  DirectLog ("TAS-WDT-RUN\n");

  TasWdtKick ();
  DirectLog ("TAS-WDT-KICK\n");

  if (gBS != NULL) {
    if (gBS->CreateEvent (
               EVT_TIMER,
               TPL_CALLBACK,
               TasWdtTick,
               NULL,
               &mWdtEvent
               ) == EFI_SUCCESS)
    {
      gBS->SetTimer (mWdtEvent, TimerPeriodic, 40000000ULL /* 4 s */);
      DirectLog ("TAS-WDT-ARMED\n");
    }
  }

  __asm__ __volatile__ ("msr daifset, #0x5" ::: "memory");
  __asm__ __volatile__ ("isb" ::: "memory");
  DirectLog ("TAS-DAIF-DONE\n");

  return EFI_SUCCESS;
}
