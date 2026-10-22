/*
 * HHEE TVM handshake trampoline.
 *
 * Runs before BootShim, preserves the boot arguments, performs
 * hvc 0xC600108A (hkip_tvm_enable) and falls through into BootShim,
 * which is concatenated immediately after this blob.
 */
    .section .text
    .global _start

_start:
    mov     x19, x0
    mov     x20, x1
    mov     x21, x2
    mov     x22, x3

    /* charlotte-style: keep SError and FIQ masked */
    msr     daifset, #0x5
    isb

    /* pmsg checkpoint at 0x2f0e0000: "TAS-TRAMP-OK\n" */
    movz    x1, #0x2f0e, lsl #16

    /* clear the previous boot's pmsg data so logs are current */
    mov     x4, x1
    movz    x5, #0x2400
3:
    str     xzr, [x4], #8
    subs    x5, x5, #1
    b.ne    3b

    movz    w2, #0x4154
    movk    w2, #0x2D53, lsl #16
    str     w2, [x1, #12]
    movz    w2, #0x5254
    movk    w2, #0x4D41, lsl #16
    str     w2, [x1, #16]
    movz    w2, #0x2D50
    movk    w2, #0x4B4F, lsl #16
    str     w2, [x1, #20]
    movz    w2, #0x000A
    str     w2, [x1, #24]

    str     wzr, [x1, #4]
    mov     w2, #0x1000
    str     w2, [x1, #8]
    mov     w2, #0x4244
    movk    w2, #0x4347, lsl #16
    str     w2, [x1]

    mov     x2, x1
    add     x3, x1, #0x1000
1:
    dc      cvac, x2
    add     x2, x2, #64
    cmp     x2, x3
    b.lo    1b
    dsb     sy

    /* TAS LPM3 IPC notify: 0xFE101000, lock 0xA00, ch29, stride 64 */
    movz    x1, #0xfe10, lsl #16
    movk    x1, #0x1000
    movz    w2, #0xe551
    movk    w2, #0x1acc, lsl #16
    add     x3, x1, #0xa00
    str     w2, [x3]
    ldr     w2, [x3]
    cbnz    w2, 12f

    add     x4, x1, #0x740
    mov     x6, #1000
10:
    ldr     w5, [x4, #0x10]
    tst     w5, #0x10
    b.ne    11f
    subs    x6, x6, #1
    b.ne    10b
    b       12f

11:
    mov     w5, #1
    str     w5, [x4, #0x00]
    ldr     w5, [x4, #0x00]
    tst     w5, #1
    b.eq    12f

    movn    w5, #0
    str     w5, [x4, #0x14]
    ldr     w5, [x4, #0x14]
    bic     w5, w5, #2
    str     w5, [x4, #0x14]

    mov     w5, #2
    str     w5, [x4, #0x04]
    mov     w5, #1
    str     w5, [x4, #0x10]
    movz    w5, #0x0201
    movk    w5, #0x0008, lsl #16
    str     w5, [x4, #0x20]
    mov     w5, #24
    str     w5, [x4, #0x24]
    mov     w5, #1
    str     w5, [x4, #0x1c]

12:

    /* HHEE TVM handshake */
    movz    x0, #0x108A
    movk    x0, #0xC600, lsl #16
    mov     x1, #0
    hvc     #0

    /* Record the HVC result: 0 = OK, nonzero = ERR. */
    movz    x1, #0x2f0e, lsl #16
    cbnz    x0, 4f

    movz    w2, #0x4154
    movk    w2, #0x2D53, lsl #16
    str     w2, [x1, #12]
    movz    w2, #0x5648
    movk    w2, #0x2D43, lsl #16
    str     w2, [x1, #16]
    movz    w2, #0x4B4F
    movk    w2, #0x000A, lsl #16
    str     w2, [x1, #20]
    b       5f

4:
    movz    w2, #0x4154
    movk    w2, #0x2D53, lsl #16
    str     w2, [x1, #12]
    movz    w2, #0x5648
    movk    w2, #0x2D43, lsl #16
    str     w2, [x1, #16]
    movz    w2, #0x5245
    movk    w2, #0x0A52, lsl #16
    str     w2, [x1, #20]

5:
    str     wzr, [x1, #4]
    mov     w2, #0x1000
    str     w2, [x1, #8]
    mov     w2, #0x4244
    movk    w2, #0x4347, lsl #16
    str     w2, [x1]

    mov     x2, x1
    add     x3, x1, #0x1000
6:
    dc      cvac, x2
    add     x2, x2, #64
    cmp     x2, x3
    b.lo    6b
    dsb     sy

    mov     x0, x19
    mov     x1, x20
    mov     x2, x21
    mov     x3, x22

    /* next instruction is the first byte of BootShim.bin */
    b       2f
    .balign 16
2:
