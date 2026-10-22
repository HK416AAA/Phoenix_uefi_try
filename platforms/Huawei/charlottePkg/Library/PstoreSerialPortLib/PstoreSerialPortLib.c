#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/CacheMaintenanceLib.h>
#include <Library/SerialPortLib.h>

//
// ramoops pmsg slot (0x2f0e0000, 0x20000). The console and dmesg
// zones are overwritten by the stock kernel during boot; pmsg survives.
//
#define PSTORE_BASE   0x2FD20000ULL
#define PSTORE_SIG    0x43474244U
#define PSTORE_CAP    0x20000U
#define PSTORE_LIMIT  0x1E000U

STATIC UINTN  mOffset;

STATIC
VOID
PstoreFlush (
  VOID
  )
{
  volatile UINT32  *Header;
  UINTN             Used;
  UINTN             Clean;

  Header = (volatile UINT32 *)(UINTN)PSTORE_BASE;
  Used   = mOffset + 12;
  Clean  = (Used + 63) & ~(UINTN)63;
  if (Clean > PSTORE_CAP) {
    Clean = PSTORE_CAP;
  }

  Header[1] = 0;
  Header[2] = (UINT32)((mOffset > 0x11000) ? mOffset : 0x11000);
  WriteBackInvalidateDataCacheRange ((VOID *)(UINTN)PSTORE_BASE, Clean);

  Header[0] = PSTORE_SIG;
  WriteBackInvalidateDataCacheRange ((VOID *)(UINTN)PSTORE_BASE, 64);
}

UINTN
EFIAPI
SerialPortWrite (
  IN UINT8  *Buffer,
  IN UINTN   NumberOfBytes
  )
{
  volatile UINT8  *Data;
  UINTN            Index;

  Data = (volatile UINT8 *)(UINTN)(PSTORE_BASE + 12);

  for (Index = 0; Index < NumberOfBytes; Index++) {
    if (mOffset >= PSTORE_LIMIT) {
      break;
    }

    Data[mOffset++] = Buffer[Index];
  }

  PstoreFlush ();
  return NumberOfBytes;
}

UINTN
EFIAPI
SerialPortRead (
  OUT UINT8  *Buffer,
  IN  UINTN   NumberOfBytes
  )
{
  return 0;
}

BOOLEAN
EFIAPI
SerialPortPoll (
  VOID
  )
{
  return FALSE;
}

EFI_STATUS
EFIAPI
SerialPortSetControl (
  IN UINT32  Control
  )
{
  return EFI_UNSUPPORTED;
}

EFI_STATUS
EFIAPI
SerialPortGetControl (
  OUT UINT32  *Control
  )
{
  return EFI_UNSUPPORTED;
}

EFI_STATUS
EFIAPI
SerialPortSetAttributes (
  IN OUT UINT64              *BaudRate,
  IN OUT UINT32              *ReceiveFifoDepth,
  IN OUT UINT32              *Timeout,
  IN OUT EFI_PARITY_TYPE     *Parity,
  IN OUT UINT8               *DataBits,
  IN OUT EFI_STOP_BITS_TYPE  *StopBits
  )
{
  return EFI_UNSUPPORTED;
}

EFI_STATUS
EFIAPI
SerialPortInitialize (
  VOID
  )
{
  mOffset = 0;
  return EFI_SUCCESS;
}
