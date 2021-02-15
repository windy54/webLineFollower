#!/bin/bash

LD_PRELOAD=/usr/lib/arm-linux-gnueabihf/libatomic.so.1 python3 upGardenPath.py --ip 0.0.0.0 --port 8000
