###############################################################################
##                                                                           ##
##       DXF points with automatic level reading to contour converter        ##
##       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~        ##
##                             Author: erikoui                               ##
##                              License: none                                ##
##                                                                           ##
###############################################################################

import argparse
import ezdxf
import os
import math
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from scipy.interpolate import griddata


def euclidean_distance(p, q):
    return math.sqrt(sum([(p[i] - q[i]) ** 2 for i in range(2)]))

def print_if_verbose(stuff):
    if(args.verbose):
        print(stuff)

if(__name__=="__main__"):
    # Create an argument parser
    parser = argparse.ArgumentParser( prog='level_to_contour',
                    description="""
Adds to a dxf file with POINTs and MTEXTs the contours. 
To make such a dxf file, use the acad.dwt template, insert your plot outline 
and then use PDMODE command to set the point rendering mode to 2. Use the 
POINT command to place a point and then use MTEXT to add the automatic level 
reading next to the point. You can add notes on the second line of the MTEXT 
if you want, the program will only consider the first line as a value. Repeat 
for all readings. Save the file as 2004 dxf.
""")
    parser.add_argument('input_file', type=str,help='input file name (required)')
    parser.add_argument('-z', '--zero', type=float, action='store', default=0,help='level reading at your zero point')
    parser.add_argument('-o', '--output_file', type=str,help='output file name')
    parser.add_argument('-s', '--show_3d', action='store_true', default=False,help='Show a 3d model of the interpolation')
    parser.add_argument('-c', '--export_csv', action='store_true', default=False,help='Export a csv as well')
    parser.add_argument('--csv_only', action='store_true', default=False,help='Export only the csv')
    parser.add_argument('-d', '--contour_z_distance', type=float, default=0.5,help='contour z distance')
    parser.add_argument('-r', '--resolution', type=int, default=50,help='subdivisions of interpolation grid')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,help='verbose')
    args = parser.parse_args()
    print('\n\n')
    print('             ▄▄▌   ▄▄▄ .   ▌ ▐·  ▄▄▌   ▄▄▄ .  ▄▄▄    ')
    print('             ██•   ▀▄.▀·  ▪█·█▌  ██•   ▀▄.▀·  ▀▄ █·  ')
    print('             ██▪   ▐▀▀▪▄  ▐█▐█•  ██▪   ▐▀▀▪▄  ▐▀▀▄   ')
    print('             ▐█▌▐▌ ▐█▄▄▌   ███   ▐█▌▐▌ ▐█▄▄▌  ▐█•█▌  ')
    print('              .▀▀▀  ▀▀▀   . ▀    .▀▀▀   ▀▀▀   .▀  ▀  ')  
    print('\n\n')               
    print('[+] Converting points from \033[34m%s\033[0m to contours...'%args.input_file)
    # Load the DXF file
    filename_no_ext=os.path.splitext(os.path.basename(args.input_file))[0]
    doc = ezdxf.readfile(args.input_file)
    print_if_verbose('[+] \033[34m%s\033[0m loaded!'%args.input_file)
    msp = doc.modelspace()
    # Get the points from the DXF file
    points = msp.query('POINT')
    # Extract the coordinates from the points
    coordinates = [(point.dxf.location.x, point.dxf.location.y) for point in points]
    # Get the texts from the DXF file
    mtexts = msp.query('MTEXT')
    # zero point of level measurements
    offset=args.zero
    print_if_verbose('[i] Level reading at zero: %.2f'%offset)
    # Extract the position and text content from the MText entities
    mtext_list = []
    for mtext in mtexts:
        try:
            z_value=float(mtext.plain_text().split('\n')[0])
            mtext_list.append([mtext.dxf.insert.x, mtext.dxf.insert.y, z_value])
        except:
            #ignore values that cannot be converted to float
            print_if_verbose('[!] Skipping MTEXT: %s'%repr(mtext.plain_text()))

    # Combine points and text into x,y,z list
    combined=[]
    for label in mtext_list:
        mind=float('inf')
        nearpoint=[0,0]
        for point in coordinates:
            if(euclidean_distance(point,label[0:2])<mind):
                nearpoint=point
                mind=euclidean_distance(point,label[0:2])
        combined.append([nearpoint[0],nearpoint[1],offset-label[2]])
    print_if_verbose('[i] Converted point list:')
    print_if_verbose(combined)

    # Export to csv
    if(args.export_csv or args.csv_only):
        import csv
        csv_filename=filename_no_ext+'.csv'
        with open(csv_filename, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(combined)
            print('[+] CSV file written to %s'%csv_filename)
    if(args.csv_only):
        exit(0)

    # Generate data for matplotlib
    x = np.array([x[0] for x in combined])
    y = np.array([x[1] for x in combined])
    z = np.array([x[2] for x in combined])

    # Calculate limits
    min_x=min(x)
    max_x=max(x)
    min_y=min(y)
    max_y=max(y)
    min_z=math.floor(min(z))
    max_z=math.ceil(max(z))

    # Define a grid of points to interpolate over
    x_new = np.linspace(min_x, max_x, args.resolution)
    y_new = np.linspace(min_y, max_y, args.resolution)
    X, Y = np.meshgrid(x_new, y_new)

    # Perform the interpolation
    Z = griddata((x, y), z, (X, Y), method='linear')

    # Generate contour lines
    contour_levels = np.arange(min_z,max_z,args.contour_z_distance)
    print_if_verbose('[i] Generated %d contour lines:'%len(contour_levels))
    print_if_verbose(contour_levels)
    contour_set = plt.contour(X, Y, Z, levels=contour_levels)

    # Add contours to the file
    color_index=10
    for i,contourr in enumerate(contour_set.collections):
        if(len(contourr.get_paths())==0):
            continue

        for point_set in contourr.get_paths():
            # Create contour pline
            pline = msp.add_polyline2d(point_set.vertices)
            pline.update_dxf_attribs({'color':color_index})

            # Add z height label to the polyline every (resolution/2) points
            for count,coords in enumerate(point_set.vertices):
                if(count%(args.resolution//2)==0):
                    text = '%.2f'%contour_set.levels[i]
                    mtext = msp.add_mtext(text, dxfattribs={
                        'char_height': 0.3,
                        'color': color_index,
                        'layer': 'CONTOURHEIGHTS'
                    })
                    mtext.set_location(tuple(coords))

        color_index=(color_index+10)%255
        # Add labels with the actual 'sealevel' height 
        for point in combined:
            text = '%.2f'%point[2]
            mtext = msp.add_mtext(text, dxfattribs={
                'char_height': 0.3,
                'layer': 'POINTHEIGHTS'
            })
            mtext.set_location((point[0]+0.2,point[1]-0.2))

    # Save the DXF file
    output_filename=filename_no_ext+'_with_contours.dxf'
    if(args.output_file):
        output_filename=args.output_file
    if(os.path.isfile(output_filename)):
        response = input("[?] File already exists, do you want to overwrite? (y/n): ")
        if response != "y":
            print('[-] Not overwriting the file and exiting.')
            exit(0)
    doc.saveas(output_filename)
    print('[+] Saved output to \033[34m%s\033[0m'%output_filename)
    print('[+] Done!')

    if(args.show_3d):
        # Plot the original data and the interpolated surface
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(x, y, z, c='r', marker='o')
        ax.plot_surface(X, Y, Z, cmap='viridis')
        cset = ax.contour(X, Y, Z, zdir='z', offset=-5, cmap='coolwarm',levels=contour_levels)
        plt.axis('equal')
        plt.show()
