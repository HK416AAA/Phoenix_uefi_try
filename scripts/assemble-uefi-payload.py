import gzip
import struct
from pathlib import Path

tramp = Path("builds/payload-uefi-trampoline.bin").read_bytes()
shim = Path("builds/tas-bootshim.bin").read_bytes()
fv = gzip.decompress(Path("builds/tas-uefi.fd.gz").read_bytes())

print(f"trampoline : {len(tramp)} bytes")
print(f"bootshim   : {len(shim)} bytes")
print(f"fv         : {len(fv)} bytes ({len(fv):#x})")
if len(fv) != 0x300000:
    raise SystemExit(f"unexpected FV size {len(fv):#x}, expected 0x300000")

start = 0x31E0000
target = 0x4000000
jump = struct.pack("<I", 0x14000000 | ((target - start) >> 2))
print(f"jump       : {jump.hex()} (0x{start:x} -> 0x{target:x})")

blob = jump + b"\0" * (target - start - 4) + tramp + shim + fv
Path("uefi-payload.bin").write_bytes(blob)
print(f"payload    : {len(blob)} bytes ({len(blob):#x})")
print(f"image end  : {start + len(blob):#x}")
