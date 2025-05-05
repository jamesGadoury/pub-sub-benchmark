#!/bin/bash

lcm-gen -p ./types/lcm/*
protoc --proto_path=./types/proto/ --python_out=./ ./types/proto/*
