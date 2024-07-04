#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pindef
import datetime
import math
from pindef import PIN_IO_TYPE

def print_pins(fp, chipname: str, pins: dict):
    fp.write("static const struct pinctrl_pin_desc %s_pins[] = {\n" % chipname)
    maxlength = max([len(pin["name"]) for id, pin in pins.items()]) + 16 + 8 + 1
    if maxlength < 40:
        vpos = 40
    else:
        vpos = maxlength + (8 - (maxlength % 8))

    for id, pin in pins.items():
        nlen = len(pin["name"]) + 16 + 8 + 1
        ntabs = int((vpos - nlen + 7) / 8)

        fp.write(("\tPINCTRL_PIN(PIN_{0}," + ntabs * "\t" + "\"{0}\"),\n").format(pin["name"]))

    fp.write("};\n")

def cook_pin_area(area: str):
    if area == "SYS":
        return "CV1800_PINCONF_AREA_SYS"
    elif area == "RTC":
        return "CV1800_PINCONF_AREA_RTC"
    else:
        return ""

def cook_func_pindata(pin: dict):
    lines = [
        "CV1800_FUNC_PIN({}, {},".format("PIN_" + pin["name"], "\"" + pin["pd"] + "\""),
        "\t\t{},".format(str(pin["type"])),
        "\t\t{}, 0x{:03x}, {}),".format(cook_pin_area(pin["mux"]["area"]), pin["mux"]["offset"], pin["mux"]["max"]),
    ]

    return "\t" +"\n\t".join(lines) + "\n"

def cook_generate_pindata(pin: dict):
    if not "iocfg" in pin:
        print(pin["name"])

    if "sub" in pin["mux"]:
        lines = [
            "CV1800_GENERATE_PIN_MUX2({}, {},".format("PIN_" + pin["name"], "\"" + pin["pd"] + "\""),
            "\t\t\t {},".format(str(pin["type"])),
            "\t\t\t {}, 0x{:03x}, {},".format(cook_pin_area(pin["mux"]["area"]), pin["mux"]["offset"], pin["mux"]["max"]),
            "\t\t\t {}, 0x{:03x}, {},".format(cook_pin_area(pin["mux"]['sub']["area"]), pin["mux"]['sub']["offset"], pin["mux"]['sub']["max"]),
            "\t\t\t {}, 0x{:03x}),".format(cook_pin_area(pin["iocfg"]["area"]), pin["iocfg"]["offset"]),
        ]
    else:
        lines = [
            "CV1800_GENERAL_PIN({}, {},".format("PIN_" + pin["name"], "\"" + pin["pd"] + "\""),
            "\t\t   {},".format(str(pin["type"])),
            "\t\t   {}, 0x{:03x}, {},".format(cook_pin_area(pin["mux"]["area"]), pin["mux"]["offset"], pin["mux"]["max"]),
            "\t\t   {}, 0x{:03x}),".format(cook_pin_area(pin["iocfg"]["area"]), pin["iocfg"]["offset"]),
        ]

    return "\t" +"\n\t".join(lines) + "\n"


def print_pindata(fp, chipname: str, pins: dict):
    fp.write("static const struct cv1800_pin %s_pin_data[ARRAY_SIZE(%s_pins)] = {\n" % (chipname, chipname))

    for id, pin in pins.items():
        ptype = pin["type"]

        if ptype is PIN_IO_TYPE.IO_TYPE_AUDIO or ptype is PIN_IO_TYPE.IO_TYPE_ETH:
            fp.write(cook_func_pindata(pin))
        elif ptype is PIN_IO_TYPE.IO_TYPE_1V8_OR_3V3 or ptype is PIN_IO_TYPE.IO_TYPE_1V8_ONLY:
            fp.write(cook_generate_pindata(pin))
        else:
            raise KeyError(ptype)

    fp.write("};\n")

def print_misc_top(fp, chipname: str):
    year = datetime.datetime.now().date().strftime("%Y")

    value = """// SPDX-License-Identifier: GPL-2.0
/*
 * Sophgo {1} SoC pinctrl driver.
 *
 * Copyright (C) {2} Inochi Amaoto <inochiama@outlook.com>
 *
 * This file is generated from vendor pinout definition.
 */

#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/of.h>

#include <linux/pinctrl/pinctrl.h>
#include <linux/pinctrl/pinmux.h>

#include <dt-bindings/pinctrl/pinctrl-{0}.h>

#include \"pinctrl-cv18xx.h\"
""".format(chipname, chipname.upper(), year)

    fp.write(value)

def print_misc_down(fp, chipname: str):
    value = """static const struct cv1800_pinctrl_data {0}_pindata = {{
\t.pins = {0}_pins,
\t.pindata = {0}_pin_data,
\t.npins = ARRAY_SIZE({0}_pins),
}};

static const struct of_device_id {0}_pinctrl_ids[] = {{
\t{{ .compatible = "sophgo,{0}-pinctrl", .data = &{0}_pindata }},
\t{{ }}
}};
MODULE_DEVICE_TABLE(of, {0}_pinctrl_ids);

static struct platform_driver {0}_pinctrl_driver = {{
\t.probe	= cv1800_pinctrl_probe,
\t.driver	= {{
\t\t.name			= "{0}-pinctrl",
\t\t.suppress_bind_attrs	= true,
\t\t.of_match_table		= {0}_pinctrl_ids,
\t}},
}};
module_platform_driver({0}_pinctrl_driver);

MODULE_DESCRIPTION("Pinctrl driver for the {1} series SoC");
MODULE_LICENSE("GPL");
""".format(chipname, chipname.upper())

    fp.write(value)

if __name__ == "__main__":
    chipname = sys.argv[1]
    pins = pindef.parse_pins(chipname + "_pindef.csv")

    with open("pinctrl-" + chipname + ".c", "w", encoding="utf-8") as fp:
        print_misc_top(fp, chipname)
        fp.write("\n")
        print_pins(fp, chipname, pins)
        fp.write("\n")
        print_pindata(fp, chipname, pins)
        fp.write("\n")
        print_misc_down(fp, chipname)

