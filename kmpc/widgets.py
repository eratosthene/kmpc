import os
from pkg_resources import resource_filename

# make sure we are on an updated version of kivy
import kivy
kivy.require('1.10.0')

# import all the other kivy stuff
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.graphics import Rectangle
from kivy.uix.image import Image,AsyncImage
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import ObjectProperty
from kivy.uix.behaviors import ButtonBehavior, FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.textinput import TextInput
from kivy.properties import BooleanProperty

normalfont = resource_filename(__name__,os.path.join('resources/fonts','DejaVuSans.ttf'))
boldfont = resource_filename(__name__,os.path.join('resources/fonts','DejaVuSans-Bold.ttf'))
fontawesomefont = resource_filename(__name__,os.path.join('resources/fonts','FontAwesome.ttf'))

class ExtraSlider(Slider):
    """Class that implements some extra stuff on top of a standard slider."""

    def __init__(self,**kwargs):
        """Do normal init routine, but also register on_release event."""
        super(self.__class__,self).__init__(**kwargs)
        self.register_event_type('on_release')

    def on_release(self):
        """Override this with something you want this slider to do."""
        pass

    def on_touch_up(self, touch):
        """Check if slider is released, dispatch the on_release event if so."""
        released = super(self.__class__,self).on_touch_up(touch)
        if released:
            self.dispatch('on_release')
        return released

class OutlineLabel(Label):
    """A label that has an outline around it."""
    pass

class OutlineButton(Button,OutlineLabel):
    """A button with a label that has an outline around it."""
    pass

class ClearButton(Button,OutlineLabel):
    """A button that is clear instead of opaque."""
    pass

class OutlineTabbedPanelItem(TabbedPanelItem,OutlineLabel):
    """A label that has an outline around it."""
    pass

class InfoLargeLabel(OutlineLabel):
    """A label with large text."""
    pass

class ImageButton(ButtonBehavior, AsyncImage):
    """An image that you can press."""
    pass

class CoverButton(OutlineButton):
    img = ObjectProperty(None)
    layout = ObjectProperty(None)

    def __init__(self,**kwargs):
        super(self.__class__,self).__init__(**kwargs)
        self.background_normal = resource_filename(__name__,os.path.join('resources/images','clear.png'))
        self.background_down = resource_filename(__name__,os.path.join('resources/images','clear.png'))
        self.font_name = resource_filename(__name__,os.path.join('resources/fonts','DejaVuSans-Bold.ttf'))
        with self.canvas.before:
            Rectangle(texture=self.img.texture,pos=self.layout.pos,size=self.layout.size)

class ArtistRecycleBoxLayout(FocusBehavior,LayoutSelectionBehavior,RecycleBoxLayout):
    ''' Adds selection and focus behaviour to the view. '''

class ArtistRow(RecycleDataViewBehavior,BoxLayout):
    ''' Add selection support to the Label '''
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        ''' Catch and handle the view changes '''
        self.index = index
        return super(ArtistRow, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        ''' Add selection on touch down '''
        if super(ArtistRow, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        ''' Respond to the selection of items in the view. '''
        self.selected = is_selected
        if is_selected:
            App.get_running_app().root.selected_row=index

class UneditTextInput(TextInput):
    def insert_text(self, substring, from_undo=False):
        pass

