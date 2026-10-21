ENTRY(_start)

SECTIONS
{
  . = 0;

  .text : {
    *(.text*)
  }

  .rodata : {
    *(.rodata*)
  }

  .data : {
    *(.data*)
  }

  .bss : {
    *(.bss*)
    *(COMMON)
  }

  . = ALIGN(8);
  _end = .;
  _image_size = _end - _start;
}
