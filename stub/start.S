/*
 * Minimal payload for TAS-AL00 (Kirin 990).
 *
 * ABL decompresses Image.gz to 0x80000 and jumps to offset 0.
 * The first 64 bytes mimic an ARM64 Image header so anything that checks
 * the "ARM\x64" magic is satisfied, then we branch to the real entry.
 *
 * The payload paints the boot logo buffer at 0x36500000 and spins.
 * If the panel is still scanning that buffer, the screen turns solid color.
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
    movz    x1, #0x3650, lsl #16     /* 0x36500000: logo buffer */
    movz    w2, #0xFFFF, lsl #16     /* 0xFFFF0000: solid colour */
    movz    x3, #0x2690             /* 0x269000 = 1080 * 2340 (rounded) */
    lsl     x3, x3, #8

1:
    str     w2, [x1], #4
    subs    x3, x3, #1
    b.ne    1b

2:
    wfi
    b       2b

    .section .rodata
    .align 3
