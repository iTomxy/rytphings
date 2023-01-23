#!/bin/bash

RIME=$HOME/.config/ibus/rime
cp rytphings*.yaml $RIME

# redeploy
# https://github.com/rime/home/wiki/CustomizationGuide#%E9%87%8D%E6%96%B0%E4%BD%88%E7%BD%B2%E7%9A%84%E6%93%8D%E4%BD%9C%E6%96%B9%E6%B3%95
touch ~/.config/ibus/rime/
ibus restart

