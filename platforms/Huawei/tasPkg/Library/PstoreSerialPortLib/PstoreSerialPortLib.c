#include <Library/BaseLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/CacheMaintenanceLib.h>
#include <Library/SerialPortLib.h>

//
// ramoops dmesg slot 0 (0x2f000000, record 0x20000).
//
#define PSTORE_BASE   0x2F000000ULL
#define PSTORE_SIG    0x43474244U
#define PSTORE_CAP    0x20000U
#define PSTORE_LIMIT  0x1E000U

//
// PL011 UART0: 0xfa054000, 19.2 MHz, 115200 8N1.
//
#define UART0_BASE    0xFA054000ULL
#define UART_DR       0x00
#define UART_FR       0x18
#define UART_IBRD     0x24
#define UART_FBRD     0x28
#define UART_LCRH     0x2C
#define UART_CR       0x30
#define UART_FR_TXFF  (1U << 5)
#define UART_FR_RXFE  (1U << 4)

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

STATIC
VOID
UartInit (
  VOID
  )
{
  volatile UINT32  *Cr;
  volatile UINT32  *Ibrd;
  volatile UINT32  *Fbrd;
  volatile UINT32  *Lcr;

  Cr   = (volatile UINT32 *)(UINTN)(UART0_BASE + UART_CR);
  Ibrd = (volatile UINT32 *)(UINTN)(UART0_BASE + UART_IBRD);
  Fbrd = (volatile UINT32 *)(UINTN)(UART0_BASE + UART_FBRD);
  Lcr  = (volatile UINT32 *)(UINTN)(UART0_BASE + UART_LCRH);

  *Cr   = 0;
  *Ibrd = 10;   /* 19.2 MHz / (16 * 115200) = 10.4167 */
  *Fbrd = 27;
  *Lcr  = 0x70; /* 8N1, FIFO enabled */
  *Cr   = 0x301; /* UARTEN | TXE | RXE */
}

STATIC
VOID
UartPutC (
  IN UINT8  Byte
  )
{
  volatile UINT32  *Fr;
  volatile UINT32  *Dr;
  UINTN             Timeout;

  Fr      = (volatile UINT32 *)(UINTN)(UART0_BASE + UART_FR);
  Dr      = (volatile UINT32 *)(UINTN)(UART0_BASE + UART_DR);
  Timeout = 100000;
  while ((*Fr & UART_FR_TXFF) != 0 && Timeout-- != 0) {
  }
  *Dr = Byte;
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
    UartPutC (Buffer[Index]);

    if (mOffset < PSTORE_LIMIT) {
      Data[mOffset++] = Buffer[Index];
    }
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
  volatile UINT32  *Fr;
  volatile UINT32  *Dr;
  UINTN             Count;

  Fr    = (volatile UINT32 *)(UINTN)(UART0_BASE + UART_FR);
  Dr    = (volatile UINT32 *)(UINTN)(UART0_BASE + UART_DR);
  Count = 0;

  while (Count < NumberOfBytes && (*Fr & UART_FR_RXFE) == 0) {
    Buffer[Count++] = (UINT8)*Dr;
  }

  return Count;
}

BOOLEAN
EFIAPI
SerialPortPoll (
  VOID
  )
{
  volatile UINT32  *Fr;

  Fr = (volatile UINT32 *)(UINTN)(UART0_BASE + UART_FR);
  return (*Fr & UART_FR_RXFE) == 0;
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
  UartInit ();
  mOffset = 0;
  return EFI_SUCCESS;
}
