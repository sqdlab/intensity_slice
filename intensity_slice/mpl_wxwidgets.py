'''
Created on 18/06/2013

@author: Matthias Baur
'''
import numpy as np
import os
import wx
from matplotlib.backend_bases import LocationEvent

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

class CursorEvent(LocationEvent):
    '''
    A motion event triggered when the cursor changed its position.
    
    In addition to the :class:`Event` attributes, the following
    event attributes are defined:
    
    id: Integer
        The id of the cursor that sent the event.
    cursor: Cursor
        A reference to the cursor that triggered the event

    '''
    def __init__(self, name, cursor, x, y, id_, **kwargs):
        LocationEvent.__init__(self, name, cursor.ax.figure.canvas, x, y, **kwargs)
        self.id = id_
        self.cursor = cursor

# TODO: Add a circle or something else in the center of the cursor, to make it
# easier to distinguish multiple cursors
class Cursor(object):
    '''
    An interactive Cursor for matplotlib plots in a wxwidgets application,
    defined by a horizontal and vertical line span across both axis.
    
    Each line can independently be picked and moved using the mouse,
    by pressing the left mouse button near one of the lines, and moving
    the mouse while keeping the button pressed. The Cursor is released 
    by releasing the mouse button.
    
    If the left button is pressed near the crossing of both Cursor lines, 
    both lines are picked and can be moved simultaneously.
    
    When the mouse is in a pickable position, the mouse cursor changes its icon,
    depending on which line(s) can be picked.

    '''
    # Only one Cursor can be animated at a time. The first cursor that can claim
    # a press event, grabs this lock by setting it to "self". All the other cursors
    # ignore an event that has already been locked.
    
    # The locking applies even before the user pressed the left mouse button.
    # If a cursor decides that the mouse position is within the "pick" distance
    # it grabs the lock and sets the mouse cursor style to indicate the action
    # that would occur after a press event. If another cursor has already grabbed
    # the lock then there will be no attempt to modify the mouse indicator even
    # if it is within range. The upshot is that the user can select the desired
    # cursor by approaching the location along a path that favours that particular
    # cursor. When the left button is clicked, the appropriate ownership is already
    # established, the mouse cursor is already set and movement parameter is
    # already initialised.
    
    lock = None
       
    def __init__(self, id_, axes, **lineprops):
        '''
        Add a new cursor to a matplotlib.Axes.
        
        Paramters:
            id_: Integer
                The id of the Cursor.
            axes: matplotlib.Axes
                The Axes on which the Cursor should be drawn.
            lineprops: Dictionary
                Dictionary of the line properties of the cursor to customize
                its appearance.

        '''
        self.id = id_
        
        self.ax = axes        
        self.canvas = axes.figure.canvas
        
        self.wxparent = self.canvas.GetParent()
        #self.canvas = self.wxparent.canvas
        
        self.background = None
        self.pickradius = 10 # pixels
        self.connected = False
        self.move_direction = None
        
        # create cursor lines
        center = np.mean(axes.get_xlim())
        lineprops["animated"] = False
        lineprops["picker"] = self.line_picker 
        lineprops["zorder"] = 30     # this does not appear to help 
        self.vline = axes.axvline(x=center, **lineprops)
        self.hline = axes.axhline(y=center, **lineprops)
        self.position = (center, center)
        self.start_position = self.position
        
        self.connect()
        
        self.pressed_flag = False
        
        # preload these cursors only once, rather than repeatedly
        
        self.xyCursor = wx.Cursor(
                os.path.join(MODULE_DIR, 'icons', 'cross.cur'), 
                wx.BITMAP_TYPE_CUR )

        self.yCursor = wx.Cursor(
                os.path.join(MODULE_DIR, 'icons', 'vsplit.cur'), 
                wx.BITMAP_TYPE_CUR )
        
        self.xCursor = wx.Cursor(
                os.path.join(MODULE_DIR, 'icons', 'hsplit.cur'), 
                wx.BITMAP_TYPE_CUR )
        
        
    def connect(self):
        '''
        Connect mouse motion and button press events to cursor
        to make cursor interactive.
        '''
        if not self.connected:
            self.cidonmove = self.canvas.mpl_connect('motion_notify_event', self.on_move)
            self.cidpress = self.canvas.mpl_connect('button_press_event', self.on_press)
            self.cidrelease = self.canvas.mpl_connect('button_release_event', self.on_release)
            
            self.connected = True
        
    def disconnect(self):
        '''
        Disconnect mouse motion and button press events from the
        cursor to turn off interactivity.
        '''
        if self.connected:
            self.canvas.mpl_disconnect(self.cidonmove)
            self.canvas.mpl_disconnect(self.cidpress)
            self.canvas.mpl_disconnect(self.cidrelease)
            
            self.connected = False
    
    def on_press(self, event):
        '''The press mouse button callback.'''
                    
        # If the user has clicked outside the cursor axes
        # there is nothing to handle
        
        # If the press event was NOT the left button, there is nothing more
        # to handle
        
        # The *only* cursor that is allowed to process this event, is the
        # one which was responsible for setting the mouse cursor. Also,
        # we know that we're ready to move, bcause it was established in
        # the mouse cursor indication (hover) stage
        
        if ((event.inaxes is self.ax)
            and ( event.button == 1)
            and (Cursor.lock is self)):

            # alter the behaviour of the move processing from mouse
            # cursor management to constrained movement of the
            # custom cross hair cursor.
            
            self.pressed_flag = True
            
            # grab a copy of the starting position in case we want to put it back
            self.start_position = self.position
                        
            # prepare the image structures for fast move events
            self.set_animated()

    def set_animated(self):
        '''Make the cursor animated.'''
        
        # draw everything but *this* cursor
        self.hline.set_animated(True)
        self.vline.set_animated(True)        
        
#         self.center_point.set_animated(True)
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
                
        # redraw cursor
        self.ax.draw_artist(self.hline)
        self.ax.draw_artist(self.vline)
        
        # blit just the redrawn area
        self.canvas.blit(self.ax.bbox)
        
    def unset_animated(self):
        '''Remove the animation state from the cursor.'''
        
        self.hline.set_animated(False)
        self.vline.set_animated(False)
#         self.center_point.set_animated(False)
        self.background = None
        
        self.canvas.draw()
        self.ax.draw_artist(self.vline)
        self.ax.draw_artist(self.hline)        
        self._update()
        
    def near_cursor_cross(self, distance):
        '''
        Return True if the mouse is near the crossing point of the two
        cursor lines. Return False otherwise.
        
        distance: tuple (deltax, deltay)
            The L2 distance between the mouse and the cursor crossing point.

        '''
        dx = distance[0]
        dy = distance[1]
        radius_sq = dx*dx + dy*dy
        
        if radius_sq > self.pickradius*self.pickradius:
            return False
        else:
            return True
        
    def get_mouse_distance(self, event):
        '''
        Return the (positive) distance between the mouse position 
        while the event was generated and the cursor crossing point.
    
        Return: tuple (valid, [deltax, deltay])
        

        '''
        event_position = (event.xdata, event.ydata)
        
        if (event.xdata is None) or (event.ydata is None):
            valid = False
            xdistance = 0
            ydistance = 0
        
        else:
            
            trans_axes = self.vline.axes.transData
            # Get the positions in the figure coordinates
            # transAxes to get axes coordinates does not work, is there some bug?
            # Tested with matplotlib version 1.1.1
            positions = [self.vline.get_xdata(), self.hline.get_ydata(),
                         event_position]
            positions_ax_coord = [trans_axes.transform(pos) for pos in positions]
        
            valid = True
            xdistance = positions_ax_coord[0][0] - positions_ax_coord[2][0]
            ydistance = positions_ax_coord[1][1] - positions_ax_coord[2][1]
        
        return (valid, [xdistance, ydistance])

    def near_horizontal_line(self, distance):
        """
        Return True if the mouse is near the horizontal line
        of the cursor. False otherwise.
        
        distance: tuple (deltax, deltay)
            The distance between the mouse and the cursor crossing point.

        """
        if abs(distance[1]) < self.pickradius:
            return True
        else:
            return False
    
    def near_vertical_line(self, distance):
        """
        Return True if the mouse is near the vertical line
        of the cursor. False otherwise.
        
        distance: tuple (deltax, deltay)
            The distance between the mouse and the cursor crossing point.

        """
        if abs(distance[0]) < self.pickradius:
            return True
        else:
            return False
        
    def on_release(self, event):
        '''The release mouse button callback'''
        
        # The release event is always followed by a move event. This appears to
        # be built in to the wxWidgets system
        
        # Any cursor only deals with release events from the left button

        # If this cursor has held the lock, then it needs to clean up now
        # All other cursors do nothing. Note that the mouse cursor indiction
        # does not change, because the mouse location is still within picking
        # distance.
        # If we had to previously fake a release event when the mouse left the
        # plot region, the pressed flag will be false, and we won't repeat the
        # action
        
        if ((event.button == 1) and (Cursor.lock == self) and self.pressed_flag):
            self.unset_animated()
            self.pressed_flag = False        
        
    
    def on_move(self, event):
        '''
        The mouse motion notify event callback.
        
        If mouse button was pressed near the cursor and cursor
        is not locked, move the cursor when moving the mouse. 
        If mouse button was not pressed, change the mouse cursor
        if it is near the cursor.

        '''

        # if this move event is outside our plot region

        if (event.inaxes != self.ax):
            
            # If we had control of the cursor previously, but this move event took us
            # outside our plot region, we revert to the standard cursor, and fake a
            # release event            

            if (Cursor.lock is self):

                # We've moved outside the plot region, so revert to the
                # standard cursor
            
                self.canvas.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
                Cursor.lock = None
                self.pressed_flag = False
                self.move_direction = None

                # Fake a release event
                # and put the cursor back to where we picked it up
                
                self.position = self.start_position
                self.set_position(self.position[0], self.position[1])              
                self.unset_animated()        

                # but in any case, if the event is outside, we have an early exit
                
            return
        
        if ((Cursor.lock is None) or (Cursor.lock is self)):
            # if no other cursor has already grabbed the lock
        
            if self.pressed_flag:
                         
                # The user has pressed the left mouse button, and this cursor
                # grabbed the lock. The wx cursor has already been set and all
                # we need here is to constrain movement according to the
                # movement_direction set previously.
                        
                ### I don't think we can have a lock with no move direction set
                
                # Set the position of the cross hair cursor depending on whether we'd
                # selected either one or both lines.
        
                if self.move_direction == "XY":
                    self.position = (event.xdata, event.ydata)
                elif self.move_direction == "X":
                    self.position = (event.xdata, self.position[1])
                elif self.move_direction == "Y":
                    self.position = (self.position[0], event.ydata)
                    
                # pass this to the hline and vline objects
                self.set_position(self.position[0], self.position[1])
    
            # If no cursor has already set the mouse cursor, then this
            # cursor is allowed to test the distance conditions.
            
            else:
                
                # We may try to own the cursor, but we're still exploring what to do with it
                 
                (valid, distance) = self.get_mouse_distance(event)
                
                if valid:
                    
                    if self.near_cursor_cross(distance):
                                
                        Cursor.lock = self     
        
                        if self.move_direction != "XY":
                            self.move_direction = "XY"
                            self.canvas.SetCursor(self.xyCursor)
                            
                    elif self.near_horizontal_line(distance):
                        Cursor.lock = self
        
                        if self.move_direction != "Y":
                            self.move_direction = "Y"
                            self.canvas.SetCursor(self.yCursor)
        
                    elif self.near_vertical_line(distance):
                        Cursor.lock = self
        
                        if self.move_direction != "X":
                            self.move_direction = "X"
                            self.canvas.SetCursor(self.xCursor)
                                
                    else:
                        # We're outside the pick distance. Release the lock and let another
                        # cursor try to grab it
                        Cursor.lock = None
                        if self.move_direction != None:
                            self.move_direction = None
                            self.canvas.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))      
            
        # else some other cursor is already in control
        
        # and then 
        
        self._update()
        self.cursor_event()        
    
    def set_position(self, x, y):
        '''Set the position of the cursor to the point (x, y)'''
        self.vline.set_xdata([x, x])
        self.hline.set_ydata([y, y])
#         self.center_point.center = (x, y)
        self._update()
        
        self.cursor_event()
        
    def recenter(self):
        '''Move the cursor to the center of the current view.'''
        self.set_animated()
        center = (np.mean(self.ax.get_xlim()),
                  np.mean(self.ax.get_ylim()))
        self.set_position(*center)
        self.unset_animated()
        
    def cursor_event(self):
        '''
        Send a cursor motion event. Connect to this event using:
        
            canvas.mpl_connect('cursor_motion_event', handler)

        '''
        s = 'cursor_motion_event'
        xy = self.ax.transData.transform(self.position)
        cursorevent = CursorEvent(s, self, xy[0], xy[1], self.id)
        self.canvas.callbacks.process(s, cursorevent)
    
    def _update(self):
        if self.background is not None:
            self.canvas.restore_region(self.background)
        
        #MIJ This can probably be faster, because currently we draw to a big rectangle
        # and so we blit a lot of emptiness to the screen. Two independent sources,
        # one for each line should require far less data movement but more overhead,
        # so it may or may not be faster. But this is not the highest priority to fix
        
        self.ax.draw_artist(self.vline)
        self.ax.draw_artist(self.hline)
        
        #blit from self.ax.bbox to this canvas
        self.canvas.blit(self.ax.bbox)
        
    # No idea why this thing needs to be defined, but all the events do not 
    # work without.
    def line_picker(self, line, mouseevent):
        return False, dict()
    
    def remove(self):
        '''Remove the cursor'''
        self.__del__()
    
    def __del__(self):
        self.disconnect()
        self.ax.lines.remove(self.hline)
        self.ax.lines.remove(self.vline)