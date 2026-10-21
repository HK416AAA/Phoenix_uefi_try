/*
 * pstore checkpoint payload.
 *
 * Writes a persistent_ram_buffer record into the ramoops console zone at
 * 0x2f060000 (TAS: 1 MiB pstore-mem, record 0x20000, console 0x80000,
 * pmsg 0x20000 -> console starts at +0x60000), then jumps back to the
 * original stext so Android boots normally. The next pstore read exposes
 * the marker as /sys/fs/pstore/console-ramoops-0.
 */
    .section .text
    .global _start

_start:
    mov     x19, x0
    mov     x20, x1
    mov     x21, x2
    mov     x22, x3

    movz    x1, #0x2f06, lsl #16     /* 0x2f060000: console zone */
    add     x2, x1, #12              /* data[] */
    adr     x3, msg
    mov     x4, #(msg_end - msg)
1:
    ldrb    w5, [x3], #1
    strb    w5, [x2], #1
    subs    x4, x4, #1
    b.ne    1b

    str     wzr, [x1, #4]            /* start = 0 */
    mov     w2, #0x1000
    str     w2, [x1, #8]             /* size = 0x1000 */
    mov     w2, #0x4244
    movk    w2, #0x4347, lsl #16     /* 0x43474244 "DBGC" */
    str     w2, [x1]                 /* signature last */

    mov     x2, x1
    add     x3, x1, #0x1000
2:
    dc      cvac, x2
    add     x2, x2, #64
    cmp     x2, x3
    b.lo    2b
    dsb     sy

    mov     x0, x19
    mov     x1, x20
    mov     x2, x21
    mov     x3, x22

    /* stext runtime = payload runtime - 0x1110000 */
    adr     x9, _start
    movz    x10, #0x0111, lsl #16
    sub     x9, x9, x10
    br      x9

    .section .rodata
msg:
    .ascii "TAS-STEP1-PSTORE-OK\n"
msg_end:
