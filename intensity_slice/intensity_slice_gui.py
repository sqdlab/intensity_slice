'''
Created on May 25, 2013

@author: Matthias Baur
'''

# version 150
import wx
import numpy as np
import copy
import os
import types
import plotfunctions as plotf
import re
import inspect
import linecache

import matplotlib
matplotlib.use('WXAgg')

from mpl_wxwidgets import Cursor
from wx.lib.scrolledpanel import ScrolledPanel

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib import gridspec
from matplotlib.ticker import MaxNLocator, FormatStrFormatter
from wxwidgets import DragListCtrl, EVT_DRAGLIST, SliderGroup, Param

# need to get rid of uqtools so this is going to be commented out (actually it seems to be unused) L
#from uqtools import CSVStore
        
# used to look for memory leak
#import gc
#import objgraph

global usage_ref
        
class CoordSliderGroup(SliderGroup):
    def __init__(self, parent, label, param, data, id_):
        selection = [0 for __ in np.shape(data)]
        selection[id_] = slice(None)
        selection[-1] = id_
        self._data_slice = data[selection]
        
        super(CoordSliderGroup, self).__init__(parent, label, param, id_=id_)
    
    def _text_handler(self, event):
        value = float(self.text.GetValue())
        # find data index of the value nearest to `value`
        index = np.argmin(np.abs(self._data_slice - value))
        self._param.set(index)
        event.Skip(True)
    
    def set_knob(self, value):
        self.slider.SetValue(value)
        self.text.SetValue("{0:.6e}".format(self._data_slice[value]))

class CoordSliderPanel(ScrolledPanel):
    def __init__(self, parent, size, **kwargs):
        super(CoordSliderPanel, self).__init__(
            parent, id=wx.ID_ANY, size=size, **kwargs)
        
        self.SetMinSize(size)
        self.SetupScrolling(False, True, 0, 10, False)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        self.sizer = sizer
        self._sliders = []
        
    def add_slider(self, label, param, data, id_=None):
        newslider = CoordSliderGroup(self, label, param, data, id_)
        self._sliders.append(newslider)
        self.sizer.Add(newslider, flag=wx.EXPAND | wx.ALL, border=5)
        self.sizer.Layout()
        self.FitInside()
        self.AdjustScrollbars()
        
        return newslider
        
    def remove_slider(self, id_):
        slider = self._find_slider(id_)
            
        if self.sizer.Remove(slider.sizer):
            self._sliders.remove(slider)
            slider.delete()
            self.sizer.Layout()
            return True
        else:
            return False

    def hide_slider(self, id_):
        slider = self._find_slider(id_)
        if self.sizer.Hide(slider):
            return True
        else:
            return False
        
    def disable_slider(self, id_):
        self.enable_slider(id_, enable=False)
        
    def enable_slider(self, id_, enable=True):
        slider = self._find_slider(id_)
        slider.enable(enable)
        
    def show_slider(self, id_):
        slider = self._find_slider(id_)
        if self.sizer.Show(slider):
            return True
        else:
            return False
            
    def _find_slider(self, id_):
        for slider in self._sliders:
            if slider.id == id_:
                return slider

    def clear(self):
        self.sizer.Clear()
        [slider.delete() for slider in self._sliders]
        self._sliders = []

class MathPanel(wx.Panel):
    def __init__(self, parent, **kwargs):
        super(MathPanel, self).__init__(parent, **kwargs)
        
        self.frame = wx.GetTopLevelParent(self)
        self.data_functions = {}
        
        self.dl_values = DragListCtrl(
            self, style=wx.LC_LIST, size=(150, 80))
        self.dl_coords = DragListCtrl(
            self, style=wx.LC_LIST, size=(150, 80))
        self.dl_coords.Disable()

        # Selection of value to display
        self.st_value = wx.StaticText(self, label='value to display', size=(75,-1))
        self.cb_value = wx.ComboBox(self, style=wx.CB_READONLY)
        self.cb_value.SetMinSize((125,-1))
        self.cb_value.SetMaxSize((200,-1))
        self.st_param = wx.StaticText(self, label='parameter (p)', size=(75,-1))
        self.t_param = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER)
        self.t_param.SetMinSize((75,-1))
        self.t_param.SetValue("0")
        self.button_reload = wx.Button(self, wx.ID_ANY, label="Reload Functions")
        
        self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        
        self.cb_value.Bind(wx.EVT_COMBOBOX, self.on_cb_value)
        self.dl_values.Bind(EVT_DRAGLIST, self.droplist_handler)
        self.t_param.Bind(wx.EVT_TEXT_ENTER, self.on_text_param)
        self.button_reload.Bind(wx.EVT_BUTTON, self.on_reload)
        
        self._do_layout()
        
    def _do_layout(self):
        sizer_v = wx.BoxSizer(wx.VERTICAL)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.dl_values, proportion=1, flag=wx.EXPAND)
        sizer.Add(self.dl_coords, proportion=1, flag=wx.EXPAND)
        
        sizer_value = wx.BoxSizer(wx.HORIZONTAL)
        sizer_value.Add(self.st_value,
                        flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL,
                        border=5)
        sizer_value.Add(self.cb_value, proportion=1,
                        flag=(wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT
                              | wx.EXPAND | wx.TOP | wx.RIGHT | wx.BOTTOM),
                        border=5)
        
        sizer_param = wx.BoxSizer(wx.HORIZONTAL)
        sizer_param.Add(self.st_param, 
                        flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL,
                        border=5)
        sizer_param.Add(self.t_param,
                        flag=(wx.ALIGN_CENTER_VERTICAL
                              | wx.TOP | wx.RIGHT | wx.BOTTOM),
                        border=5)
        
        sizer_v.Add(sizer, flag=wx.EXPAND)
        sizer_v.Add(sizer_value, flag=wx.EXPAND)
        sizer_v.Add(sizer_param, flag=wx.EXPAND)
        sizer_v.Add(self.text,
                    proportion=1,
                    flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
                    border=5)
        sizer_v.Add(self.button_reload)
        
        self.SetSizer(sizer_v)

    def _clear_functions(self):
        # Remove all functions from the the plotf dictionary
        # such that old functions removed from the library do
        # not persist in the scope due to caching.
        for attr in dir(plotf):
            if attr not in ('__name__', '__file__'):
                delattr(plotf, attr)
        
        for __ in self.data_functions:
            last_pos = self.cb_value.GetCount()
            self.cb_value.Delete(last_pos-1)
        self.text.Clear()
        self.data_functions = {}

    def on_reload(self, event):
        # Store previous selection
        selection = self.cb_value.GetStringSelection()
        
        # Reload the module
        self._clear_functions()
        self.load_functions_module()
        
        # Restore previous selection if it still exists
        index = self.cb_value.FindString(selection)
        if index == wx.NOT_FOUND:
            index = 0
        self.cb_value.SetSelection(index)
        self.draw()

    def on_cb_value(self, event):
        self.draw()

    def on_text_param(self, event):
        self.draw()
            
    def draw(self):
        # find the function that corresponds to the selection index
        value = self.cb_value.GetSelection()
        number_of_values = self.cb_value.GetCount()
        number_of_functions = len(self.data_functions)
        
        # draw the value as is saved in the data file
        if value < number_of_values - number_of_functions:
            value_idx = -(number_of_values - number_of_functions - value)
            self.frame.draw(self.frame.x_idx, self.frame.y_idx, value_idx,
                            recenter=False)
        
        # apply the function before drawing
        else:
            name = self.cb_value.GetString(value)
            func = self.data_functions[name]
            self.text.Clear()
           
            # This reloads the definition of the functions. This is required
            # to keep track of changes in the functions defined in the
            # plotfunctions module. However, this does not load new function 
            # definitions! This requires a reload of the module.
            linecache.clearcache()
            funcsource= self._get_src_code(func)
            self.text.WriteText(funcsource)
            values = [self.dl_values.GetItemText(i) for i 
                      in range(self.dl_values.GetItemCount())]
            
            param = float(self.t_param.GetValue())
            newfun = lambda v: func(v[0], v[1], v[2], param)
            self.frame.draw_function(newfun, values, recenter=False)

    def _get_src_code(self, func):
        src_lines = inspect.getsourcelines(func)[0]
        
        # Find all positions that have these two patterns
        pattern = r"\"\"\""
        pattern2 = r"'''"
        pos = []
        pos2 = []
        for idx, line in enumerate(src_lines):
            if re.findall(pattern, line):
                pos.append(idx)
            if re.findall(pattern2, line):
                pos2.append(idx)
        
        # if nothing was found, there was no docstring
        # if ''' was found but no """, only consider the ''' cases
        # if ''' and """ was found, only consider the ones 
        # that were found first
        if not ((pos == []) and (pos2 == [])):
            if pos2:
                if not pos:
                    pos = pos2
                elif pos[0] > pos2[0]:
                    pos = pos2
            else:
                pass
                
            src_no_doc_lines = src_lines[:pos[0]]
            src_no_doc_lines.extend(src_lines[pos[1]+1:])
        else:
            src_no_doc_lines = src_lines
        
        return "".join(src_no_doc_lines)

    def droplist_handler(self, event):
        self.draw()
        
    def load_functions_module(self):
        reload(plotf)
        for attr in dir(plotf):
            func = plotf.__dict__.get(attr)
            if isinstance(func, types.FunctionType):
                name = next(name for name in re.split("\n", func.__doc__)
                            if name != "")
                name = name.strip()
                self.data_functions[name] = func
                
        self.cb_value.AppendItems(sorted(self.data_functions.keys()))

    def prepend_value_items(self, items):
        for i, item in enumerate(items):
            self.cb_value.Insert(item, i)

class RightPanel(wx.Panel):
    def __init__(self, parent=None, frame=None, id_=wx.ID_ANY, **kwargs):
        super(RightPanel, self).__init__(parent, id_, **kwargs)
        
        self.SetBackgroundColour('white')
        
        self.cb_x = wx.ComboBox(self)
        self.st_x = wx.StaticText(self, label='x-axis', style=wx.CB_READONLY)
        self.cb_y = wx.ComboBox(self)
        self.st_y = wx.StaticText(self, label='y-axis', style=wx.CB_READONLY)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Axis Coordinate selection
        grid_sizer = wx.GridBagSizer(0,0)
        grid_sizer.Add(self.st_x, pos=(0,0), 
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.TOP | wx.LEFT, border=5)
        grid_sizer.Add(self.st_y, pos=(1,0), 
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.TOP | wx.LEFT, border=5)
        grid_sizer.Add(self.cb_x, pos=(0,1),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.TOP | wx.RIGHT, border=5)
        grid_sizer.Add(self.cb_y, pos=(1,1),
                  flag=wx.ALIGN_CENTER_VERTICAL | wx.TOP | wx.RIGHT, border=5)

        sizer.Add(grid_sizer)
        self.SetSizerAndFit(sizer)
        
        # Selection of data slice
        self.slider_panel = CoordSliderPanel(
            self, style=wx.BORDER_SIMPLE | wx.VSCROLL,
            size=(150,170) # Space for 4 slider groups
            )
        self.Sizer.Add(self.slider_panel, flag=wx.EXPAND | wx.ALL, border=5)
        
        self.math_panel = MathPanel(self)
        self.Sizer.Add(self.math_panel, proportion=1,
                       flag=wx.EXPAND | wx.ALL, border=5)

class LeftPanel(wx.Panel):
    min_size = (500, 500)
    
    def __init__(self, parent=None, frame=None, id_=1, **kwargs):
        super(LeftPanel, self).__init__(parent, id_, **kwargs)
        
        self.parent = parent
        self.frame = frame
        self.SetMinSize(self.min_size)
#         self.plot_window.draw_demo()
        
        splitter = wx.SplitterWindow(self)
        self.cursor_prop_window = CursorPropertiesWindow(parent=splitter, id=wx.ID_ANY)
        self.plot_window = PlotWindow(parent=splitter, frame=frame)
        
        splitter.SplitHorizontally(self.plot_window,
                                   self.cursor_prop_window)
        splitter.SetMinimumPaneSize(100)
        wx.CallAfter(splitter.SetSashPosition, -100)
        splitter.SetSashGravity(1.0)
        
#         self.toolbar = NavigationToolbar(self.plot_window.canvas)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
#         sizer.Add(self.toolbar, proportion=0, flag=wx.ALIGN_LEFT)
        sizer.Add(splitter, proportion=1, flag=wx.EXPAND)
        self.SetSizer(sizer)

class CursorPositionListCtrl(wx.Panel):
    def __init__(self, *args, **kwargs):
        super(CursorPositionListCtrl, self).__init__(*args, **kwargs)
        
        self.entries = {}
        self.coord_count = 2
        
        sb = wx.StaticBox(self, label=self.Name)
        self.list = wx.ListCtrl(self, id=wx.ID_ANY, style=wx.LC_REPORT)
        self.list.InsertColumn(0, 'Cursors', width=55)
        self.list.InsertColumn(1, 'X', width=65)
        self.list.InsertColumn(2, 'Y', width=65)
        self.list.InsertColumn(3, 'delta X', width=70)
        self.list.InsertColumn(4, 'delta Y', width=70)
        
        sb_boxsizer = wx.StaticBoxSizer(sb, wx.HORIZONTAL)
        sb_boxsizer.Add(self.list, proportion=1, flag=wx.EXPAND)
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sb_boxsizer, proportion=1, flag=wx.EXPAND)
        self.SetSizer(sizer)

    def add(self, name, column_entries):
        item_count = self.list.GetItemCount()
        pos = self.list.InsertStringItem(item_count, name)
        self.entries[name] = [pos, column_entries]
        for column, entry in enumerate(column_entries, 1):
            self.list.SetStringItem(pos, column, "{0:.6e}".format(entry))
        
        self._update_deltas()

    def _update_deltas(self):
        item_count = self.list.GetItemCount()
        if item_count == 1:
            return
        
        name_0 = self.list.GetItemText(0)
        entries_0 = self.entries[name_0][1]
        for item in range(1, item_count):
            for col in range(1 + self.coord_count, 1 + 2*self.coord_count):
                name = self.list.GetItemText(item)
                delta = (self.entries[name][1][col - self.coord_count - 1]
                         - entries_0[col - self.coord_count - 1])
                self.list.SetStringItem(item, col, "{0:.6e}".format(delta))

    def remove(self, name):
        pos = self.entries.pop(name)[0]
        self.list.DeleteItem(pos)

    def update(self, name, column_entries):
        
        pos = self.entries[name][0]
        self.entries[name][1] = column_entries
        for column, entry in enumerate(column_entries, 1):
            self.list.SetStringItem(pos, column, "{0:.6e}".format(entry))
        
        self._update_deltas()

    def clear(self):
        self.list.DeleteAllItems()
        self.entries = {}

class CursorPropertiesWindow(wx.Panel):
    def __init__(self, *args, **kwargs):
        super(CursorPropertiesWindow, self).__init__(*args, **kwargs)

        self.cursor_props = [
            CursorPositionListCtrl(
                parent=self, id=wx.ID_ANY, name='Intensity Plot Cursors'),
            CursorPositionListCtrl(
                parent=self, id=wx.ID_ANY, name='X Plot Cursors'),
            CursorPositionListCtrl(
                parent=self, id=wx.ID_ANY, name='Y Plot Cursors')
            ]
        
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.cursor_props[0], proportion=1,
                  flag=wx.EXPAND | wx.LEFT, border=5)
        sizer.Add(self.cursor_props[1], proportion=1,
                  flag=wx.EXPAND | wx.LEFT, border=5)
        sizer.Add(self.cursor_props[2], proportion=1,
                  flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=5)
        
        self.SetSizer(sizer)
        
class PlotContextMenu(wx.Menu):
    item_titles = [
        "Recenter Cursor",
        "Create Cursor",
        "Delete Cursor"]
    
    check_item_titles = ["Autoscale"]
    
    menu_titles = item_titles + check_item_titles
    
    menu_id_by_title = {}
    
    for title in menu_titles:
        menu_id_by_title[title] = wx.NewId()
    
    def __init__(self, autoscale=True):
        super(PlotContextMenu, self).__init__()
    
        for title in self.item_titles:
            self.Append(self.menu_id_by_title[title], title)
        
        if autoscale:
            for title in reversed(self.check_item_titles):
                id_ = self.menu_id_by_title[title]
                self.PrependCheckItem(id_, title)
                self.Check(id_, True)
    
    def check_item(self, title, check):
        self.Check(self.menu_id_by_title[title], check)

class ReloadDataContextMenu(wx.Menu):
    items = (
        (None, 'Manual'),
        (1000, '1s'),
        (2000, '2s'),
        (3000, '3s'),
        (5000, '5s'),
        (10000, '10s'),
        (15000, '15s'),
        (30000, '30s'),
        (60000, '60s'),
        (120000, '2min'),
        (300000, '5min'),
        (600000, '10min'),
        (900000, '15min'),
        (1800000, '30min'),
        (3600000, '60min')
    )
    # id to delay mapping
    ids = {}
    
    def __init__(self, on_set_delay):
        super(ReloadDataContextMenu, self).__init__()
        for delay, label in self.items:
            id_ = wx.NewId()
            self.ids[id_] = delay
            self.AppendRadioItem(id_, label)
            self.Bind(wx.EVT_MENU, on_set_delay, id=id_)
        
    
class PlotWindow(wx.Panel):
    ## BUG: Re the blinking of the cursor by using animation. The problem is
    ## update_slice_plots(), which redraws the whole canvas, instead of only the 
    ## slice axes. This can only be solved using animations (FuncAnimation)
    colors = ['b', 'r', 'g', 'c', 'm', 'y', 'k']
    
    def __init__(self, parent=None, frame=None, id_=wx.ID_ANY, **kwargs):
        super(PlotWindow, self).__init__(parent, id_, **kwargs)
        
        self.parent = parent
        self.frame = frame
        self.dpi = 70
        self.figure = plt.figure(figsize=(7.0, 7.0), dpi=self.dpi)
        self.figure.patch.set_color('w')
        self.canvas = FigureCanvas(self, wx.ID_ANY, self.figure)
        self.toolbar = NavigationToolbar(self.canvas)
        self.toolbar.Realize()
        
        self.button_reload_data = wx.ToggleButton(
            self, wx.ID_ANY, label="Reload data")
        self.button_reload_data_popup = ReloadDataContextMenu(self._on_reload_data_delay_changed)
        self.timer_reload_data = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_reload_data)
        self.reload_data_delay = None
        
        self.xp_params = {
            "major_formatter": FormatStrFormatter("%.2f")}
        self.yp_params = copy.copy(self.xp_params)
               
        self._init_plots()
        self._init_plot_context_menu()
        
        sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer1.Add(self.toolbar, proportion=0,
                   flag=wx.LEFT | wx.ALIGN_CENTER_VERTICAL, border=0)
        sizer1.Add(self.button_reload_data, proportion=0,
                   flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL, border=5)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sizer1, proportion=0, flag=wx.EXPAND)
        sizer.Add(self.canvas, proportion=1, flag=wx.EXPAND)
        
        self.SetSizer(sizer)
        
        # Cursor list [intensity plot, xplot, yplot]
        self.cursors = [[], [], []]
        self.create_cursor(1, self.intensity_plot, color='black', linewidth=2)
        self.canvas.mpl_connect('cursor_motion_event', self.cursor_handler)
        
        self.data = None
        self.x = None
        self.y = None
        
        self.image = None
        self.x_idx = -1
        self.y_idx = -1
        self.x_slice = None
        self.y_slice = None
        self._autoscale = {}
        self._autoscale[self.x_slice_plot] = (True, True)
        self._autoscale[self.y_slice_plot] = (True, True)
        
        self._bind_events()
        
    def _init_plots(self):
        
        # plt.xkcd(scale=0.5, length=200, randomness=50)
        
        gs = gridspec.GridSpec(2, 2, width_ratios=[3, 1], height_ratios=[3,1])
        self.x_slice_plot = plt.subplot(gs[2])
        self.x_slice_plot.ticklabel_format(
            style='sci', scilimits=(0, 0), useOffset=False, axis='both')

        self.y_slice_plot = plt.subplot(gs[1])
        self.y_slice_plot.ticklabel_format(
            style='sci', scilimits=(0, 0), useOffset=False, axis='both')
        self.y_slice_plot.yaxis.tick_right()
        self.y_slice_plot.yaxis.set_label_position("right") 

        self.y_slice_plot.xaxis.set_major_locator(MaxNLocator(4, prune=None))
        
        self.intensity_plot = plt.subplot(gs[0],
                                          sharex=self.x_slice_plot,
                                          sharey=self.y_slice_plot)
        ###
        self.intensity_plot.set_zorder(1)
        
        # The default configuration of matplotlib sets the _hold parameter to True,
        # which cause the data reload action to leak memory. We override the _hold
        # setting here to prevent this.
        
        self.x_slice_plot._hold = False
        self.y_slice_plot._hold = False
        self.intensity_plot._hold = False
    
    def _init_plot_context_menu(self):
        self._plot_cm = []
        for axes in [self.intensity_plot, self.x_slice_plot, self.y_slice_plot]:
            
            if axes == self.intensity_plot:
                menu = PlotContextMenu(autoscale=False)
            else:
                menu = PlotContextMenu()
                menu.Bind(wx.EVT_MENU, lambda event, inaxes=axes:
                                self._on_autoscale(event, inaxes),
                          id=menu.menu_id_by_title["Autoscale"])
            
            menu.Bind(wx.EVT_MENU,
                      lambda event, inaxes=axes: self.recenter_cursor(event, inaxes),
                      id=menu.menu_id_by_title["Recenter Cursor"])
            menu.Bind(wx.EVT_MENU,
                      lambda event, inaxes=axes: self.on_create_cursor(event, inaxes),
                      id=menu.menu_id_by_title["Create Cursor"])
            menu.Bind(wx.EVT_MENU,
                      lambda event, inaxes=axes: self.on_delete_cursor(event, inaxes),
                      id=menu.menu_id_by_title["Delete Cursor"])
            
            self._plot_cm.append(menu)
    
    def _bind_events(self):
        self.canvas.mpl_connect('motion_notify_event', self.motion_handler)
        self.canvas.mpl_connect('button_press_event', self.right_click_handler)
        
        self.button_reload_data.Bind(wx.EVT_TOGGLEBUTTON, self._on_reload_data_toggled)
        self.button_reload_data.Bind(wx.EVT_CONTEXT_MENU, lambda event: self.PopupMenu(self.button_reload_data_popup))
     
    def _on_reload_data_toggled(self, event):
        if self.reload_data_delay is None:
            # manual reload 
            self._on_reload_data(event)
            self.button_reload_data.SetValue(False)
        else:
            # start/stop timer
            self._reload_data_timer_setup()
    
    def _on_reload_data_delay_changed(self, event):
        delay = self.button_reload_data_popup.ids[event.Id]
        self.reload_data_delay = delay
        self.button_reload_data.SetValue(False if (self.reload_data_delay is None) else True)
        self._reload_data_timer_setup()
    
    def _reload_data_timer_setup(self):
        if (self.reload_data_delay is not None) and self.button_reload_data.GetValue():
            self.timer_reload_data.Start(self.reload_data_delay)
        else:
            self.timer_reload_data.Stop()
    
    def _on_reload_data(self, event):
        main_frame = wx.GetTopLevelParent(self)
        main_frame.reload_data()
        
    def create_cursor(self, id_, axes, **lineprops):
        idx = self._get_axes_index(axes)
        for cursor in self.cursors[idx]:
            if id_ == cursor.id:
                raise ValueError("Cursor id already exists")
                #return
        
        if id_ == 1:
            lineprops["color"] = 'black'
            
        # This is a custom cursor, not a wxWidgets cursor,
        # nor a matplotlib cursor.
        
        cursor = Cursor(id_, axes, **lineprops)
        
        self.cursors[idx].append(cursor)
        self.GrandParent.cursor_prop_window.cursor_props[idx].add(
            'Cursor' + str(id_), cursor.position)
        cursor.recenter()
        self.repaint()

    def delete_cursor(self, axes):
        # Delete the most recently create cursor (ie we pop off the end of the list)
        idx = self._get_axes_index(axes)
        # Do not delete the data cursor to select the data slices
        if idx == 0:
            if len(self.cursors[0]) <= 1:
                return
        
        if self.cursors[idx]:
            cursor = self.cursors[idx].pop()
            self.GrandParent.cursor_prop_window.cursor_props[idx].remove(
                'Cursor' + str(cursor.id))
            cursor.remove()
            self.repaint()
        
    def motion_handler(self, event):
        # This is bound mouse motion events
        # It does not perform redraw.
        
        # If zooming and panning enabled, disable cursor events
        # to not interfere with zooming
        
        ### MIJ This stuff needs to be moved to the toolbar setting processing,
        ### not every little mouse motion event!
        
        if self.toolbar.mode != '':
            for cursors in self.cursors:
                [cursor.disconnect() for cursor in cursors]
        else:
            for cursors in self.cursors:
                [cursor.connect() for cursor in cursors]
        
        # Format and write the position information (or message) for the status bar
        # at the very base of the window
        
        if self.data is None:
            status_bar_text = 'no data'
        elif ((event.inaxes == self.intensity_plot)
            | (event.inaxes == self.x_slice_plot)
            | (event.inaxes == self.y_slice_plot)):
            status_bar_text = 'x = {0:.2e}, y = {1:.2e}'.format(
                event.xdata,event.ydata)
        else:
            return
            
        self.frame.status_bar.SetStatusText(status_bar_text)

    def right_click_handler(self, event):
        if event.button != 3:
            return
        
        axes_list = [self.intensity_plot, self.x_slice_plot, self.y_slice_plot]
        
        try:
            idx = axes_list.index(event.inaxes)
        except ValueError:
            return
        
        self.PopupMenu(self._plot_cm[idx])
    
    def _get_axes_index(self, axes):
        if axes == self.intensity_plot:
            return 0
        elif axes == self.x_slice_plot:
            return 1
        elif axes == self.y_slice_plot:
            return 2
        else:
            return
    
    def _on_autoscale(self, event, inaxes):
        self._autoscale[inaxes] = event.IsChecked()
        self.update_slice_plots(
            self.data[self.y_idx], np.transpose(self.data)[self.x_idx])
    
    def recenter_cursor(self, event, inaxes):
        i = self._get_axes_index(inaxes)
        if i is None:
            return
        
        [cursor.recenter() for cursor in self.cursors[i]]

    def _cursors_recenter(self):
        for cursors in self.cursors:
            [cursor.recenter() for cursor in cursors]

    def on_create_cursor(self, event, inaxes):
        idx = self._get_axes_index(inaxes)
        cursors = self.cursors[idx]
        if not cursors:
            id_ = 1
        else:
            id_ = cursors[-1].id + 1
         
        self.create_cursor(id_, inaxes)

    def on_delete_cursor(self, event, inaxes):
        self.delete_cursor(inaxes)

    def cursor_handler(self, event):
        if event.inaxes == self.intensity_plot:
            if event.id == 1:
                self.data_cursor_handler(event)
                
        idx = self._get_axes_index(event.cursor.ax)
        
        self.GrandParent.cursor_prop_window.cursor_props[idx].update(
            'Cursor' + str(event.id), event.cursor.position)

    def data_cursor_handler(self, event):
        if self.data is None:
            return
        
        pos = event.xdata, event.ydata
        self.x_idx = np.argmin(np.abs(self.x - pos[0]))
        self.y_idx = np.argmin(np.abs(self.y - pos[1]))
        
        self.update_slice_plots(
            self.data[self.y_idx], np.transpose(self.data)[self.x_idx])
        
    def update_slice_plots(self, xdata, ydata):
        self.x_slice.set_ydata(xdata)
        self.y_slice.set_xdata(ydata)
        
        if self._autoscale[self.x_slice_plot]:
            self.x_slice_plot.set_ylim((min(xdata), max(xdata)))
        if self._autoscale[self.y_slice_plot]:
            self.y_slice_plot.set_xlim((min(ydata), max(ydata)))
        
        #MIJ this overdraws the cursors, slowly because we keep redrawing the data over the top
        # and we should only redraw the slices anyway, not the 2D intensity. This has been disabled
        # to remove significant lag. The slices get updated on button release
        
        #self.repaint()
        #self.canvas.draw()
            
    def draw(self, x, y, data, recenter=True):
        
        ###DEBUG
        #print 'draw (1)'
        #objgraph.show_growth(limit=20)
        #print
        ###END            
        
        # The parameter data is retained for the data_cursor_handler
        
        self.data = data
        self.x = x
        self.y = y
        
        # Reset the home, back and forward button on the 
        # Navigation toolbar
        self.toolbar.update()
        
        if data.shape[0] < abs(self.y_idx):
            self.y_idx = -1
        xslice = data[self.y_idx]
        
        if data.shape[1] < abs(self.x_idx):
            self.x_idx = -1
        yslice = np.transpose(data)[self.x_idx]           

        self.x_slice, = self.x_slice_plot.plot(x, xslice)       #horizontal slice below main image
        self.y_slice, = self.y_slice_plot.plot(yslice, y)       #vertical slice to right of main image

        deltas = []
        for coord in [x, y]:
            if len(coord) == 1:
                deltas.append(1)
            else:
                #deltas.append(coord[1] - coord[0])
                deltas.append(np.min(np.diff(coord)))

        px = np.append(x, x[-1]+deltas[0]) - deltas[0]/2.
        py = np.append(y, y[-1]+deltas[1]) - deltas[1]/2.


        self.intensity_plot.pcolormesh(px, py, data, )
        
        #self.intensity_plot.imshow(data, interpolation='none',
                                   #aspect='auto', origin='lower',
                                   #extent=[x[0] - deltas[0]/2.0,
                                           #x[-1] + deltas[0]/2.0,
                                           #y[0] - deltas[1]/2.0,
                                           #y[-1] + deltas[1]/2.0])

        self.intensity_plot.set_xlim(x[0], x[-1])
        self.intensity_plot.set_ylim(y[0], y[-1])

        
        if recenter:
            self._cursors_recenter()
        
        self.figure.tight_layout()
        self.repaint()

        
        ###DEBUG
        #print 'draw (8)'
        #objgraph.show_growth(limit=20)
        #print
        ###END        
        
    def repaint(self):
#        self.figure.tight_layout()
        self.canvas.draw()

class MainFrame(wx.Frame):
    # TODO: Slider step size?
    # TODO: Use PubSub to communicate between different parts of the
    # application
    min_size = (600, 600)

    def __init__(self, parent=None, id_=-1, size=(900, 600),**kwargs):
        self.size = self._size_constraint(size)
        
        super(MainFrame, self).__init__(parent, id_, size=self.size, **kwargs)
        font = wx.SystemSettings_GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(9)
        self.SetMinSize(self.min_size)
        
        self.status_bar = self.CreateStatusBar()
        self.init_menu()
        
        splitter = wx.SplitterWindow(self)
        self.left_panel = LeftPanel(parent=splitter, frame=self)
        self.right_panel = RightPanel(parent=splitter, frame=self)
        
        splitter.SplitVertically(self.left_panel, self.right_panel, -10)
        splitter.SetMinimumPaneSize(300)
        splitter.SetSashGravity(1.0)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(splitter, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
        self.shaped_data = None
        self.coordinates = None
        self.values = None
        self.value_func = None
        
        self.bind_events()
        
        self.x_idx = 0
        self.y_idx = 1
        self.value_idx = -1
        
        # Defines which slices of 2D data should be plotted (selects the
        # index of the coordinates that are not plotted) 
        self.data_selection = []

        # We need a filename holder that we can test before attempting "reload".
        # Otherwise pressing the reload button with having a selected file will
        # crash the application
        self.filename = None
        
    def init_menu(self):
        menu_bar = wx.MenuBar()
        self.init_file_menu(menu_bar)
        self.SetMenuBar(menu_bar)
        
    def init_file_menu(self, menu_bar):
        file_menu = wx.Menu()
        
        m_open = file_menu.Append(wx.ID_OPEN, 'Open File', 'Open File')
        self.Bind(wx.EVT_MENU, self.on_open, m_open)
        file_menu.AppendSeparator()
        
        m_exit = file_menu.Append(wx.ID_EXIT, 'Exit', 'Exit application')
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)
        
        menu_bar.Append(file_menu, '&File')
        
    def bind_events(self):
        self.right_panel.cb_x.Bind(wx.EVT_COMBOBOX, self.on_cb_x)
        self.right_panel.cb_y.Bind(wx.EVT_COMBOBOX, self.on_cb_y)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        
    def on_axis_cb(self, axis_idx, previous_axis_idx, other_axis_idx):
        if axis_idx == previous_axis_idx:
            return
        
        if axis_idx == other_axis_idx:
            self.right_panel.slider_panel.enable_slider(previous_axis_idx)
            return
        elif previous_axis_idx == other_axis_idx:
            self.right_panel.slider_panel.disable_slider(axis_idx)
        else:
            self.right_panel.slider_panel.disable_slider(axis_idx)
            self.right_panel.slider_panel.enable_slider(previous_axis_idx)
        
        if self.value_func is None:
            self.draw(self.x_idx, self.y_idx, self.value_idx)
        else:
            self.draw_function(self.value_func["function"],
                               self.value_func["values"])
        self.right_panel.slider_panel.Layout()

    def on_cb_x(self, event):
        previous_x_idx = self.x_idx
        self.x_idx = event.GetSelection()
        self.on_axis_cb(self.x_idx, previous_x_idx, self.y_idx)

    def on_cb_y(self, event):
        previous_y_idx = self.y_idx
        self.y_idx = event.GetSelection()
        self.on_axis_cb(self.y_idx, previous_y_idx, self.x_idx)
        
    def on_coord_slider(self, event):
        coord_idx = event.GetEventObject().Parent.id
        position = event.GetInt()
        self.data_selection[coord_idx] = position
        if self.value_func is None:
            self.draw(self.x_idx, self.y_idx, self.value_idx)
        else:
            self.draw_function(self.value_func["function"],
                               self.value_func["values"])

    def on_exit(self, event):
        self.Close()
        
    def on_close(self, event):
        self.Destroy()
        wx.GetApp().ExitMainLoop()
        
    def on_open(self, event):
        # TODO: Remove memory leak when opening new files or reloading an existing one                       

        wildcard = ("data files (*.dat)|*.dat"
                    "|*.*|*.*")
        file_dialog = wx.FileDialog(self, "Open file", 
                                    wildcard=wildcard,
                                    style=wx.FD_FILE_MUST_EXIST)
        
        # if user pressed ok button
        
        if file_dialog.ShowModal() == wx.ID_OK:
            self.directory = file_dialog.Directory
            self.filename = file_dialog.Filename          

                    

            self.load_data(self.directory, self.filename)                              

        file_dialog.Destroy()
        
    def load_data(self, directory, file_name):

        file_ = types.StringType(os.path.join(directory, file_name))
        
        f = open(file_,"r")
        next_ = f.readline().split()
        
        # store the initial information about the coordinates and values listed in the first few lines of the file
        coordinates = []
        values = []
        
        while next_[0] == "#":
            if next_[1] == "Column":
                colname = f.readline().split()[2]
                coltype = f.readline().split()[2]
                if coltype == "coordinate":
                    coordinates.append({'name':colname,'type':coltype})
                elif coltype == "value":
                    values.append({'name':colname,'type':coltype})
                else:
                    raise ValueError("Inputs should only be of type coordinate or value")            
                
            next_ = f.readline().split()
            
        if len(coordinates) < 1:
            f.close()
            del coordinates
            del values
            raise RuntimeError('Data with less than 1 coordinate is currently '
                               'not supported')
        
        # fill in start, end, and size values for each coordinate dimension
        file_lines = f.readlines()
        numLinesOfData = len(file_lines)
        
        for i in range(0,numLinesOfData):
            file_lines[i] = file_lines[i].split()
        
        for i in range(0, len(coordinates)):
            # NOTE potential precision issues if you evaluate an int as a float
            coordinates[i]['start'] = float(next_[i])
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
        print(coordinates)
        print(values)
        # return to the start of the file
        # is there a better way to do this?
        f.close()
        f = open(file_,"r")
        
        # create array of arbitrary shape
        size = len(coordinates)+1
        shape = [0]*(size)
        for i in range(0,size-1):
            shape[i]=long(coordinates[i]['size'])
        shape[size-1]=long(len(coordinates)+len(values))
        
        shape = tuple(shape)
        shaped_data = np.zeros(shape);
        
        #skip through the first couple of lines where they talk about columns
        next_ = f.readline().split()
        while next_[0] == "#":
            next_ = f.readline().split()
        
        # populated shaped_data with the data values
        shaped_data.flat=[next_]+file_lines
        print(shaped_data)
                    
        
        self.coordinates = coordinates
        self.shaped_data = shaped_data
        self.values = values
        
        if len(coordinates) == 1:
            self.coordinates.append(dict(type='coordinate', name='None', size=1))
            self.shaped_data.shape = (self.shaped_data.shape[0], 1, self.shaped_data.shape[1])
        
        f.close()
        del coordinates
        del values
        del shaped_data
        del shape
        del next_

        self._set_axis_cb_choices()
        self._set_value_choices()
        self._set_coordinate_choices()
        
        self.data_selection = [0 for __ in self.shaped_data.shape]
        
        if self.value_func is None:
            self.draw(self.x_idx, self.y_idx, self.value_idx, recenter=True)
        else:
            self.draw_function(self.value_func["function"], self.value_func["values"],
                               recenter=True)
            
    def reload_data(self):
        
        ###MIJ this needs to be via a greyed out button
        if self.filename == None:
            return
        
        file_ = types.StringType(os.path.join(self.directory, self.filename))

        mydata = data.Data(file_,name='static')
        self.shaped_data = mydata.get_reshaped_data()
        mydata.close_file()
        del mydata

        if self.value_func is None:
            self.draw(self.x_idx, self.y_idx, self.value_idx, recenter=False)
        else:
            self.draw_function(self.value_func["function"], self.value_func["values"],
                               recenter=False)
                      
    def draw(self, x_idx, y_idx, value, **kwargs):

        # Draw MainFrame object        
        
        self.value_func = None
        
        self.x_idx = x_idx
        self.y_idx = y_idx
        self.value_idx = value
        
        # Draw the left panel within the MainFrame
        
        self.left_panel.plot_window.draw(
            self.get_coordinate(x_idx),
            self.get_coordinate(y_idx),
            self.get_data_slice(value),
            **kwargs
            )         

    def draw_function(self, func, values, **kwargs):
        self.value_idx = None
        
        self.value_func = {"function": func,
                           "values": values
                           }
        value_names = [coord['name'] for coord in self.values]
        value_indices = [value_names.index(value) for value in values]
        
        data_slices = [self.get_data_slice(-len(values) + i)
                       for i in value_indices]
        computed_data = func([data_slices, self.get_coordinate(self.x_idx), self.get_coordinate(self.y_idx)])
        
        self.left_panel.plot_window.draw(
            self.get_coordinate(self.x_idx),
            self.get_coordinate(self.y_idx),
            computed_data,
            **kwargs
            )

    def get_selection(self, axis_idx, value=None):
        selection = copy.copy(self.data_selection)
        if value is None:
            selection[axis_idx] = slice(None)
            selection[-1] = axis_idx
        else:
            for idx in axis_idx:
                selection[idx] = slice(None)
            selection[-1] = value
        
        return selection
    
    def get_coordinate(self, axis):
        selection = self.get_selection(axis)
        return self.shaped_data[selection]

    def get_data_slice(self, value_axis):
        selection = self.get_selection((self.x_idx, self.y_idx), value_axis)
        data_slice = self.shaped_data[selection]
        if self.x_idx < self.y_idx:
            return np.transpose(data_slice)
        else:
            return data_slice

    def _set_axis_cb_choices(self):
                
        x_axis_previous = self.right_panel.cb_x.GetString(
            self.right_panel.cb_x.GetSelection())
        y_axis_previous = self.right_panel.cb_y.GetString(
            self.right_panel.cb_y.GetSelection())
        
        names = [coord['name'] for coord in self.coordinates]
        self.right_panel.cb_x.Clear()
        self.right_panel.cb_y.Clear()
        
        for i, name in enumerate(names):
            self.right_panel.cb_x.Insert(name, i)
            self.right_panel.cb_y.Insert(name, i)
        
        # remember previous selection for x and y axis coordinate
        try:
            self.x_idx = names.index(x_axis_previous)
            x_idx_found = True
        except ValueError:
            x_idx_found = False
            self.x_idx = 0
        
        try:
            self.y_idx = names.index(y_axis_previous)
        except ValueError:
            self.y_idx = 1
        
        # make sure that not the same x and y axis coordinate is selected
        if self.x_idx == self.y_idx:
            if x_idx_found:
                if self.y_idx > 0:
                    self.y_idx -= 1
                else:
                    self.y_idx += 1
            else:
                if self.x_idx > 0:
                    self.x_idx -= 1
                else:
                    self.x_idx += 1
        
        self.right_panel.cb_x.Select(self.x_idx)
        self.right_panel.cb_y.Select(self.y_idx)
        
        coord_indices = range(len(self.coordinates))[2:]
        self._set_coordinate_sliders(coord_indices)

    def _set_value_choices(self):
        
        cb_value = self.right_panel.math_panel.cb_value
        value_previous = cb_value.GetString(cb_value.GetSelection())
        
        names = [coord['name'] for coord in self.values]
        self.right_panel.math_panel.cb_value.Clear()
        self.right_panel.math_panel.dl_values.ClearAll()
        self.right_panel.math_panel.load_functions_module()
        for i, name in enumerate(names):
            self.right_panel.math_panel.cb_value.Insert(name, i)
            self.right_panel.math_panel.dl_values.InsertStringItem(i, name)
        
        value_strings = cb_value.GetStrings()
        try:
            selection = value_strings.index(value_previous)
        except ValueError:
            self.value_idx = -1
            self.value_func = None
            selection = len(names) - 1
        
        self.right_panel.math_panel.cb_value.Select(selection)

    def _set_coordinate_choices(self):
        self.right_panel.math_panel.dl_coords.ClearAll()
        for i, coord in enumerate(self.coordinates):
            self.right_panel.math_panel.dl_coords.InsertStringItem(
                i, coord['name'])

    def _set_coordinate_sliders(self, coord_indices):
        self.right_panel.slider_panel.clear()
        for idx in range(len(self.coordinates)):
            self.right_panel.slider_panel.add_slider(
                self.coordinates[idx]['name'], 
                Param(0, 0, self.coordinates[idx]['size']-1),
                self.shaped_data,
                id_=idx
                )
            
            if idx not in coord_indices:
                self.right_panel.slider_panel.disable_slider(idx)
        
        self.right_panel.slider_panel.Bind(wx.EVT_SLIDER, self.on_coord_slider)

    def _size_constraint(self, size):
        new_size = list(size)
        for i, value in enumerate(size):
            if value < self.min_size[i]:
                new_size[i] = self.min_size[i]
        return tuple(new_size)

class App(wx.App):
    def OnInit(self):
              
        self.locale = wx.Locale(wx.LANGUAGE_ENGLISH)
        self.frame1 = MainFrame(title="Intensity Slice")
        self.frame1.Show()
        return True

if __name__ == '__main__':
    app = App(False)
    app.MainLoop()