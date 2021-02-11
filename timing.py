#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Feb  7 09:24:34 2021

@author: fqb11104
"""

import datetime
import beamhardening as bh

a = datetime.datetime.now()
bh.simple(5)

print('No parellel took', datetime.datetime.now()-a) #44s every 100 slices
