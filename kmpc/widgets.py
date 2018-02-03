# make sure we are on an updated version of kivy
import kivy
kivy.require('1.10.0')

# import all the other kivy stuff
from kivy.graphics import Rectangle
from kivy.uix.image import Image,AsyncImage
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import ObjectProperty

# import our local modules
from kmpc.extra import OutlineLabel,OutlineButton

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
        self.background_normal = resource_filename(__name__,os.path.join('resources','clear.png'))
        self.background_down = resource_filename(__name__,os.path.join('resources','clear.png'))
        self.font_name = resource_filename(__name__,os.path.join('resources','DejaVuSans-Bold.ttf'))
        with self.canvas.before:
            Rectangle(texture=self.img.texture,pos=self.layout.pos,size=self.layout.size)

