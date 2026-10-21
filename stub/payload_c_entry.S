/*
 * C payload entry: keep the boot arguments, give payload_main a stack,
 * then return to stext so Android still boots.
 */
    .section .text
    .global _start

_start:
    mov     x19, x0
    mov     x20, x1
    mov     x21, x2
    mov     x22, x3

    adrp    x0, stack_top
    add     x0, x0, :lo12:stack_top
    mov     sp, x0

    mov     x0, x19
    bl      payload_main

    mov     x0, x19
    mov     x1, x20
    mov     x2, x21
    mov     x3, x22

    adr     x9, _start
    movz    x10, #0x0111, lsl #16
    sub     x9, x9, x10
    br      x9

    .section .bss
    .align 4
    .global payload_stack
payload_stack:
    .skip 65536
    .global stack_top
stack_top:
