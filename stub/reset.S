/*
 * Reset-only payload.
 *
 * Purpose: prove that HHEE actually transfers control to the image we put in
 * the boot partition. PSCI SYSTEM_RESET is what the kernel itself uses, so if
 * the stub runs the phone reboots within a second. If it stays on the unlock
 * warning screen, the stub never executed.
 */
    .section .text
    .global _start

_start:
    b       _real_start
    .long   0
    .quad   0
    .quad   _image_size
    .quad   0xa
    .quad   0, 0, 0
    .ascii  "ARM\x64"
    .long   0

_real_start:
    movz    w0, #0x0009
    movk    w0, #0x8400, lsl #16     /* 0x84000009: PSCI SYSTEM_RESET */
    smc     #0
1:
    wfi
    b       1b

    .section .rodata
    .align 3
