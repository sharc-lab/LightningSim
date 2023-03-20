#!/opt/anaconda1anaconda2anaconda3/bin/python3

import re
from argparse import ArgumentParser
from os import environ
from pathlib import Path
from tempfile import TemporaryDirectory
from subprocess import Popen
from typing import List, Tuple

CXXFLAGS = [
    "-g",
    "-emit-llvm",
    "-Xclang",
    "-no-opaque-pointers",
    "-c",
    "-S",
    "-isystem",
    Path(environ["PREFIX"]) / "include",
]

REPLACEMENT_MAP: List[Tuple[re.Pattern, re.Pattern, str]] = [
    (
        re.compile(r"i"),
        re.compile(r"l"),
        r"{{len(T)}}{{T}}",
    ),
    (
        re.compile(r"i32"),
        re.compile(r"i64"),
        r"{{T}}",
    ),
    (
        re.compile(r",? align 4"),
        re.compile(r",? align 8"),
        r"",
    ),
    (
        re.compile(r" noundef 4"),
        re.compile(r" noundef 8"),
        r" noundef {{(N + 7) // 8}}",
    ),
    (
        re.compile(r"dereferenceable\(4\)"),
        re.compile(r"dereferenceable\(8\)"),
        r"dereferenceable({{(N + 7) // 8}})",
    ),
    (
        re.compile(r"i64 @_ZSt16__deque_buf_sizem\(i64 4\)"),
        re.compile(r"i64 @_ZSt16__deque_buf_sizem\(i64 8\)"),
        r"i64 @_ZSt16__deque_buf_sizem(i64 {{(N + 7) // 8}})",
    ),
    (
        re.compile(r"mul i64 %([\w\.]+), 4,"),
        re.compile(r"mul i64 %([\w\.]+), 8,"),
        r"mul i64 %\1, {{(N + 7) // 8}},",
    ),
    (
        re.compile(r"4611686018427387903"),
        re.compile(r"2305843009213693951"),
        r"{{0xffffffffffffffff // ((N + 7) // 8)}}",
    ),
    (
        re.compile(r"2305843009213693951"),
        re.compile(r"1152921504606846975"),
        r"{{0x7fffffffffffffff // ((N + 7) // 8)}}",
    ),
    (
        re.compile(r"sdiv exact i64 %([\w\.]+), 4,"),
        re.compile(r"sdiv exact i64 %([\w\.]+), 8,"),
        r"sdiv exact i64 %\1, {{(N + 7) // 8}},",
    ),
    (
        re.compile(r"\[50 x i8\]"),
        re.compile(r"\[50 x i8\]"),
        r"[{{(len(T) * 3) + 23}} x i8]",
    ),
    (
        re.compile(r'c"std::int32_t _autotb_FifoRead_i32\(std::int32_t \*\)\\00"'),
        re.compile(r'c"std::int64_t _autotb_FifoRead_i64\(std::int64_t \*\)\\00"'),
        r'c"{{T}} _autotb_FifoRead_{{T}}({{T}} *)\\00"',
    ),
]

FIRST_COPY_LINE = "!0 = !DIGlobalVariableExpression(var: !1, expr: !DIExpression())\n"


def main():
    parser = ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("-c", "--cxx", type=str, default="clang-15")
    args = parser.parse_args()

    with TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        subprocess_generate_i32 = Popen(
            [
                args.cxx,
                args.input,
                *CXXFLAGS,
                "-DT=std::int32_t",
                "-D_autotb_FifoRead_iN=_autotb_FifoRead_i32",
                "-D_autotb_FifoWrite_iN=_autotb_FifoWrite_i32",
                "-o",
                tmpdir / "fifo_i32.ll",
            ]
        )
        subprocess_generate_i64 = Popen(
            [
                args.cxx,
                args.input,
                *CXXFLAGS,
                "-DT=std::int64_t",
                "-D_autotb_FifoRead_iN=_autotb_FifoRead_i64",
                "-D_autotb_FifoWrite_iN=_autotb_FifoWrite_i64",
                "-o",
                tmpdir / "fifo_i64.ll",
            ]
        )
        if subprocess_generate_i32.wait() != 0:
            raise RuntimeError("failed to generate fifo_i32.ll")
        if subprocess_generate_i64.wait() != 0:
            raise RuntimeError("failed to generate fifo_i64.ll")

        with open(args.output, "w") as out:
            with open(tmpdir / "fifo_i32.ll") as i32:
                with open(tmpdir / "fifo_i64.ll") as i64:
                    copy_i32 = False
                    for line_no, (line_i32, line_i64) in enumerate(zip(i32, i64)):
                        if line_i32 == FIRST_COPY_LINE:
                            copy_i32 = True

                        if copy_i32:
                            out.write(line_i32)
                            continue

                        while True:
                            try:
                                type_idx = line_i64.index("long")
                            except ValueError:
                                break
                            else:
                                line_i32 = (
                                    line_i32[:type_idx]
                                    + "{{T}}"
                                    + line_i32[type_idx + len("int") :]
                                )
                                line_i64 = (
                                    line_i64[:type_idx]
                                    + "{{T}}"
                                    + line_i64[type_idx + len("long") :]
                                )

                        assert len(line_i32) == len(line_i64)
                        i = 0
                        line = ""
                        while i < len(line_i32):
                            for pattern_i32, pattern_i64, replacement in REPLACEMENT_MAP:
                                match_i32 = pattern_i32.match(line_i32, i)
                                if match_i32 is None:
                                    continue
                                match_i64 = pattern_i64.match(line_i64, i)
                                if match_i64 is None:
                                    continue
                                if match_i32.groups() != match_i64.groups():
                                    continue

                                line += match_i32.expand(replacement)
                                i = match_i32.end()
                                break
                            else:
                                assert line_i32[i] == line_i64[i], (
                                    "No replacement found "
                                    f"on line {line_no + 1} "
                                    f"({line_i32!r} vs. {line_i64!r})"
                                )
                                line += line_i32[i]
                                i += 1
                        out.write(line)


if __name__ == "__main__":
    main()
