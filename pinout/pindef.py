#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import pprint
import re
import sys
from enum import Enum

FUNC_PATTERN = re.compile(r"(\d) *: *([^ ]+)")

class PIN_IO_TYPE(Enum):
    IO_TYPE_1V8_ONLY = 0
    IO_TYPE_1V8_OR_3V3 = 1
    IO_TYPE_AUDIO = 2
    IO_TYPE_ETH = 3

    def __str__(self):
        return f'{self.name}'

def parse_pin_num(value: str):
    if value.isdigit():
        return int(value)
    return (value[0], int(value[1:]))

def parse_pin_address(value: str):
    return int(value.replace('_', ''), base=0)

def parse_pin_name(value: str):
    value = value.removeprefix("PAD_")

    pos = value.find("__")
    if pos != -1:
        value = value[0:pos]

    return value

def parse_pin_cfg(value: str):
    value = [part.strip() for part in value.split('\n') if len(part.strip()) > 0]

    if (len(value) > 2) or (len(value) == 0):
        pprint.pp(value)
        raise KeyError

    if len(value) == 2:
        return value[0], parse_pin_address(value[1])

    value = value[0].replace(' ', '')

    return value[0:-11], parse_pin_address(value[-11:])

def parse_pin_io_type(value: str):
    if value.find("ETH") != -1:
        return PIN_IO_TYPE.IO_TYPE_ETH
    elif value.find("AUDIO") != -1:
        return PIN_IO_TYPE.IO_TYPE_AUDIO
    elif value.find("18OD33") != -1:
        return PIN_IO_TYPE.IO_TYPE_1V8_OR_3V3
    else:
        return PIN_IO_TYPE.IO_TYPE_1V8_ONLY

def parse_pin_mux(row):
    name, addr = parse_pin_cfg(row['Function_select\n_register'])
    mux = {
        "name": name,
        "address": addr,
        "default": parse_pin_address(row['fmux_\ndefault']),
        "func": {int(iter.group(1)): iter.group(2) for iter in FUNC_PATTERN.finditer(row['Description'].replace('\n', ' '))},
    }
    mux['max'] = max(mux['func'].keys())
    mux['area'], mux['offset'] = pin_addr_area(addr)

    return mux

def pin_addr_area(value: int):
    if value >= 0x03001000 and value < 0x03002000:
        return "SYS", value - 0x03001000
    elif value >= 0x05027000 and value < 0x05028000:
        return "RTC", value - 0x05027000
    else:
        raise KeyError(hex(value))

def parse_pins(filename: str) -> dict[int, dict]:
    NArows = []
    pins = {}

    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['Pin Num'] == "#N/A":
                NArows.append(row)
                continue

            pin = {
                "id": parse_pin_num(row['Pin Num']),
                "name": parse_pin_name(row['Pin Name']),
                "type": parse_pin_io_type(row['IO Type']),
                "power_domain": row['PowerDomain'],
            }

            if row['IO_cfg_register'] != "#N/A":
                name, addr = parse_pin_cfg(row['IO_cfg_register'])
                pin['iocfg'] = {
                    "name": name,
                    "address": addr,
                }
                pin['iocfg']['area'], pin['iocfg']['offset'] = pin_addr_area(addr)

            pin['mux'] = parse_pin_mux(row)

            pins[pin["id"]] = pin

    for row in NArows:
        if len(row['Note']) == 0:
            continue

        key = [id for (id, pin) in pins.items() if row['Note'].find(pin['name']) != -1]
        if len(key) == 0:
            continue
        if len(key) != 1:
            raise KeyError(key)
        key = key[0]

        pins[key]['mux']['sub'] = parse_pin_mux(row)

    return {k: v for k, v in sorted(pins.items())}

if __name__ == "__main__":
    pprint.pp(parse_pins(sys.argv[1]))
