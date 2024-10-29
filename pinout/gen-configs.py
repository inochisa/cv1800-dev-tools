#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pindef
import datetime
import math
from pindef import PIN_IO_TYPE
from vddio import CV18XX_VDDIO_MAP

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
        "CV1800_FUNC_PIN({}, {},".format("PIN_" + pin["name"], pin["power_domain"]),
        "\t\t{},".format(str(pin["type"])),
        "\t\t{}, 0x{:03x}, {}),".format(cook_pin_area(pin["mux"]["area"]), pin["mux"]["offset"], pin["mux"]["max"]),
    ]

    return "\t" +"\n\t".join(lines) + "\n"

def cook_generate_pindata(pin: dict):
    if not "iocfg" in pin:
        print(pin["name"])

    if "sub" in pin["mux"]:
        lines = [
            "CV1800_GENERATE_PIN_MUX2({}, {},".format("PIN_" + pin["name"], pin["power_domain"]),
            "\t\t\t {},".format(str(pin["type"])),
            "\t\t\t {}, 0x{:03x}, {},".format(cook_pin_area(pin["mux"]["area"]), pin["mux"]["offset"], pin["mux"]["max"]),
            "\t\t\t {}, 0x{:03x}, {},".format(cook_pin_area(pin["mux"]['sub']["area"]), pin["mux"]['sub']["offset"], pin["mux"]['sub']["max"]),
            "\t\t\t {}, 0x{:03x}),".format(cook_pin_area(pin["iocfg"]["area"]), pin["iocfg"]["offset"]),
        ]
    else:
        lines = [
            "CV1800_GENERAL_PIN({}, {},".format("PIN_" + pin["name"], pin["power_domain"]),
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
\t.pins\t\t= {0}_pins,
\t.pindata\t= {0}_pin_data,
\t.pdnames\t= {0}_power_domain_desc,
\t.vddio_ops\t= &{0}_vddio_cfg_ops,
\t.npins\t\t= ARRAY_SIZE({0}_pins),
\t.npd\t\t= ARRAY_SIZE({0}_power_domain_desc),
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

def pin_to_power_domains(pins: dict):
    return sorted(set([pin["power_domain"] for pin in pins.values()]))

def print_power_domain_mapping(fp, chipname: str, pin: dict):
    mapping = pin_to_power_domains(pins)
    maxlength = max([len(domain) for domain in mapping]) + 8
    if maxlength < 32:
        vpos = 32
    else:
        vpos = maxlength + (8 - (maxlength % 8))

    fp.write("enum {}_POWER_DOMAIN {{\n".format(chipname.upper()))
    for id, name in enumerate(mapping):
        nlen = len(name) + 8
        ntabs = int((vpos - nlen + 7) / 8)
        fp.write(("\t{}" + ntabs * "\t" + "= {}{}\n").format(name, id, "" if id + 1 == len(mapping) else ","))
    fp.write("};\n")

    fp.write("\n")

    maxlength = maxlength + 2
    if maxlength < 32:
        vpos = 32
    else:
        vpos = maxlength + (8 - (maxlength % 8))
    fp.write("static const char *const {}_power_domain_desc[] = {{\n".format(chipname))
    for name in mapping:
        nlen = len(name) + 8 + 2
        ntabs = int((vpos - nlen + 7) / 8)
        fp.write(("\t[{0}]" + ntabs * "\t" + "= \"{0}\",\n").format(name))
    fp.write("};\n")


def print_vddio(fp, chipname):
    def get_vddio_map(type, vddio):
        return [map for map in CV18XX_VDDIO_MAP if map["type"] == type and map["VDDIO"] == vddio][0]
    def get_vddio_schmit(value):
        return value[0][1] if len(value) == 6 else 0
    def print_vddio_pull(fp, chipname, state, *value):
        fp.write("""static int {0}_get_pull_{1}(struct cv1800_pin *pin, const u32 *psmap)
{{
	u32 pstate = psmap[pin->power_domain];
	enum cv1800_pin_io_type type = cv1800_pin_io_type(pin);

	if (type == IO_TYPE_1V8_ONLY)
		return {2};

	if (type == IO_TYPE_1V8_OR_3V3) {{
		if (pstate == PIN_POWER_STATE_1V8)
			return {3};
		if (pstate == PIN_POWER_STATE_3V3)
			return {4};

		return -EINVAL;
	}}

	return -ENOTSUPP;
}}
""".format(chipname, state, *value))

    def print_vddio_map(fp, chipname, mtype, name, value):
        fp.write("static const u32 {0}_{1}_{2}_map[] = {{\n".format(chipname, name, mtype))
        fp.write("\t" + ",\n\t".join(value) + "\n")
        fp.write("};\n")

    def print_vddio_oc_func(fp, chipname):
        head = "static int {0}_get_oc_map(".format(chipname)
        tabs = int(len(head) / 8)
        spaces = len(head) % 8
        fp.write(head + "struct cv1800_pin *pin, const u32 *psmap,\n")
        fp.write("\t" * tabs + " " * spaces + "const u32 **map)\n")
        fp.write("""{{
	enum cv1800_pin_io_type type = cv1800_pin_io_type(pin);
	u32 pstate = psmap[pin->power_domain];

	if (type == IO_TYPE_1V8_ONLY) {{
		*map = {0}_1v8_oc_map;
		return ARRAY_SIZE({0}_1v8_oc_map);
	}}

	if (type == IO_TYPE_1V8_OR_3V3) {{
		if (pstate == PIN_POWER_STATE_1V8) {{
			*map = {0}_18od33_1v8_oc_map;
			return ARRAY_SIZE({0}_18od33_1v8_oc_map);
		}} else if (pstate == PIN_POWER_STATE_3V3) {{
			*map = {0}_18od33_3v3_oc_map;
			return ARRAY_SIZE({0}_18od33_3v3_oc_map);
		}}
	}}

	if (type == IO_TYPE_ETH) {{
		*map = {0}_eth_oc_map;
		return ARRAY_SIZE({0}_eth_oc_map);
	}}

	return -ENOTSUPP;
}}
""".format(chipname))

    def print_vddio_schmitt_func(fp, chipname):
        head = "static int {0}_get_schmitt_map(".format(chipname)
        tabs = int(len(head) / 8)
        spaces = len(head) % 8
        fp.write(head + "struct cv1800_pin *pin, const u32 *psmap,\n")
        fp.write("\t" * tabs + " " * spaces + "const u32 **map)\n")
        fp.write("""{{
	enum cv1800_pin_io_type type = cv1800_pin_io_type(pin);
	u32 pstate = psmap[pin->power_domain];

	if (type == IO_TYPE_1V8_ONLY) {{
		*map = {0}_1v8_schmitt_map;
		return ARRAY_SIZE({0}_1v8_schmitt_map);
	}}

	if (type == IO_TYPE_1V8_OR_3V3) {{
		if (pstate == PIN_POWER_STATE_1V8) {{
			*map = {0}_18od33_1v8_schmitt_map;
			return ARRAY_SIZE({0}_18od33_1v8_schmitt_map);
		}} else if (pstate == PIN_POWER_STATE_3V3) {{
			*map = {0}_18od33_3v3_schmitt_map;
			return ARRAY_SIZE({0}_18od33_3v3_schmitt_map);
		}}
	}}

	return -ENOTSUPP;
}}
""".format(chipname))

    print_vddio_pull(fp, chipname, "up",
        get_vddio_map(PIN_IO_TYPE.IO_TYPE_1V8_ONLY, 1800)["map"]["pull-up"],
        get_vddio_map(PIN_IO_TYPE.IO_TYPE_1V8_OR_3V3, 1800)["map"]["pull-up"],
        get_vddio_map(PIN_IO_TYPE.IO_TYPE_1V8_OR_3V3, 3300)["map"]["pull-up"],
    )
    fp.write("\n")

    print_vddio_pull(fp, chipname, "down",
        get_vddio_map(PIN_IO_TYPE.IO_TYPE_1V8_ONLY, 1800)["map"]["pull-down"],
        get_vddio_map(PIN_IO_TYPE.IO_TYPE_1V8_OR_3V3, 1800)["map"]["pull-down"],
        get_vddio_map(PIN_IO_TYPE.IO_TYPE_1V8_OR_3V3, 3300)["map"]["pull-down"],
    )
    fp.write("\n")

    print_vddio_map(fp, chipname, "oc", "1v8", [str(value[1]) for value in get_vddio_map(PIN_IO_TYPE.IO_TYPE_1V8_ONLY, 1800)["map"]["output-low"]])
    fp.write("\n")
    print_vddio_map(fp, chipname, "oc", "18od33_1v8", [str(value[1]) for value in get_vddio_map(PIN_IO_TYPE.IO_TYPE_1V8_OR_3V3, 1800)["map"]["output-low"]])
    fp.write("\n")
    print_vddio_map(fp, chipname, "oc", "18od33_3v3", [str(value[1]) for value in get_vddio_map(PIN_IO_TYPE.IO_TYPE_1V8_OR_3V3, 3300)["map"]["output-low"]])
    fp.write("\n")
    print_vddio_map(fp, chipname, "oc", "eth", [str(value[1]) for value in get_vddio_map(PIN_IO_TYPE.IO_TYPE_ETH, 1800)["map"]["output-low"]])
    fp.write("\n")

    print_vddio_oc_func(fp, chipname)
    fp.write("\n")

    print_vddio_map(fp, chipname, "schmitt", "1v8", [str(get_vddio_schmit(value) * 1000) for value in get_vddio_map(PIN_IO_TYPE.IO_TYPE_1V8_ONLY, 1800)["map"]["schmit-trigger"]])
    fp.write("\n")
    print_vddio_map(fp, chipname, "schmitt", "18od33_1v8", [str(get_vddio_schmit(value) * 1000) for value in get_vddio_map(PIN_IO_TYPE.IO_TYPE_1V8_OR_3V3, 1800)["map"]["schmit-trigger"]])
    fp.write("\n")
    print_vddio_map(fp, chipname, "schmitt", "18od33_3v3", [str(get_vddio_schmit(value) * 1000) for value in get_vddio_map(PIN_IO_TYPE.IO_TYPE_1V8_OR_3V3, 3300)["map"]["schmit-trigger"]])
    fp.write("\n")

    print_vddio_schmitt_func(fp,chipname)
    fp.write("\n")
    fp.write("""static const struct cv1800_vddio_cfg_ops {0}_vddio_cfg_ops = {{
	.get_pull_up\t\t= {0}_get_pull_up,
	.get_pull_down\t\t= {0}_get_pull_down,
	.get_oc_map\t\t= {0}_get_oc_map,
	.get_schmitt_map\t= {0}_get_schmitt_map,
}};
""".format(chipname))


if __name__ == "__main__":
    chipname = sys.argv[1]
    pins = pindef.parse_pins(chipname + "_pindef.csv")

    with open("pinctrl-" + chipname + ".c", "w", encoding="utf-8") as fp:
        print_misc_top(fp, chipname)
        fp.write("\n")
        print_power_domain_mapping(fp, chipname, pins)
        fp.write("\n")
        print_vddio(fp, chipname)
        fp.write("\n")
        print_pins(fp, chipname, pins)
        fp.write("\n")
        print_pindata(fp, chipname, pins)
        fp.write("\n")
        print_misc_down(fp, chipname)

