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

# TODO: Automatic sections x y

def euclidean_distance(p, q):
    return math.sqrt(sum([(p[i] - q[i]) ** 2 for i in range(2)]))

def print_if_verbose(stuff):
    if(args.verbose):
        print(stuff)

def my_floor(num,resolution):
    nearest_down=np.floor((num/resolution))*resolution
    return nearest_down.astype(np.int64)

def my_ceil(num,resolution):
    nearest_up=np.ceil((num/resolution))*resolution
    return nearest_up.astype(np.int64)

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
for all readings. Save the file as 2004 dxf. It is recommended to rotate the 
plot such that the sections you want are in the x and y directions.
""")
    parser.add_argument('input_file', type=str,help='input file name (required)')
    parser.add_argument('-z', '--zero', type=float, action='store', default=0,help='level reading at your zero point')
    parser.add_argument('-o', '--output_file', type=str,help='output file name')
    parser.add_argument('-s', '--show_3d', action='store_true', default=False,help='Show a 3d model of the interpolation')
    parser.add_argument('-c', '--export_csv', action='store_true', default=False,help='Export a csv as well')
    parser.add_argument('--csv_only', action='store_true', default=False,help='Export only the csv')
    parser.add_argument('-d', '--contour_z_distance', type=float, default=0.5,help='Contour z distance')
    parser.add_argument('-p', '--pre_calculated_z', action='store_true', default=False,help='Use this if MTEXTS of dxf contain heights instead of readings.')
    parser.add_argument('-r', '--resolution', type=int, default=0.25,help='Interpolation grid distance between points (meters)')
    parser.add_argument('--no-sections',action='store_true', default=False, help='Do not add sections to the output file')
    parser.add_argument('--section_resolution', type=float, default=4,help='Distance between section lines (in meters). This will snap to the interpolation grid')
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

    # ============================= Interpret DXF ======================================
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
        if(args.pre_calculated_z):
            combined.append([nearpoint[0],nearpoint[1],label[2]]-offset)
        else:
            combined.append([nearpoint[0],nearpoint[1],offset-label[2]])
    print_if_verbose('[i] Converted point list:')
    print_if_verbose(combined)

    # ============================= Export CSV ======================================
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

    # ============================= Contours ======================================
    # Generate data for matplotlib
    x = np.array([x[0] for x in combined])
    y = np.array([x[1] for x in combined])
    z = np.array([x[2] for x in combined])

    # Calculate limits
    print_if_verbose("Resolution is "+str(args.resolution))
    min_x=my_floor(min(x),args.resolution)
    max_x=my_ceil(max(x),args.resolution)
    min_y=my_floor(min(y),args.resolution)
    max_y=my_ceil(max(y),args.resolution)
    min_z=math.floor(min(z))
    max_z=math.ceil(max(z))
    print_if_verbose("x,y to x,y:"+str(min_x)+" "+str(min_y)+" "+str(max_x)+ " " + str(max_y))
    
    # Define a grid of points to interpolate over
    x_subdivisions=((max_x-min_x+args.resolution)/args.resolution).astype(np.int64)
    y_subdivisions=((max_y-min_y+args.resolution)/args.resolution).astype(np.int64)
    print_if_verbose("Subdivisions in x:"+str(x_subdivisions))
    print_if_verbose("Subdivisions in y:"+str(y_subdivisions))
    x_new = np.linspace(min_x, max_x, x_subdivisions)
    y_new = np.linspace(min_y, max_y, y_subdivisions)
    X, Y = np.meshgrid(x_new, y_new)

    # Perform the interpolation
    Z = griddata((x, y), z, (X, Y), method='linear')

    # Generate contour lines
    contour_levels = np.arange(min_z,max_z,args.contour_z_distance)
    print_if_verbose('[i] Generated '+str(len(contour_levels))+'contour lines:'+str(contour_levels))
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

            # Add z height label to the polyline every (resolution*200 ish) points
            for count,coords in enumerate(point_set.vertices):
                if(count%(np.floor(args.resolution*200).astype(np.int64))==0):
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

    # ========================= Sections ==============================

    # Set section distance to match the gridlines
    section_dist=my_floor(args.section_resolution,args.resolution)
    # Make list of where sections will be drawn
    sections_x=list(range(min_x,max_x+section_dist,section_dist))
    print_if_verbose("[i] Making sections at x coordinate: "+str(sections_x))
    sections_y=list(range(min_y,max_y+section_dist,section_dist))
    print_if_verbose("[i] Making sections at y coordinate: "+str(sections_y))
    # Find index of points at each x and y coordinate from above
    def generate_section_indices(meshgrid_axis,values):
        sections_indices=[]
        ind=0
        for i,s in enumerate(meshgrid_axis[0]):
            if(s==values[ind]):
                sections_indices.append(i)
                ind+=1
        return sections_indices
    sections_x_indices=generate_section_indices(X,sections_x)
    sections_y_indices=generate_section_indices(Y.T,sections_y)# use transpose of Y s.t. we can enumerate over the first element normally
    print_if_verbose("[i] X section indices:"+str(sections_x_indices))
    print_if_verbose("[i] Y section indices:"+str(sections_y_indices))

    # TODO: make lists of x,y coordinates for each section
    sections={}
    def section_name(type,n):
        if(type=='letter'):
            if n <= 0:
                ...
                #throw exception

            alphabet = "abcdefghijklmnopqrstuvwxyz"
            result = ""

            while n > 0:
                remainder = (n - 1) % 26
                result = alphabet[remainder] + result
                n = (n - 1) // 26 

            return result   
        else:
            return n
    
    # Vertical sections
    section_num=1
    for sex in sections_x_indices:
        # make a list of coordinates from Z, on the index of y=sex
        current_section=[]
        for i in range(0,Y.shape[0]):
            distance=Y[i,0]
            height=Z[i,sex]
            if not np.isnan(height):
                current_section.append([distance,height])
        sections[section_name('letter',section_num)]=current_section

        # Add section icons to main drawing
        anno_art1=msp.add_polyline2d([[X[0,sex],min_y],[X[0,sex],min_y-2],[X[0,sex]+0.5,min_y-2],[X[0,sex]+0.2,min_y-1.8]],dxfattribs={'color':2})
        anno_art2=msp.add_polyline2d([[X[0,sex],max_y],[X[0,sex],max_y+2],[X[0,sex]+0.5,max_y+2],[X[0,sex]+0.2,max_y+1.8]],dxfattribs={'color':2})
        anno_letter1=msp.add_mtext(section_name('letter',section_num), dxfattribs={'char_height': 0.3,'color': 2})
        anno_letter1.set_location(tuple([X[0,sex],min_y]))
        anno_letter2=msp.add_mtext(section_name('letter',section_num), dxfattribs={'char_height': 0.3,'color': 2})
        anno_letter2.set_location(tuple([X[0,sex],max_y]))

        section_num+=1
        
    # Horizontal sections
    section_num=1 
    for sey in sections_y_indices:
        # make a list of coordinates from Z, on the index of x=sey
        current_section=[]
        for i in range(0,X.shape[1]):
            distance=X[0,i]
            height=Z[sey,i]
            if not np.isnan(height):
                current_section.append([distance,height])
                sections[section_name('number',section_num)]=current_section

        # Add section icons to main drawing
        anno_art1=msp.add_polyline2d([[min_x,Y[sey,0]],[min_x-2,Y[sey,0]],[min_x-2,Y[sey,0]+0.5],[min_x-1.8,Y[sey,0]+0.2]],dxfattribs={'color':3})
        anno_art1=msp.add_polyline2d([[max_x,Y[sey,0]],[max_x+2,Y[sey,0]],[max_x+2,Y[sey,0]+0.5],[max_x+1.8,Y[sey,0]+0.2]],dxfattribs={'color':3})
        anno_letter1=msp.add_mtext(section_name('number',section_num), dxfattribs={'char_height': 0.3,'color': 2})
        anno_letter1.set_location(tuple([min_x,Y[sey,0]]))
        anno_letter2=msp.add_mtext(section_name('number',section_num), dxfattribs={'char_height': 0.3,'color': 2})
        anno_letter2.set_location(tuple([max_x,Y[sey,0]]))

        section_num+=1

    # Make pline with these lists at an empty space in the dxf
    # This will be used to set the vertical spacing between sections
    offset=-10
    max_height_difference=np.nanmax(Z)-np.nanmin(Z)
    print_if_verbose("[i] Max height difference in input"+str(max_height_difference))
    for section in sections:
        color_index=np.random.randint(1,255)
        print_if_verbose("[i] Drawing section "+str(section)+"-"+str(section))
        for point in sections[section]:
            point[1]+=offset
        sect_pline = msp.add_polyline2d(sections[section],dxfattribs={'color':color_index})

        # ENHANCEMENT: add dashed line to show where nearest integer height to minimum point is (currently shows 0 point)
        sect_reference=msp.add_polyline2d([[0,offset],[10,offset]],dxfattribs={'color':color_index})
        sect_ref_mtext = msp.add_mtext("%%p0.00", dxfattribs={'char_height': 0.3,'color': color_index})
        sect_ref_mtext.set_location(tuple([0,offset]))

        # ENHANCEMENT: center text under section with its name
        sect_name_mtext=msp.add_mtext("Section "+str(section), dxfattribs={'char_height': 0.3,'color': color_index})
        sect_name_mtext.set_location(tuple([5,offset-1]))

        # Draw the next line more down
        offset-=5+max_height_difference

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
        plt.axis('auto')# should be equal when they implement it
        plt.show()