# -*- coding: utf-8 -*-
"""
Created on Wed Mar 14 09:45:24 2018

@author: Lachlan
"""

import numpy as np

f = open("C:/Users/Lachlan/Google Drive/Courses/2018 SEM1/SCIE3011/intensity_slice/data/TvMode.dat","r")
next = f.readline().split()

# store the initial information about the coordinates and values listed in the first few lines of the file
coordinates = []
values = []

while next[0] == "#":
    if next[1] == "Column":
        colname = f.readline().split()[2]
        coltype = f.readline().split()[2]
        if coltype == "coordinate":
            coordinates.append({'name':colname,'type':coltype})
        elif coltype == "value":
            values.append({'name':colname,'type':coltype})
        else:
            raise ValueError("Inputs should only be of type coordinate or value")            
        
    next = f.readline().split()

# fill in start, end, and size values for each coordinate dimension
file_lines = f.readlines()
numLinesOfData = len(file_lines)
data = [None for n in range(0,numLinesOfData)]

for i in range(0,numLinesOfData):
    file_lines[i] = file_lines[i].split()

for i in range(0, len(coordinates)):
    # NOTE potential precision issues if you evaluate an int as a float
    coordinates[i]['start'] = float(next[i])
    coordinates[i]['end'] = float(file_lines[-1][i])
    n = 0L
    coordinateValues = []
    for j in range(0,numLinesOfData):
        if file_lines[j][i] in coordinateValues:
            pass
        else:
            n+=1
            coordinateValues.append(file_lines[j][i])
    coordinates[i]['size'] = n
    
# return to the start of the file
f.close()
f = open("C:/Users/Lachlan/Google Drive/Courses/2018 SEM1/SCIE3011/intensity_slice/data/TvMode.dat","r")

# how many coordinates will we have for the data? Do we know that it's always going to be 3?
shape = (coordinates[0]['size'], coordinates[1]['size'], coordinates[2]['size'], long(len(coordinates)+len(values)))
shaped_data = np.zeros(shape);

#skip through the first couple of lines
next = f.readline().split()
while next[0] == "#":
    next = f.readline().split()

# populated shaped_data with the data values
for i in range(0,shaped_data.shape[0]):
    for j in range(0,shaped_data.shape[1]):
        for k in range(0,shaped_data.shape[2]):
            shaped_data[i][j][k] = next
            next = f.readline().split()
            
f.close()
