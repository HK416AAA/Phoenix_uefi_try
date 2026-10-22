#include <Uefi.h>
#include <Library/BaseLib.h>
#include <Library/SerialPortLib.h>
#include <Library/UefiBootServicesTableLib.h>

#define IPC_BASE      0xFE101000UL
#define IPC_LOCK      0x0A00
#define IPC_UNLOCK    0x1ACCE551U
#define IPC_CHN       29
#define IPC_STRIDE    64
#define IPC_IDLE      0x10
#define IPC_SRC       0x1
#define IPC_DES       0x2
#define IPC_CMD_WDTT  0x00080201U
#define IPC_TIMEOUT   24
#define PMSG_BASE     0x2F0E0000UL

STATIC EFI_EVENT  mIpcEvent;

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
MarkHigh (
  IN CONST CHAR8  *Text
  )
{
  volatile UINT8   *Data;
  volatile UINT32  *Header;
  UINTN             Index;
  UINTN             Address;

  Data   = (volatile UINT8 *)(UINTN)(PMSG_BASE + 12 + 0x8000);
  Header = (volatile UINT32 *)(UINTN)PMSG_BASE;

  for (Index = 0; Text[Index] != 0; Index++) {
    Data[Index] = (UINT8)Text[Index];
  }
  Data[Index] = 0;

  Header[1] = 0;
  Header[2] = 0x11000;

  for (Address = PMSG_BASE; Address < PMSG_BASE + 0x11000; Address += 64) {
    __asm__ __volatile__ ("dc cvac, %0" :: "r" (Address) : "memory");
  }
  __asm__ __volatile__ ("dsb sy" ::: "memory");

  Header[0] = 0x43474244;
  __asm__ __volatile__ ("dc cvac, %0" :: "r" (Header) : "memory");
  __asm__ __volatile__ ("dsb sy" ::: "memory");
}

STATIC
BOOLEAN
Lpm3Notify (
  VOID
  )
{
  volatile UINT32  *Base;
  volatile UINT32  *Lock;
  UINT32            Off;
  UINTN             Index;

  Base = (volatile UINT32 *)(UINTN)IPC_BASE;
  Lock = (volatile UINT32 *)(UINTN)(IPC_BASE + IPC_LOCK);
  Off  = IPC_CHN * IPC_STRIDE;

  *Lock = IPC_UNLOCK;
  if (*Lock != 0) {
    DirectLog ("TAS-IPC-LOCKFAIL\n");
    MarkHigh ("TAS-IPC-LOCKFAIL");
    return FALSE;
  }

  for (Index = 0; Index < 10; Index++) {
    if ((Base[(Off + 0x10) / 4] & IPC_IDLE) != 0) {
      break;
    }
    gBS->Stall (10);
  }

  Base[(Off + 0x00) / 4] = IPC_SRC;
  if ((Base[(Off + 0x00) / 4] & IPC_SRC) == 0) {
    DirectLog ("TAS-IPC-SRCFAIL\n");
    MarkHigh ("TAS-IPC-SRCFAIL");
    return FALSE;
  }

  Base[(Off + 0x14) / 4] = ~0U;
  Base[(Off + 0x14) / 4] = Base[(Off + 0x14) / 4] & ~(UINT32)IPC_DES;
  Base[(Off + 0x04) / 4] = IPC_DES;
  Base[(Off + 0x10) / 4] = 1; /* AUTOMATIC_ACK_CONFIG */
  Base[(Off + 0x20) / 4] = IPC_CMD_WDTT;
  Base[(Off + 0x24) / 4] = IPC_TIMEOUT;
  Base[(Off + 0x1C) / 4] = IPC_SRC;

  MarkHigh ("TAS-IPC-SENT");
  return TRUE;
}

STATIC
VOID
EFIAPI
Lpm3Tick (
  IN EFI_EVENT  Event,
  IN VOID       *Context
  )
{
  Lpm3Notify ();
}

EFI_STATUS
EFIAPI
FiqMaskInitialize (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  DirectLog ("TAS-IPC-RUN\n");

  if (Lpm3Notify ()) {
    DirectLog ("TAS-IPC-SENT\n");
  }

  if (gBS != NULL) {
    if (gBS->CreateEvent (
               EVT_TIMER,
               TPL_CALLBACK,
               Lpm3Tick,
               NULL,
               &mIpcEvent
               ) == EFI_SUCCESS)
    {
      gBS->SetTimer (mIpcEvent, TimerPeriodic, 40000000ULL /* 4 s */);
      DirectLog ("TAS-IPC-ARMED\n");
    }
  }

  __asm__ __volatile__ ("msr daifset, #0x5" ::: "memory");
  __asm__ __volatile__ ("isb" ::: "memory");
  DirectLog ("TAS-DAIF-DONE\n");

  return EFI_SUCCESS;
}
