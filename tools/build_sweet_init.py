#!/usr/bin/env python3
"""Assemble tools/sweet-init.S and wrap it with mkinit.py to produce out/sweet-init Mach-O."""
import os, struct, sys
import keystone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mkinit

def assemble_sweet_init():
    ks = keystone.Ks(keystone.KS_ARCH_ARM64, keystone.KS_MODE_LITTLE_ENDIAN)

    # 1. Structure of sweet-init instructions
    # Each item: (label, asm_template)
    instructions = [
        # _start
        ("_start", "mov x9, sp"),
        (None, "and x9, x9, #0xfffffffffffffff0"),
        (None, "mov sp, x9"),
        (None, "adr x0, {path}"),
        (None, "mov x1, #2"),               # O_RDWR
        (None, "mov x2, #0"),
        (None, "mov x16, #5"),              # SYS_open
        (None, "svc #0x80"),
        (None, "b.cs {hang}"),
        (None, "mov x19, x0"),
        (None, "adr x1, {hello}"),
        (None, "adr x2, {hello_tail}"),
        (None, "sub x2, x2, x1"),
        (None, "bl {write_console}"),
        (None, "mov x16, #20"),             # SYS_getpid
        (None, "svc #0x80"),
        (None, "add w0, w0, #0x30"),        # +'0'
        (None, "sub sp, sp, #16"),
        (None, "strb w0, [sp]"),
        (None, "mov x1, sp"),
        (None, "mov x2, #1"),
        (None, "bl {write_console}"),
        (None, "add sp, sp, #16"),
        (None, "adr x1, {hello_tail}"),
        (None, "adr x2, {alive}"),
        (None, "sub x2, x2, x1"),
        (None, "bl {write_console}"),
        # tick
        ("tick", "mov x0, #0"),
        (None, "mov x1, #0"),
        (None, "mov x2, #0"),
        (None, "mov x3, #0"),
        (None, "adr x4, {five_sec}"),
        (None, "mov x16, #93"),             # SYS_select
        (None, "svc #0x80"),
        (None, "adr x1, {alive}"),
        (None, "adr x2, {alive_end}"),
        (None, "sub x2, x2, x1"),
        (None, "bl {write_console}"),
        (None, "b {tick}"),
        # write_console
        ("write_console", "mov x0, x19"),
        (None, "mov x16, #4"),              # SYS_write
        (None, "svc #0x80"),
        (None, "ret"),
        # hang
        ("hang", "b {hang}"),
    ]

    num_insts = len(instructions)
    code_size = num_insts * 4

    # Pad code_size to 8 bytes (.p2align 3)
    pad = (8 - (code_size % 8)) % 8
    data_start = code_size + pad

    # Data items
    five_sec_data = struct.pack('<QQ', 5, 0)
    path_data = b"/dev/console\0"
    hello_data = b"\n*** SWEET userspace: init running as PID "
    hello_tail_data = b" ***\n"
    alive_data = b"SWEET init: still alive\n"

    labels = {}
    # Code labels
    offset = 0
    for lbl, _ in instructions:
        if lbl:
            labels[lbl] = offset
        offset += 4

    # Data labels
    labels["five_sec"] = data_start
    labels["path"] = labels["five_sec"] + len(five_sec_data)
    labels["hello"] = labels["path"] + len(path_data)
    labels["hello_tail"] = labels["hello"] + len(hello_data)
    labels["alive"] = labels["hello_tail"] + len(hello_tail_data)
    labels["alive_end"] = labels["alive"] + len(alive_data)

    # 2. Assemble instructions with resolved relative offsets
    encoded_code = bytearray()
    curr_offset = 0
    for _, template in instructions:
        inst_str = template
        for target_label, target_off in labels.items():
            placeholder = "{" + target_label + "}"
            if placeholder in inst_str:
                rel = target_off - curr_offset
                inst_str = inst_str.replace(placeholder, str(rel))
        b, _ = ks.asm(inst_str)
        encoded_code += bytes(b)
        curr_offset += 4

    # Add padding
    encoded_code += b'\x00' * pad

    # Add data section
    encoded_code += five_sec_data
    encoded_code += path_data
    encoded_code += hello_data
    encoded_code += hello_tail_data
    encoded_code += alive_data

    print(f"[+] Total __text size: {len(encoded_code)} bytes")
    return bytes(encoded_code)

def wrap_macho(code, out_path):
    """Wraps code directly using mkinit logic."""
    start = 0
    assert mkinit.CODE_OFF + len(code) <= mkinit.SEG, 'code does not fit in one __TEXT page'
    sect = struct.pack('<16s16sQQIIIIIIII', b'__text', b'__TEXT', mkinit.BASE + mkinit.CODE_OFF, len(code),
                       mkinit.CODE_OFF, 3, 0, 0, mkinit.S_ATTR_CODE, 0, 0, 0)
    sig_size = len(mkinit.code_signature(bytes(mkinit.SEG), mkinit.SEG, mkinit.SEG, None))
    thread = struct.pack('<IIII', mkinit.LC_UNIXTHREAD, 16 + 4 * mkinit.ARM_THREAD_STATE64_COUNT,
                         mkinit.ARM_THREAD_STATE64, mkinit.ARM_THREAD_STATE64_COUNT)
    state = [0] * 33
    state[32] = mkinit.BASE + mkinit.CODE_OFF + start
    thread += struct.pack('<33QII', *state, 0, 0)
    cmds = [
        mkinit.segment('__PAGEZERO', 0, mkinit.BASE, 0, 0, 0),
        mkinit.segment('__TEXT', mkinit.BASE, mkinit.SEG, 0, mkinit.SEG, mkinit.VM_PROT_R | mkinit.VM_PROT_X, [sect]),
        mkinit.segment('__LINKEDIT', mkinit.BASE + mkinit.SEG, mkinit.SEG, mkinit.SEG, sig_size, mkinit.VM_PROT_R),
        thread,
        struct.pack('<4I', mkinit.LC_CODE_SIGNATURE, 16, mkinit.SEG, sig_size),
    ]
    lc = b''.join(cmds)
    header = struct.pack('<8I', mkinit.MH_MAGIC_64, mkinit.CPU_TYPE_ARM64, 0, mkinit.MH_EXECUTE, len(cmds), len(lc),
                         mkinit.MH_NOUNDEFS, 0)
    assert 32 + len(lc) <= mkinit.CODE_OFF
    image = bytearray(mkinit.SEG)
    image[:32 + len(lc)] = header + lc
    image[mkinit.CODE_OFF:mkinit.CODE_OFF + len(code)] = code
    sig = mkinit.code_signature(bytes(image), mkinit.SEG, mkinit.SEG, None)
    assert len(sig) == sig_size

    out_bytes = bytes(image) + sig
    with open(out_path, 'wb') as f:
        f.write(out_bytes)
    print(f"[+] Successfully generated static arm64 Mach-O: {out_path} ({len(out_bytes)} bytes)")

if __name__ == '__main__':
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out_file = os.path.join(root, "out", "sweet-init")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    code = assemble_sweet_init()
    wrap_macho(code, out_file)
