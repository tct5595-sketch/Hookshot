"""Read-only storage buffers are bound to their pool's end by default.

The console's global loads have no bounds: a shader may read records past the size word its storage buffer descriptor
gives. Bound to the size word, those reads came back 0 here. The targeting cursor (program 13afdae0385d7afe) reads its
four arrows' 256-byte transforms from a buffer whose size word says 16 KB, and only the arrows whose records fell inside
were drawn: 1-3 of 4 (the grass's culling, Lichii bf3f395c9, the same). A read-only single buffer is bound to the end of
its pool, 64 MB at most; one the program writes keeps its range, so a copy back to guest memory never reaches past
the buffer. RX_VK_SSBO_STRETCH=0 binds the size word's range, as before.
python -I -B tests/test_ssbo_stretch.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "gpu" / "vk" / "vk_draw.cpp"


def main():
    source = SOURCE.read_text(encoding="utf-8")
    switch = 'getenv("RX_VK_SSBO_STRETCH")'
    if switch not in source:
        raise SystemExit("no RX_VK_SSBO_STRETCH switch")
    at = source.index(switch)
    flag = source[source.rindex("static const bool stretch", 0, at):source.index(";", at) + 1]
    if "!getenv(\"RX_VK_SSBO_STRETCH\") ||" not in flag or 'strcmp(getenv("RX_VK_SSBO_STRETCH"), "0") != 0' not in flag:
        raise SystemExit("stretch is not on by default with =0 to turn it off: %s" % flag)
    cond = "if (stretch && !d.is_written && addr && d.count == 1)"
    if cond not in source:
        raise SystemExit("stretch is not limited to read-only single buffers")
    body = source[source.index(cond):source.index("}", source.index(cond))]
    if "gpu_pool_end(base)" not in body or "64ull << 20" not in body:
        raise SystemExit("stretch must stop at the pool's end, 64 MB at most")
    bind = "BufferRef b = addr && plausible ? gpu_buffer_bind(base, n,"
    if bind not in source or not source.index(cond) < source.index(bind):
        raise SystemExit("the stretched range must be what gets bound")
    print("storage buffer stretch ok")


if __name__ == "__main__":
    main()
