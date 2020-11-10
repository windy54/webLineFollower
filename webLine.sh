#!/bin/bash

LD_PRELOAD=/usr/lib/arm-linux-gnueabihf/libatomic.so.1 python3 webLineFollower.py --ip 0.0.0.0 --port 8000
