/*
 * C payload entry: keep the boot arguments, give payload_main a stack,
 * then return to stext so Android still boots.
 */
    .section .text
    .global _start

_start:
    b       _real_start
    .long   0                    /* code1 (unused) */
    .quad   0                    /* text_offset */
    .quad   _image_size          /* image_size (from the linker script) */
    .quad   0xa                  /* flags: PIE | 4 KiB pages */
    .quad   0, 0, 0              /* reserved */
    .ascii  "ARM\x64"            /* magic at offset 0x38 */
    .long   0                    /* reserved */

_real_start:
    mov     x19, x0
    mov     x20, x1
    mov     x21, x2
    mov     x22, x3

    adrp    x0, shim_enter
    add     x0, x0, :lo12:shim_enter
    bl      pstore_mark

    adrp    x0, stack_top
    add     x0, x0, :lo12:stack_top
    mov     sp, x0

    mov     x0, x19
    bl      payload_main

    adrp    x0, shim_back
    add     x0, x0, :lo12:shim_back
    bl      pstore_mark

    mov     x0, x19
    mov     x1, x20
    mov     x2, x21
    mov     x3, x22

    adr     x9, _start
    movz    x10, #0x0111, lsl #16
    sub     x9, x9, x10
    br      x9

    .section .rodata
    .align 3
shim_enter:
    .asciz "CHARLOTTE-SHIM: enter\n"
shim_back:
    .asciz "CHARLOTTE-SHIM: back\n"

    .section .bss
    .align 4
    .global payload_stack
payload_stack:
    .skip 65536
    .global stack_top
stack_top:
