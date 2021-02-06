# -*- coding: utf-8 -*-
"""
Created on Fri Feb  5 17:40:26 2021

@author: Matteo

library for radial profile

https://pypi.org/project/sectorizedradialprofile/
"""

import os
from numba import jit
import datetime
import numpy as np
import matplotlib.pyplot as plt
from scipy import optimize
import cv2
from sectorizedradialprofile.calculate_radial_profile import CalculateRadialProfile


def bhsimple(z, input_folder = 'stack', output_folder = 'corrected',
              angle_ini = -90, angle_fin = 90):
    '''
    Applies a beam hardening correction on a given tif sequence
    Correction is calculated on one given slide only

    --> z             = slice to use for correction
    --> input_folder  = folder where the original tif sequence is stored
    --> output_folder = folder where the corrected tif sequence will be stored
    --> angle_ini     = initial angle for angle range for radial profile
                            angle in degrees: 0 is 12:00 and 90 is 3:00
    --> angle_fin     = final anle for angle range for radial profile (degrees)
    '''

    file_list = []
    for f in os.listdir(input_folder):
        if f.endswith('.tif'):
            file_list.append(f)

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    data_file = input_folder + '/' + file_list[z-1]
    # working_data = cv2.imread(data_file, cv2.IMREAD_GRAYSCALE)
    working_data = cv2.imread(data_file, -1)

    center = {'x0': working_data.shape[0]/2+0.5,
              'y0': working_data.shape[1]/2+0.5}  #pixels

    angle_range = {'from': angle_ini, 'to': angle_fin}  #degrees

    r_profile = CalculateRadialProfile(data=working_data,
                                        center=center, angle_range=angle_range)
    r_profile.calculate()
    profile = r_profile.radial_profile

    limit = int(np.where(profile == profile.max())[0])

    fig1 = plt.figure()
    plt.plot(profile)

    i = profile[:limit]
    r = np.arange(1,len(i)+1,1)

    # Brezier
    A = {'x':r.min(), 'y':i.min()}
    C = {'x':r.max(), 'y':i.max()}

    def funy(w,r,A,C):
        B = {'x':w[3],'y': w[4]}
        h = ((A['x']-B['x'] +
              np.sqrt(r*A['x']-2*r*B['x']+B['x']**2+r*C['x']-A['x']*C['x']))/
              (A['x']-2*B['x']+C['x']))
        y = (((1-h)**2*A['y']*w[0]+2*(1-h)*h*B['y']*w[1]+h**2*C['y']*w[2])/
              ((1-h)**2*w[0]+2*(1-h)*h*w[1]+h**2*w[2]))
        return y

    def offset(w,A,C,r,i):
        y = funy(w,r,A,C)
        return i-y

    wopt = optimize.least_squares(offset, [1,1,1,r.max()*2/3,i.min()],
                                  args = (A,C,r,i), bounds=([0,0,0,0,0],
                                        [np.inf,np.inf,np.inf,np.inf,np.inf]),
                                  verbose=1)

    ref = [i[0:400].mean()]*len(i)
    corrected = i - (funy(wopt.x,r,A,C) - ref)

    fig2 = plt.figure()
    ax21 = fig2.add_subplot(121)
    ax21.plot(r,i,label='original')
    ax21.plot(r,funy(wopt.x,r,A,C),label='fitted with Bezier')
    ax21.legend()

    ax22 = fig2.add_subplot(122)
    ax22.plot(r,i,label='original')
    ax22.plot(r,corrected,label='corrected')
    ax22.plot(r,ref, label='aim')
    ax22.legend()

    fig3 = plt.figure()
    ax31 = fig3.add_subplot(121)
    ax32 = fig3.add_subplot(122)

    x_range = working_data.shape[0]
    y_range = working_data.shape[1]

    new = np.empty(working_data.shape)
    ref_z = np.full(working_data.shape, ref[0])

    @jit
    # @jit(nopython=True, parallel=True) # Switch this on for parallel processing
    def calculate_radii(xrange, yrange, cx, cy):
        r = np.empty(working_data.shape, np.float64)
        for x in range(xrange):
            for y in range(yrange):
                r[x,y] = np.sqrt((x-cx)*(x-cx) + (y-cy)*(y-cy))
        return r

    count = 0
    radii = calculate_radii(x_range, y_range, center['x0'], center['y0'])

    for image in file_list:
        count += 1
        if count % 100 == 0:
            print('Starting slice', count, datetime.datetime.now())
        data_file_z = input_folder + '/' + image
        im_z = cv2.imread(data_file_z, -1)
        mask = radii <= limit
        foo = funy(wopt.x,radii*mask,A,C)
        new = im_z*mask - foo*mask - ref_z*mask

        os.chdir(output_folder)
        new_n = np.float32(new)
        cv2.imwrite(image,new_n)

        os.chdir('..')
        if count == z:
            corrected = new

    ax31.imshow(working_data)
    ax32.imshow(corrected)

    return new

a= bhsimple(20)

