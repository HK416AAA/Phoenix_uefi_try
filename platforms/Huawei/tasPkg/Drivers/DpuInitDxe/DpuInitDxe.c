#include <Uefi.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/DebugLib.h>

#define LCD_DISPBUF     0x36500000ULL
#define CANVAS_BUF      0x36EA3F80ULL
#define FB_WIDTH        1080U
#define FB_HEIGHT       2340U
#define WDT_BASE        0xFE026000ULL

STATIC
VOID
WdtFeed (
  VOID
  )
{
  volatile UINT32 *Wdt = (volatile UINT32 *)WDT_BASE;

  /* SP805: unlock, load, enable, reload */
  Wdt[0xC00 / 4] = 0x1ACCE551;
  Wdt[0x000 / 4] = 0x00100000;
  Wdt[0x008 / 4] = 0x1;
  Wdt[0x000 / 4] = 0x00100000;
  Wdt[0x00C / 4] = 1;
  Wdt[0xC00 / 4] = 1;
}

STATIC
VOID
DrawRect (
  IN volatile UINT16 *Fb,
  IN INT32            X,
  IN INT32            Y,
  IN INT32            W,
  IN INT32            H,
  IN UINT16           Color
  )
{
  INT32 J;
  INT32 I;

  for (J = Y; J < Y + H; J++) {
    for (I = X; I < X + W; I++) {
      Fb[J * FB_WIDTH + I] = Color;
    }
  }
}

STATIC
VOID
DrawScreen (
  IN volatile UINT16 *Fb
  )
{
  UINT32 I;

  for (I = 0; I < FB_WIDTH * FB_HEIGHT; I++) {
    Fb[I] = 0xFFFF;
  }

  DrawRect (Fb, 200, 500, 680, 400, 0x0000);
  DrawRect (Fb, 230, 530, 620, 340, 0xFFFF);

  /* UnixNU block glyphs */
  DrawRect (Fb, 270, 600, 40, 120, 0x0000);
  DrawRect (Fb, 270, 700, 120, 20, 0x0000);
  DrawRect (Fb, 350, 600, 40, 120, 0x0000);
  DrawRect (Fb, 390, 620, 30, 100, 0x0000);
  DrawRect (Fb, 390, 620, 80, 20, 0x0000);
  DrawRect (Fb, 450, 620, 30, 100, 0x0000);
  DrawRect (Fb, 490, 620, 30, 20, 0x0000);
  DrawRect (Fb, 490, 660, 30, 60, 0x0000);
  DrawRect (Fb, 530, 620, 20, 20, 0x0000);
  DrawRect (Fb, 590, 620, 20, 20, 0x0000);
  DrawRect (Fb, 550, 640, 20, 20, 0x0000);
  DrawRect (Fb, 570, 660, 20, 20, 0x0000);
  DrawRect (Fb, 550, 680, 20, 20, 0x0000);
  DrawRect (Fb, 590, 700, 20, 20, 0x0000);
  DrawRect (Fb, 530, 700, 20, 20, 0x0000);

  DrawRect (Fb, 270, 760, 520, 20, 0xF800);
}

EFI_STATUS
EFIAPI
DpuInitEntry (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  DEBUG ((DEBUG_INFO, "DpuInit: lcd=0x%lx canvas=0x%lx %ux%u RGB565\n",
          LCD_DISPBUF, CANVAS_BUF, FB_WIDTH, FB_HEIGHT));

  DrawScreen ((volatile UINT16 *)LCD_DISPBUF);
  DEBUG ((DEBUG_INFO, "DpuInit: lcd written\n"));

  DrawScreen ((volatile UINT16 *)CANVAS_BUF);
  DEBUG ((DEBUG_INFO, "DpuInit: canvas written\n"));

  WdtFeed ();
  DEBUG ((DEBUG_INFO, "DpuInit: watchdog fed\n"));

  return EFI_SUCCESS;
}
