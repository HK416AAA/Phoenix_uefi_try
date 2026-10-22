##
#  Minimal Huawei TAS-AL00 (Kirin 990) platform.
#
#  Reuses SiliciumPkg's SEC/DXE core, GIC, timer, BDS and null libraries.
#  No vendor SoC package is required for the first bring-up.
##

[Defines]
  PLATFORM_NAME                  = tas
  PLATFORM_GUID                  = 6C1E7A2B-3F4D-4A5E-9B6C-7D8E9F0A1B2C
  PLATFORM_VERSION               = 0.1
  DSC_SPECIFICATION              = 0x00010005
  OUTPUT_DIRECTORY               = Build/tasPkg
  SUPPORTED_ARCHITECTURES        = AARCH64
  BUILD_TARGETS                  = RELEASE|DEBUG
  SKUID_IDENTIFIER               = DEFAULT
  FLASH_DEFINITION               = tasPkg/tas.fdf
  USE_CUSTOM_DISPLAY_DRIVER      = 0

!include SiliciumPkg/SiliciumPkg.dsc.inc

[PcdsFixedAtBuild]
  #
  # DDR
  #
  gArmTokenSpaceGuid.PcdSystemMemoryBase|0x400000

  #
  # UEFI Stack (FD ends at 0x3700000)
  #
  gArmPlatformTokenSpaceGuid.PcdCPUCoresStackBase|0x3800000
  gArmPlatformTokenSpaceGuid.PcdCPUCorePrimaryStackSize|0x40000

  #
  # CPU
  #
  gArmPlatformTokenSpaceGuid.PcdCoreCount|8
  gArmPlatformTokenSpaceGuid.PcdClusterCount|3

  #
  # GICv3
  #
  gArmTokenSpaceGuid.PcdGicDistributorBase|0xfe400000
  gArmTokenSpaceGuid.PcdGicRedistributorsBase|0xfe440000

  #
  # Generic timer
  #
  gSiliciumPkgTokenSpaceGuid.PcdTimerFreqOverwrite|1920000

  #
  # Simple frame buffer (GOP may not find it in the vendor DTB)
  #
  gSiliciumPkgTokenSpaceGuid.PcdFrameBufferWidth|1080
  gSiliciumPkgTokenSpaceGuid.PcdFrameBufferHeight|2340
  gSiliciumPkgTokenSpaceGuid.PcdFrameBufferColorDepth|32

  #
  # SMBIOS
  #
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemManufacturer|"Huawei"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemModel|"Mate 30"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemRetailModel|"tas"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemRetailSku|"TAS-AL00"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemBoardModel|"TAS-AL00"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosProcessorModel|"Kirin 990"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosProcessorPartNumber|"Kirin990"

[LibraryClasses]
  #
  # Platform memory map (FD, stack, heap, pstore, display, GIC, UFS)
  #
  MemoryMapLib|tasPkg/Library/MemoryMapLib/MemoryMapLib.inf

  #
  # Debug and console go to the ramoops console zone (0x2f060000),
  # readable from /sys/fs/pstore/console-ramoops-0 after the next boot.
  #
  SerialPortLib|tasPkg/Library/PstoreSerialPortLib/PstoreSerialPortLib.inf
  DebugLib|MdePkg/Library/BaseDebugLibSerialPort/BaseDebugLibSerialPort.inf
