#PYTHONPATH=./source
#pythonw custom_lib/intensity_slice_gui.py

import sys
import os
#root, _ = os.path.split(__file__)
#sys.path.append(os.path.join(root, 'source'))

# use pygi instead of pygtk if available
#try:
#    from gi import pygtkcompat
#    pygtkcompat.enable()
#    pygtkcompat.enable_gtk(version='3.0')
#finally:
#    pass

from intensity_slice_gui import App
app = App(False)
#if len(sys.argv)>1:
#	directory, filename = os.path.split(sys.argv[1])
#        app.frame1.directory = directory
#        app.frame1.filename = filename
#	app.frame1.load_data(directory, filename)
app.MainLoop()
