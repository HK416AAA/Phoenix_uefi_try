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

    /* pmsg checkpoint at 0x2f0e0000: "TAS-TRAMP-OK\n" */
    movz    x1, #0x2f0e, lsl #16
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

    /* HHEE TVM handshake */
    movz    x0, #0x108A
    movk    x0, #0xC600, lsl #16
    mov     x1, #0
    hvc     #0

    mov     x0, x19
    mov     x1, x20
    mov     x2, x21
    mov     x3, x22

    /* next instruction is the first byte of BootShim.bin */
    b       2f
2:
