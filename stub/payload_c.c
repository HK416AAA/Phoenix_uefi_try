#include <stddef.h>
#include <stdint.h>

#define PSTORE_BASE 0x2f060000UL
#define PSTORE_SIG  0x43474244U
#define FB_LCD      0x36500000UL
#define FB_CANVAS   0x36ea3f80UL
#define FB_PIXELS   (1080U * 2340U)

static uint32_t woff;

static void cache_clean(const void *start, size_t len)
{
    uintptr_t p = (uintptr_t)start;
    uintptr_t end = p + len;

    for (; p < end; p += 64)
        asm volatile("dc cvac, %0" :: "r"(p) : "memory");
    asm volatile("dsb sy" ::: "memory");
}

static void pstore_mark(const char *s)
{
    volatile uint32_t *z = (volatile uint32_t *)PSTORE_BASE;
    volatile char *data = (volatile char *)(PSTORE_BASE + 12);
    size_t n = 0;

    while (s[n])
        n++;
    if (woff + n > 0xF000)
        return;

    for (size_t i = 0; i < n; i++)
        data[woff + i] = s[i];
    woff += n;

    z[1] = 0;
    z[2] = woff > 0x11000 ? woff : 0x11000;
    cache_clean((const void *)PSTORE_BASE, 0x12000);
    z[0] = PSTORE_SIG;
    cache_clean((const void *)PSTORE_BASE, 64);
}

static void hhee_tvm_enable(void)
{
    register uint64_t x0 asm("x0") = 0xC600108AUL;
    register uint64_t x1 asm("x1") = 0;

    asm volatile("hvc #0"
                 : "+r"(x0)
                 : "r"(x1)
                 : "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9",
                   "x10", "x11", "x12", "x13", "x14", "x15", "x16", "x17",
                   "memory");
}

static void fb_fill(uintptr_t base, uint32_t color)
{
    volatile uint32_t *p = (volatile uint32_t *)base;

    for (uint32_t i = 0; i < FB_PIXELS; i++)
        p[i] = color;
}

void payload_main(uint64_t dtb)
{
    (void)dtb;

    pstore_mark("TAS-C-1\n");
    hhee_tvm_enable();
    pstore_mark("TAS-C-2\n");
    fb_fill(FB_LCD, 0xFFFFFFFFU);
    pstore_mark("TAS-C-FB1\n");
    fb_fill(FB_CANVAS, 0xFFFFFFFFU);
    pstore_mark("TAS-C-FB2\n");
    pstore_mark("TAS-C-DONE\n");
}
