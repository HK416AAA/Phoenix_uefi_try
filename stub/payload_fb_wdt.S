/*
 * Framebuffer + watchdog probe. No SMC, no PSCI.
 *
 * 1. Program the SP805 watchdog to reset after roughly 32 s (32 kHz) or
 *    43 ms (24 MHz), so a successful execution is visible as a reboot even
 *    if the framebuffer write is not being scanned.
 * 2. Paint lcd_dispbuf (0x36500000) and canvas_buf (0x36ea3f80).
 */
    .section .text
    .global _start

_start:
    /* SP805: unlock, LOAD=0x100000, CONTROL=enable+reset */
    movz    x1, #0xfe02, lsl #16
    movk    x1, #0x6000
    movz    w2, #0xE551
    movk    w2, #0x1ACC, lsl #16
    str     w2, [x1, #0xC00]
    movz    w2, #0x0010, lsl #16
    str     w2, [x1]
    mov     w2, #3
    str     w2, [x1, #8]

    /* lcd_dispbuf */
    movz    x1, #0x3650, lsl #16
    movz    w2, #0xFFFF, lsl #16
    movz    x3, #0x2690
    lsl     x3, x3, #8
1:
    str     w2, [x1], #4
    subs    x3, x3, #1
    b.ne    1b

    /* canvas_buf */
    movz    x1, #0x36ea, lsl #16
    movk    x1, #0x3f80
    movz    x3, #0x2690
    lsl     x3, x3, #8
2:
    str     w2, [x1], #4
    subs    x3, x3, #1
    b.ne    2b

3:
    wfi
    b       3b
