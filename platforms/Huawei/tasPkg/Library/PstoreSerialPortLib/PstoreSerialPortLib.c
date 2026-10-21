#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/CacheMaintenanceLib.h>
#include <Library/SerialPortLib.h>

//
// ramoops console zone: pstore-mem 0x2f000000 (1 MiB),
// record 0x20000 + console 0x80000 + pmsg 0x20000 -> console at +0x60000.
//
#define PSTORE_BASE  0x2F060000ULL
#define PSTORE_SIG   0x43474244U
#define PSTORE_CAP   0x12000U
#define PSTORE_LIMIT 0xF000U

STATIC UINTN  mOffset;

STATIC
VOID
PstoreFlush (
  VOID
  )
{
  volatile UINT32  *Header;
  UINT32            Size;

  Header    = (volatile UINT32 *)(UINTN)PSTORE_BASE;
  Size      = (UINT32)((mOffset > 0x11000) ? mOffset : 0x11000);
  Header[1] = 0;
  Header[2] = Size;

  WriteBackInvalidateDataCacheRange ((VOID *)(UINTN)PSTORE_BASE, PSTORE_CAP);

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
