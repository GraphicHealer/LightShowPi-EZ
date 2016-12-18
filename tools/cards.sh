#!/bin/bash
x=`aplay -L | grep sysdefault`
echo ${x}
