#include <stddef.h>
#include <stdint.h>

#define PSTORE_BASE 0x2f060000UL
#define PSTORE_SIG  0x43474244U
#define FB_LCD      0x36500000UL
#define FB_CANVAS   0x36ea3f80UL
#define FB_PIXELS   (1080U * 7020U)

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

static void draw_rect(volatile uint16_t *p, int x, int y, int rw, int rh, uint16_t c)
{
    for (int j = y; j < y + rh; j++)
        for (int i = x; i < x + rw; i++)
            p[j * 1080 + i] = c;
}

static void dpu_draw_logo(void)
{
    volatile uint16_t *p = (volatile uint16_t *)FB_LCD;

    draw_rect(p, 200, 500, 680, 400, 0x0000);
    draw_rect(p, 230, 530, 620, 340, 0xFFFF);

    draw_rect(p, 270, 600, 40, 120, 0x00000000U);
    draw_rect(p, 270, 700, 120, 20, 0x00000000U);
    draw_rect(p, 350, 600, 40, 120, 0x00000000U);
    draw_rect(p, 390, 620, 30, 100, 0x00000000U);
    draw_rect(p, 390, 620, 80, 20, 0x00000000U);
    draw_rect(p, 450, 620, 30, 100, 0x00000000U);
    draw_rect(p, 490, 620, 30, 20, 0x00000000U);
    draw_rect(p, 490, 660, 30, 60, 0x00000000U);
    draw_rect(p, 530, 620, 20, 20, 0x00000000U);
    draw_rect(p, 590, 620, 20, 20, 0x00000000U);
    draw_rect(p, 550, 640, 20, 20, 0x00000000U);
    draw_rect(p, 570, 660, 20, 20, 0x00000000U);
    draw_rect(p, 550, 680, 20, 20, 0x00000000U);
    draw_rect(p, 590, 700, 20, 20, 0x00000000U);
    draw_rect(p, 530, 700, 20, 20, 0x00000000U);

    draw_rect(p, 270, 760, 520, 20, 0xF800);
}

static void fb_fill16(uintptr_t base, uint16_t color)
{
    volatile uint16_t *p = (volatile uint16_t *)base;

    for (uint32_t i = 0; i < FB_PIXELS; i++)
        p[i] = color;
}

void payload_main(uint64_t dtb)
{
    (void)dtb;

    pstore_mark("TAS-DPU: lcd=0x36500000 canvas=0x36ea3f80\n");
    pstore_mark("TAS-DPU: 1080x7020 stride=4320 RGB565 16bit\n");
    pstore_mark("TAS-C-1\n");
    hhee_tvm_enable();
    pstore_mark("TAS-C-2\n");
    fb_fill16(FB_LCD, 0xFFFF);
    pstore_mark("TAS-C-FB1\n");
    fb_fill16(FB_CANVAS, 0xFFFF);
    pstore_mark("TAS-C-FB2\n");
    dpu_draw_logo();
    pstore_mark("TAS-DPU: logo-ok\n");
    pstore_mark("TAS-C-DONE\n");
}
