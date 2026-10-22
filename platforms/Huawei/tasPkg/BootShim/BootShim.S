_Head:
  adr   x1, _Payload    /* Set _Entry address */
  b     _Start          /* Jump to the real code */

#if REQUIRES_KERNEL_HEADER == 1
_StackBase:
  .quad FD_BASE         /* Text Offset */

_StackSize:
  .quad FD_SIZE         /* Image Size */
  .quad 0               /* Flags */
  .quad 0               /* Reserved */
  .quad 0               /* Reserved */
  .quad 0               /* Reserved */
  .ascii "ARM\x64"      /* ARM64 Magic */
  .long 0               /* Reserved */
#endif

_Start:
  mov   x19, x0
  mov   x20, x1

  /* pmsg checkpoint: TAS-SHIM\n (before the copy) */
  movz  x1, #0x2f0e, lsl #16
  movz  w2, #0x4154
  movk  w2, #0x2D53, lsl #16
  str   w2, [x1, #12]
  movz  w2, #0x4853
  movk  w2, #0x4D49, lsl #16
  str   w2, [x1, #16]
  movz  w2, #0x000A
  str   w2, [x1, #20]

  str   wzr, [x1, #4]
  mov   w2, #0x1000
  str   w2, [x1, #8]
  mov   w2, #0x4244
  movk  w2, #0x4347, lsl #16
  str   w2, [x1]

  mov   x2, x1
  add   x3, x1, #0x1000
8:
  dc    cvac, x2
  add   x2, x2, #64
  cmp   x2, x3
  b.lo  8b
  dsb   sy

  mov   x1, x20
  mov   x0, x19
  mov   x4, x1
  ldr   x5, =FD_BASE
  cmp   x4, x5
  beq   _Entry
  ldr   x6,  =FD_SIZE

_CopyLoop:
  ldp   x2, x3, [x4], #16
  stp   x2, x3, [x5], #16
  subs  x6, x6, #16
  b.ne  _CopyLoop
  ldr   x5, =FD_BASE

_Entry:
  /* pmsg checkpoint: TAS-BOOTSHIM\n at 0x2f0e0000 */
  mov   x19, x0
  movz  x1, #0x2f0e, lsl #16
  movz  w2, #0x4154
  movk  w2, #0x2D53, lsl #16
  str   w2, [x1, #12]
  movz  w2, #0x4F42
  movk  w2, #0x544F, lsl #16
  str   w2, [x1, #16]
  movz  w2, #0x4853
  movk  w2, #0x4D49, lsl #16
  str   w2, [x1, #20]
  movz  w2, #0x000A
  str   w2, [x1, #24]

  str   wzr, [x1, #4]
  mov   w2, #0x1000
  str   w2, [x1, #8]
  mov   w2, #0x4244
  movk  w2, #0x4347, lsl #16
  str   w2, [x1]

  mov   x2, x1
  add   x3, x1, #0x1000
9:
  dc    cvac, x2
  add   x2, x2, #64
  cmp   x2, x3
  b.lo  9b
  dsb   sy

  mov   x0, x19
  br    x5

_Dead:
  b     _Dead

.text
.align 4

_Payload:
