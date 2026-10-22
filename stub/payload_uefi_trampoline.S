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

    movz    x0, #0x108A
    movk    x0, #0xC600, lsl #16
    mov     x1, #0
    hvc     #0

    mov     x0, x19
    mov     x1, x20
    mov     x2, x21
    mov     x3, x22

    /* next instruction is the first byte of BootShim.bin */
    b       1f
1:
