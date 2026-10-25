ENTRY(_start)

SECTIONS
{
  . = 0;

  .text : {
    KEEP(*(.text*))
  }

  .rodata : {
    KEEP(*(.rodata*))
  }

  .data : {
    KEEP(*(.data*))
  }

  .bss : {
    KEEP(*(.bss*))
    KEEP(*(COMMON))
  }

  . = ALIGN(8);
  _end = .;
  _image_size = _end - _start;
}
