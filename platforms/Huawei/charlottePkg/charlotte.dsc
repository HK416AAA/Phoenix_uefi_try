##
#  Minimal Huawei Charlotte (Kirin 9010) platform.
#
#  Reuses SiliciumPkg's SEC/DXE core, GIC, timer, BDS and null libraries.
#  No vendor SoC package is required for the first bring-up.
##

[Defines]
  PLATFORM_NAME                  = charlotte
  PLATFORM_GUID                  = 7B2C4D6E-8F0A-4B1C-9D2E-3F4A5B6C7D8E
  PLATFORM_VERSION               = 0.1
  DSC_SPECIFICATION              = 0x00010005
  OUTPUT_DIRECTORY               = Build/charlottePkg
  SUPPORTED_ARCHITECTURES        = AARCH64
  BUILD_TARGETS                  = RELEASE|DEBUG
  SKUID_IDENTIFIER               = DEFAULT
  FLASH_DEFINITION               = charlottePkg/charlotte.fdf
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
  gArmPlatformTokenSpaceGuid.PcdCPUCoresStackBase|0x80300000
  gArmPlatformTokenSpaceGuid.PcdCPUCorePrimaryStackSize|0x40000

  #
  # CPU
  #
  gArmPlatformTokenSpaceGuid.PcdCoreCount|8
  gArmPlatformTokenSpaceGuid.PcdClusterCount|3

  #
  # GICv3
  #
  gArmTokenSpaceGuid.PcdGicDistributorBase|0xff000000
  gArmTokenSpaceGuid.PcdGicRedistributorsBase|0xff040000

  #
  # Generic timer
  #
  gSiliciumPkgTokenSpaceGuid.PcdTimerFreqOverwrite|24000000

  #
  # Simple frame buffer (GOP may not find it in the vendor DTB)
  #
  gSiliciumPkgTokenSpaceGuid.PcdFrameBufferWidth|1840
  gSiliciumPkgTokenSpaceGuid.PcdFrameBufferHeight|2800
  gSiliciumPkgTokenSpaceGuid.PcdFrameBufferColorDepth|32

  #
  # SMBIOS
  #
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemManufacturer|"Huawei"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemModel|"Mate 70"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemRetailModel|"charlotte"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemRetailSku|"Charlotte"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosSystemBoardModel|"Charlotte"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosProcessorModel|"Kirin 9010"
  gSiliciumPkgTokenSpaceGuid.PcdSmbiosProcessorPartNumber|"Kirin9010"

[LibraryClasses]
  #
  # Platform memory map (FD, stack, heap, pstore, display, GIC, UFS)
  #
  MemoryMapLib|charlottePkg/Library/MemoryMapLib/MemoryMapLib.inf

  #
  # Debug and console go to the ramoops console zone (0x2f060000),
  # readable from /sys/fs/pstore/console-ramoops-0 after the next boot.
  #
  SerialPortLib|charlottePkg/Library/PstoreSerialPortLib/PstoreSerialPortLib.inf
  DebugLib|MdePkg/Library/BaseDebugLibSerialPort/BaseDebugLibSerialPort.inf
  UniXNULib|UniXNUPkg/Library/UniXNULib/UniXNULib.inf

[Components]
  charlottePkg/Drivers/FiqMaskDxe/FiqMaskDxe.inf
  UniXNUPkg/Application/UniXNU/UniXNU.inf
  UniXNUPkg/Driver/UniXNUDxe/UniXNUDxe.inf
  DarwinBootPkg/Driver/DarwinBoot.inf
