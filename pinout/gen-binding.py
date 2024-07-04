#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pindef
import datetime
import math

def print_header(fp):
    year = datetime.datetime.now().date().strftime("%Y")

    fp.writelines([
        "/* SPDX-License-Identifier: GPL-2.0-only OR BSD-2-Clause */\n",
        "/*\n",
        " * Copyright (C) %s Inochi Amaoto <inochiama@outlook.com>\n" % year,
        " *\n",
        " * This file is generated from vendor pinout definition.\n",
        " */\n",
        "\n"
    ])

def print_include_guard_start(fp, chipname: str):
    fp.writelines([
        "#ifndef _DT_BINDINGS_PINCTRL_%s_H\n" % chipname.upper(),
        "#define _DT_BINDINGS_PINCTRL_%s_H\n" % chipname.upper(),
        "\n"
    ])

def print_included(fp):
    fp.writelines([
        "#include <dt-bindings/pinctrl/pinctrl-cv18xx.h>\n",
        "\n"
    ])

def print_include_guard_end(fp, chipname: str):
    fp.writelines([
        "\n"
        "#endif /* _DT_BINDINGS_PINCTRL_%s_H */\n" % chipname.upper(),
    ])

def print_pins(fp, pins: dict):
    maxlength = max([len(pin["name"]) for id, pin in pins.items()]) + 8 + 4
    if maxlength < 40:
        vpos = 40
    else:
        vpos = maxlength + (8 - (maxlength % 8))

    for id, pin in pins.items():
        nlen = len(pin["name"]) + 8 + 4
        ntabs = int((vpos - nlen + 7) / 8)

        if (isinstance(id, tuple)):
            id = "PINPOS('{}', {})".format(*id)

        fp.write(("#define PIN_{}" + ntabs * "\t" + "{}\n").format(pin["name"], id))


if __name__ == "__main__":
    chipname = sys.argv[1]
    pins = pindef.parse_pins(chipname + "_pindef.csv")

    with open("pinctrl-" + chipname + ".h", "w", encoding="utf-8") as fp:
        print_header(fp)
        print_include_guard_start(fp, chipname)
        print_included(fp)

        if isinstance(list(pins.items())[0][0], tuple):
            fp.write("#define PINPOS(row, col)\t\t\t\\\n\t((((row) - 'A' + 1) << 8) + ((col) - 1))\n")
            fp.write("\n")

        print_pins(fp, pins)

        print_include_guard_end(fp, chipname)


