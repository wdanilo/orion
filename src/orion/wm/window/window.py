from orion.wm.window import proto

import sys, struct, contextlib
#import xcb.xcb
from xcb.xproto import EventMask, StackMode, SetMode
import xcb.xproto
from orion import utils
#import command
from orion import hook

from orion.utils import flagEnum, enum

from icccm import wmState
import icccm
from xcb.xproto import CW
from orion.signals import SignalGroup
# float states
floatStates = enum(
        'NOT_FLOATING',
        'FLOATING',
        'MAXIMIZED',
        'FULLSCREEN',
        'TOP',
        'MINIMIZED',
)



class MaskMap:
    """
        A general utility class that encapsulates the way the mask/value idiom
        works in xpyb. It understands a special attribute _maskvalue on
        objects, which will be used instead of the object value if present.
        This lets us passin a Font object, rather than Font.fid, for example.
    """
    def __init__(self, obj):
        self.mmap = []
        for i in dir(obj):
            if not i.startswith("_"):
                self.mmap.append((getattr(obj, i), i.lower()))
        self.mmap.sort()

    def __call__(self, **kwargs):
        """
            kwargs: keys should be in the mmap name set

            Returns a (mask, values) tuple.
        """
        mask = 0
        values = []
        for m, s in self.mmap:
            if s in kwargs:
                val = kwargs.get(s)
                if val is not None:
                    mask |= m
                    values.append(getattr(val, "_maskvalue", val))
                del kwargs[s]
        if kwargs:
            raise ValueError("Unknown mask names: %s"%kwargs.keys())
        return mask, values

ConfigureMasks = MaskMap(xcb.xproto.ConfigWindow)
AttributeMasks = MaskMap(CW)
GCMasks = MaskMap(xcb.xproto.GC)

class _BaseWindow(object):
    def __init__(self, qtile):
        self.qtile = qtile
        self.hidden = True
        self.group = None
        self.name = "<no name>"
    
    def xx(self):
        self.set_attribute(eventmask=self._windowMask)
        try:
            g = self.get_geometry()
            self._x, self._y, self._width, self._height = g.x, g.y, g.width, g.height
            # note that _float_info x and y are
            # really offsets, relative to screen x,y
            self._float_info = {
                'x': g.x, 'y': g.y,
                'w': g.width, 'h': g.height
            }
        except xcb.xproto.BadDrawable:
            # Whoops, we were too early, so let's ignore it for now and get the
            # values on demand.
            self._x, self._y, self._width, self._height = None, None, None, None
            self._float_info = None
        self.borderwidth = 0
        self.bordercolor = None
        self.state = wmState.NORMAL
        self.window_type = "normal"
        self._float_state = floatStates.NOT_FLOATING

        self.hints = {
            'input': True,
            'state': wmState.NORMAL, #Normal state
            'icon_pixmap': None,
            'icon_window': None,
            'icon_x': 0,
            'icon_y': 0,
            'icon_mask': 0,
            'window_group': None,
            'urgent': False,
            # normal or size hints
            'width_inc': None,
            'height_inc': None,
            'base_width': 0,
            'base_height': 0,
            }
        self.updateHints()


    def update_name(self):
        try:
            self.name = self.get_name()
        except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
            return

    def updateHints(self):
        """
            update the local copy of the window's WM_HINTS
            http://tronche.com/gui/x/icccm/sec-4.html#WM_HINTS
        """
        try:
            h = self.get_wm_hints()
            normh = self.get_wm_normal_hints()
        except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
            return

        # FIXME
        # h values
        #{
        #    'icon_pixmap': 4194337,
        #    'icon_window': 0,
        #    'icon_mask': 4194340,
        #    'icon_y': 0,
        #    'input': 1,
        #    'icon_x': 0,
        #    'window_group': 4194305
        #    'initial_state': 1,
        #    'flags': set(['StateHint',
        #                  'IconMaskHint',
        #                  'WindowGroupHint',
        #                  'InputHint',
        #                  'UrgencyHint',
        #                  'IconPixmapHint']),
        #}

        if normh:
            normh.pop('flags')
            if(not normh['base_width']
                and normh['min_width'] and normh['width_inc']):
                # seems xcb does ignore base width :(
                normh['base_width'] = normh['min_width'] % normh['width_inc']
            if(not normh['base_height']
                and normh['min_height'] and normh['height_inc']):
                # seems xcb does ignore base height :(
                normh['base_height'] = normh['min_height'] % normh['height_inc']
            self.hints.update(normh)

        if h and 'UrgencyHint' in h['flags']:
            self.hints['urgent'] = True
            hook.fire('client_urgent_hint_changed', self)
        elif self.urgent:
            self.hints['urgent'] = False
            hook.fire('client_urgent_hint_changed', self)

        if getattr(self, 'group', None):
            self.group.layoutAll()

        return

    def updateState(self):
        self.fullscreen = self.get_net_wm_state() == 'fullscreen'

    @property
    def urgent(self):
        return self.hints['urgent']

    def info(self):
        if self.group:
            group = self.group.name
        else:
            group = None
        return dict(
            name = self.name,
            x = self.x,
            y = self.y,
            width = self.width,
            height = self.height,
            group = group,
            id = self.wid,
            floating = self._float_state != floatStates.NOT_FLOATING,
            float_info = self._float_info,
            maximized = self._float_state == floatStates.MAXIMIZED,
            minimized = self._float_state == floatStates.MINIMIZED,
            fullscreen = self._float_state == floatStates.FULLSCREEN

        )

    @property
    def state(self):
        return self.get_wm_state()[0]

    @state.setter
    def state(self, val):
        if val in (wmState.WITHDRAWN, wmState.NORMAL, wmState.ICONIC):
            self.set_property('WM_STATE', [val, 0])

    def setOpacity(self, opacity):
        if 0.0 <= opacity <= 1.0:
            real_opacity = int(opacity * 0xffffffff)
            self.set_property('_NET_WM_WINDOW_OPACITY', real_opacity)
        else:
            return

    def getOpacity(self):
        opacity = self.get_property("_NET_WM_WINDOW_OPACITY", unpack="I")
        if not opacity:
            return 1.0
        else:
            value = opacity[0]
            as_float = round(
                (float(value)/0xffffffff),
                2  #2 decimal places
                )
            return as_float

    opacity = property(getOpacity, setOpacity)

    def kill(self):
        if "WM_DELETE_WINDOW" in self.get_wm_protocols():
            #e = event.ClientMessage(
            #        window = self.window,
            #        client_type = self.qtile.display.intern_atom("WM_PROTOCOLS"),
            #        data = [
            #            # Use 32-bit format:
            #            32,
            #            # Must be exactly 20 bytes long:
            #            [
            #                self.qtile.display.intern_atom("WM_DELETE_WINDOW"),
            #                X.CurrentTime,
            #                0,
            #                0,
            #                0
            #            ]
            #        ]
            #)
            vals = [
                33, # ClientMessageEvent
                32, # Format
                0,
                self.wid,
                self.qtile.conn.atoms["WM_PROTOCOLS"],
                self.qtile.conn.atoms["WM_DELETE_WINDOW"],
                xcb.xproto.Time.CurrentTime,
                0,
                0,
                0,
            ]
            e = struct.pack('BBHII5I', *vals)
            self.send_event(e)
        else:
            self.kill_client()

    def hide(self):
        # We don't want to get the UnmapNotify for this unmap
        with self.disableMask(xcb.xproto.EventMask.StructureNotify):
            self.unmap()
        self.hidden = True

    def unhide(self):
        self.map()
        self.state = wmState.NORMAL
        self.hidden = False

    @contextlib.contextmanager
    def disableMask(self, mask):
        self._disableMask(mask)
        yield
        self._resetMask()

    def _disableMask(self, mask):
        self.set_attribute(
            eventmask=self._windowMask&(~mask)
        )

    def _resetMask(self):
        self.set_attribute(
            eventmask=self._windowMask
        )

    def place(self, x, y, width, height, borderwidth, bordercolor,
        above=False, force=False, twice=False):
        """
            Places the window at the specified location with the given size.

            if force is false, than it tries to obey hints
            if twice is true, that it does positioning twice (useful for some
                gtk apps)
        """
        # TODO(tailhook) uncomment resize increments when we'll decide
        #                to obey all those hints
        #if self.hints['width_inc']:
        #    width = (width -
        #        ((width - self.hints['base_width']) % self.hints['width_inc']))
        #if self.hints['height_inc']:
        #    height = (height -
        #        ((height - self.hints['base_height'])
        #        % self.hints['height_inc']))
        # TODO(tailhook) implement min-size, maybe
        # TODO(tailhook) implement max-size
        # TODO(tailhook) implement gravity
        self.x, self.y, self.width, self.height = x, y, width, height
        self.borderwidth, self.bordercolor = borderwidth, bordercolor

        # save x and y float offset
        if self.group is not None and self.group.screen is not None:
            self._float_info['x'] = x - self.group.screen.x
            self._float_info['y'] = y - self.group.screen.y

        kwarg = dict(
            x=x,
            y=y,
            width=width,
            height=height,
            borderwidth=borderwidth,
            )
        if above:
            kwarg['stackmode'] = StackMode.Above

        # Oh, yes we do this twice
        #
        # This sort of weird thing is because GTK assumes that each it's
        # configure request is replied with configure notify. But X server
        # is smarter than that and does not send configure notify if size is
        # not changed. So we hack this.
        #
        # And no, manually sending ConfigureNotifyEvent does nothing, really!
        #
        # We use increment position because its more probably will
        # lead to less calculations on the application side (no word
        # rewrapping, widget resizing, etc.)
        #
        # TODO(tailhook) may be configure notify event will work for reparented
        # windows
        if twice:
            kwarg['y'] -= 1
            self.configure(**kwarg)
            kwarg['y'] += 1
        self.configure(**kwarg)

        if bordercolor is not None:
            self.set_attribute(
                borderpixel = bordercolor
            )

    def focus(self, warp):
        if not self.hidden and self.hints['input']:
            self.set_input_focus()
            try:
                if warp and self.qtile.config.cursor_warp:
                    self.warp_pointer(self.width//2, self.height//2)
            except AttributeError:
                pass

    def _items(self, name, sel):
        return None

    def _select(self, name, sel):
        return None

    def cmd_info(self):
        """
            Returns a dictionary of info for this object.
        """
        return self.info()

    def cmd_inspect(self):
        """
            Tells you more than you ever wanted to know about a window.
        """
        a = self.get_attributes()
        attrs = {
            "backing_store": a.backing_store,
            "visual": a.visual,
            "class": a._class,
            "bit_gravity": a.bit_gravity,
            "win_gravity": a.win_gravity,
            "backing_planes": a.backing_planes,
            "backing_pixel": a.backing_pixel,
            "save_under": a.save_under,
            "map_is_installed": a.map_is_installed,
            "map_state": a.map_state,
            "override_redirect": a.override_redirect,
            #"colormap": a.colormap,
            "all_event_masks": a.all_event_masks,
            "your_event_mask": a.your_event_mask,
            "do_not_propagate_mask": a.do_not_propagate_mask
        }
        props = self.list_properties()
        normalhints = self.get_wm_normal_hints()
        hints = self.get_wm_hints()
        protocols = []
        for i in self.get_wm_protocols():
            protocols.append(i)

        state = self.get_wm_state()

        return dict(
            attributes=attrs,
            properties=props,
            name = self.get_name(),
            wm_class = self.get_wm_class(),
            wm_window_role = self.get_wm_window_role(),
            wm_type = self.get_wm_type(),
            wm_transient_for = self.get_wm_transient_for(),
            protocols = protocols,
            wm_icon_name = self.get_wm_icon_name(),
            wm_client_machine = self.get_wm_client_machine(),
            normalhints = normalhints,
            hints = hints,
            state = state,
            float_info = self._float_info
        )


class Window(_BaseWindow):
    _windowMask = EventMask.StructureNotify |\
                  EventMask.PropertyChange |\
                  EventMask.EnterWindow |\
                  EventMask.FocusChange
    
    def xxx(self,qtile):
        self.xx()
        self.update_name()

        # add window to the save-set, so it gets mapped when qtile dies
        qtile.conn.conn.core.ChangeSaveSet(SetMode.Insert, self.wid)
    
    def __init__(self, conn, wid, qtile):
        _BaseWindow.__init__(self, qtile)
        self.qtile = qtile
        self.conn, self.wid = conn, wid
        
        self.events = SignalGroup(
            'create',        
            'mouse_enter',        
            'key_press',        
            'key_release',        
            'map_request',        
            'destroy_notify',        
            'property_notify',        
            'client_message',        
            'configure_request',        
            'configure_notify',        
        )
        
        self.events.property_notify.connect(self.handle_PropertyNotify)
        self.events.configure_request.connect(self.handle_ConfigureRequest)
        #self.on_mouse_enter.connect(self.handle_EnterNotify)

    def _propertyString(self, r):
        """
            Extract a string from a window property reply message.
        """
        return "".join(chr(i) for i in r.value)

#    def send_event(self, eventbuf, mask=EventMask.NoEvent):
#        self.conn.conn.core.SendEvent(False, self.wid, mask, eventbuf)

#    def kill_client(self):
#        self.conn.conn.core.KillClient(self.wid)

    def set_input_focus(self):
        self.conn.conn.core.SetInputFocus(
            xcb.xproto.InputFocus.PointerRoot,
            self.wid,
            xcb.xproto.Time.CurrentTime
        )

#    def warp_pointer(self, x, y):
#        self.conn.conn.core.WarpPointer(
#                0
#                ,self.wid
#                ,0
#                ,0
#                ,0
#                ,0
#                ,x
#                ,y
#        )

    def get_name(self):
        """
            Tries to retrieve a canonical window name. We test the following
            properties in order of preference: _NET_WM_VISIBLE_NAME,
            _NET_WM_NAME, WM_NAME.
        """
        r = self.get_property("_NET_WM_VISIBLE_NAME", xcb.xproto.GetPropertyType.Any)
        if r:
            return self._propertyString(r)

        r = self.get_property("_NET_WM_NAME", xcb.xproto.GetPropertyType.Any)
        if r:
            return self._propertyString(r)

        r = self.get_property(xcb.xproto.Atom.WM_NAME, xcb.xproto.GetPropertyType.Any)
        if r:
            return self._propertyString(r)

    def get_wm_hints(self):
        r = self.get_property("WM_HINTS", xcb.xproto.GetPropertyType.Any)
        if r:
            data = struct.pack("B" * len(r.value), *(list(r.value)))
            l = struct.unpack_from("=IIIIIIIII", data)
            flags = set()
            for k, v in proto.HintsFlags.items():
                if l[0]&v:
                    flags.add(k)
            return dict(
                flags = flags,
                input = l[1],
                initial_state = l[2],
                icon_pixmap = l[3],
                icon_window = l[4],
                icon_x = l[5],
                icon_y = l[6],
                icon_mask = l[7],
                window_group = l[8]
            )

    def get_wm_normal_hints(self):
        r = self.get_property("WM_NORMAL_HINTS", xcb.xproto.GetPropertyType.Any)
        if r:
            data = struct.pack("B" * len(r.value), *(list(r.value)))
            l = struct.unpack_from("=IIIIIIIIIIIIII", data)
            flags = set()
            for k, v in icccm.NormalHintsFlags.items():
                if l[0]&v:
                    flags.add(k)
            return dict(
                flags = flags,
                min_width = l[1+4],
                min_height = l[2+4],
                max_width = l[3+4],
                max_height = l[4+4],
                width_inc = l[5+4],
                height_inc = l[6+4],
                min_aspect = l[7+4],
                max_aspect = l[8+4],
                base_width = l[9+4],
                base_height = l[9+4],
                win_gravity = l[9+4],
            )

#    def get_wm_protocols(self):
#        r = self.get_property("WM_PROTOCOLS", xcb.xproto.GetPropertyType.Any)
#        if r:
#            data = struct.pack("B" * len(r.value), *(list(r.value)))
#            l = struct.unpack_from("=" + "L"*r.value_len, data)
#            return set([self.conn.atoms.get_name(i) for i in l])
#        else:
#            return set()

    def get_wm_state(self):
        r = self.get_property("WM_STATE", xcb.xproto.GetPropertyType.Any)
        if r:
            return struct.unpack('=LL', r.value.buf())

#    def get_wm_class(self):
#        """
#            Return an (instance, class) tuple if WM_CLASS exists, or None.
#        """
#        r = self.get_property("WM_CLASS", "STRING")
#        if r:
#            s = self._propertyString(r)
#            return tuple(s.strip("\0").split("\0"))

#    def get_wm_window_role(self):
#        r = self.get_property("WM_WINDOW_ROLE", "STRING")
#        if r:
#            return self._propertyString(r)
#
#    def get_wm_transient_for(self):
#        r = self.get_property("WM_TRANSIENT_FOR", "ATOM")
#        if r:
#            return list(r.value)
#
#    def get_wm_icon_name(self):
#        r = self.get_property("WM_ICON_NAME", "UTF8_STRING")
#        if r:
#            return self._propertyString(r)
#
#    def get_wm_client_machine(self):
#        r = self.get_property("WM_CLIENT_MACHINE", "UTF8_STRING")
#        if r:
#            return self._propertyString(r)
#
    def get_geometry(self):
        q = self.conn.conn.core.GetGeometry(self.wid)
        return q.reply()
#
#    def get_wm_desktop(self):
#        r = self.get_property("_NET_WM_DESKTOP", "CARDINAL")
#        if r:
#            return r.value[0]
#
    def get_wm_type(self):
        """
            http://standards.freedesktop.org/wm-spec/wm-spec-latest.html#id2551529
        """
        r = self.get_property('_NET_WM_WINDOW_TYPE', "ATOM", unpack='I')
        if r:
            name = self.conn.atoms.get_name(r[0])
            return proto.WindowTypes.get(name, name)

    def get_net_wm_state(self):
        r = self.get_property('_NET_WM_STATE', "ATOM", unpack='I')
        if r:
            name = self.conn.atoms.get_name(r[0])
            return proto.WindowStates.get(name, name)

    def configure(self, **kwargs):
        """
            Arguments can be: x, y, width, height, border, sibling, stackmode
        """
        mask, values = ConfigureMasks(**kwargs)
        return self.conn.conn.core.ConfigureWindow(self.wid, mask, values)

    def set_attribute(self, **kwargs):
        mask, values = AttributeMasks(**kwargs)
        self.conn.conn.core.ChangeWindowAttributesChecked(self.wid, mask, values)

    def set_property(self, name, value, type=None, format=None):
        """
            name: String Atom name
            type: String Atom name
            format: 8, 16, 32
        """
        if name in proto.PropertyMap:
            if type or format:
                raise ValueError, "Over-riding default type or format for property."
            type, format = proto.PropertyMap[name]
        else:
            if None in (type, format):
                raise ValueError, "Must specify type and format for unknown property."

        if not utils.isSequenceLike(value):
            value = [value]

        buf = []
        for i in value:
            # We'll expand these conversions as we need them
            if format == 32:
                buf.append(struct.pack("=L", i))
            elif format == 16:
                buf.append(struct.pack("=H", i))
            elif format == 8:
                if utils.isStringLike(i):
                    # FIXME: Unicode -> bytes conversion needed here
                    buf.append(i)
                else:
                    buf.append(struct.pack("=B", i))
        buf = "".join(buf)

        length = len(buf)/(format/8)

        # This is a real balls-up interface-wise. As I understand it, each type
        # can have a different associated size.
        #  - value is a string of bytes.
        #  - length is the length of the data in terms of the specified format.
        self.conn.conn.core.ChangeProperty(
            xcb.xproto.PropMode.Replace,
            self.wid,
            self.conn.atoms[name],
            self.conn.atoms[type],
            format,  # Format - 8, 16, 32
            length,
            buf
        )

    def get_property(self, prop, type=None, unpack=None):
        """
            Return the contents of a property as a GetPropertyReply, or
            a tuple of values if unpack is specified, which is a format
            string to be used with the struct module.
        """
        if type is None:
            if not prop in proto.PropertyMap:
                raise ValueError, "Must specify type for unknown property."
            else:
                type, _ = proto.PropertyMap[prop]
        r = self.conn.conn.core.GetProperty(
            False, self.wid,
            self.conn.atoms[prop] if isinstance(prop, basestring) else prop,
            self.conn.atoms[type] if isinstance(type, basestring) else type,
            0, (2**32)-1
        ).reply()

        if not r.value_len:
            return None
        elif unpack is not None:
            return struct.unpack_from(unpack, r.value.buf())
        else:
            return r

#    def list_properties(self):
#        r = self.conn.conn.core.ListProperties(self.wid).reply()
#        return [self.conn.atoms.get_name(i) for i in r.atoms]

    def map(self):
        self.conn.conn.core.MapWindow(self.wid)

    def unmap(self):
        self.conn.conn.core.UnmapWindow(self.wid)

    def get_attributes(self):
        return self.conn.conn.core.GetWindowAttributes(self.wid).reply()
#
#    def create_gc(self, **kwargs):
#        gid = self.conn.conn.generate_id()
#        mask, values = GCMasks(**kwargs)
#        self.conn.conn.core.CreateGC(gid, self.wid, mask, values)
#        return GC(self.conn, gid)

    def ungrab_key(self, key, modifiers):
        """
            Passing None means any key, or any modifier.
        """
        if key is None:
            key = xcb.xproto.Atom.Any
        if modifiers is None:
            modifiers = xcb.xproto.ModMask.Any
        self.conn.conn.core.UngrabKey(key, self.wid, modifiers)

    def grab_key(self, key, modifiers, owner_events, pointer_mode, keyboard_mode):
        self.conn.conn.core.GrabKey(
            owner_events,
            self.wid,
            modifiers,
            key,
            pointer_mode,
            keyboard_mode
        )

    def ungrab_button(self, button, modifiers):
        """
            Passing None means any key, or any modifier.
        """
        if button is None:
            button = xcb.xproto.Atom.Any
        if modifiers is None:
            modifiers = xcb.xproto.ModMask.Any
        self.conn.conn.core.UngrabButton(button, self.wid, modifiers)

    def grab_button(self, button, modifiers, owner_events, event_mask, pointer_mode, keyboard_mode):
        self.conn.conn.core.GrabButton(
            owner_events,
            self.wid,
            event_mask,
            pointer_mode,
            keyboard_mode,
            xcb.xproto.Atom._None,
            xcb.xproto.Atom._None,
            button,
            modifiers,
        )

#    def grab_pointer(self, owner_events, event_mask, pointer_mode, keyboard_mode, cursor=None):
#        self.conn.conn.core.GrabPointer(
#            owner_events,
#            self.wid,
#            event_mask,
#            pointer_mode,
#            keyboard_mode,
#            xcb.xproto.Atom._None,
#            cursor or xcb.xproto.Atom._None,
#            xcb.xproto.Atom._None,
#        )
#
#    def ungrab_pointer(self):
#        self.conn.conn.core.UngrabPointer(
#            xcb.xproto.Atom._None,
#        )

    def query_tree(self):
        q = self.conn.conn.core.QueryTree(self.wid).reply()
        root, parent = None, None
        if q.root:
            root = Window(self.conn, q.root, self.qtile)
        if q.parent:
            parent = Window(self.conn, q.root, self.qtile)
        return root, parent, [Window(self.conn, i, self.qtile) for i in q.children]
    
    
    #################
    
    
    
    @property
    def floating(self):
        return self._float_state != floatStates.NOT_FLOATING

    @floating.setter
    def floating(self, do_float):
        if do_float:
            if self._float_state == floatStates.NOT_FLOATING:
                self.enablefloating()


    @property
    def fullscreen(self):
        return self._float_state == floatStates.FULLSCREEN

    @fullscreen.setter
    def fullscreen(self, do_full):
        if do_full:
            if self._float_state != floatStates.FULLSCREEN:
                self.enablemaximize(state=floatStates.FULLSCREEN)
        else:
            if self._float_state == floatStates.FULLSCREEN:
                self.disablefloating()

    @property
    def maximized(self):
        return self._float_state == floatStates.MAXIMIZED

    @maximized.setter
    def maximized(self, do_maximize):
        if do_maximize:
            if self._float_state != floatStates.MAXIMIZED:
                self.enablemaximize()
        else:
            if self._float_state == floatStates.MAXIMIZED:
                self.disablefloating()

    @property
    def minimized(self):
        return self._float_state == floatStates.MINIMIZED

    @minimized.setter
    def minimized(self, do_minimize):
        if do_minimize:
            if self._float_state != floatStates.MINIMIZED:
                self.enableminimize()
        else:
            if self._float_state == floatStates.MINIMIZED:
                self.disablefloating()


    '''def static(self, screen, x=None, y=None, width=None, height=None):
        """
            Makes this window a static window, attached to a Screen. If any of
            the arguments are left unspecified, the values given by the window
            itself are used instead. So, for a window that's aware of its
            appropriate size and location (like dzen), you don't have to
            specify anything.
        """
        self.defunct = True
        screen = self.qtile.screens[screen]
        if self.group:
            self.group.remove(self)
        s = Static(self.window, self.qtile, screen, x, y, width, height)
        self.qtile.windowMap[self.window.wid] = s
        hook.fire("client_managed", s)
        return s
    '''

    def tweak_float(self, x=None, y=None, dx=0, dy=0,
                    w=None, h=None, dw=0, dh=0):
        if x is not None:
            self.x = x
        self.x += dx

        if y is not None:
            self.y = y
        self.y += dy

        if w is not None:
            self.width = w
        self.width += dw

        if h is not None:
            self.height = h
        self.height += dh

        if self.height < 0:
            self.height = 0
        if self.width < 0:
            self.width = 0

        screen = self.qtile.find_closest_screen(self.x, self.y)
        if screen is not None and screen != self.group.screen:
            self.group.remove(self)
            screen.group.add(self)
            self.qtile.toScreen(screen.index)
            # TODO - need to kick boxes to update

        self._reconfigure_floating()

    def getsize(self):
        return self.width, self.height

    def getposition(self):
        return self.x, self.y

    def toggleminimize(self):
        if self.minimized:
            self.disablefloating()
        else:
            self.enableminimize()

    def enableminimize(self):
        self._enablefloating(new_float_state=floatStates.MINIMIZED)

    def togglemaximize(self, state=floatStates.MAXIMIZED):
        if self._float_state == state:
            self.disablefloating()
        else:
            self.enablemaximize(state)

    def enablemaximize(self, state=floatStates.MAXIMIZED):
        screen = self.group.screen
        if state == floatStates.MAXIMIZED:
            self._enablefloating(screen.dx,
                             screen.dy,
                             screen.dwidth,
                             screen.dheight,
                             new_float_state=state)
        elif state == floatStates.FULLSCREEN:
            self._enablefloating(screen.x,
                                 screen.y,
                                 screen.width,
                                 screen.height,
                                 new_float_state=state)

    def togglefloating(self):
        if self.floating:
            self.disablefloating()
        else:
            self.enablefloating()

    def _reconfigure_floating(self, new_float_state=floatStates.FLOATING):
        if new_float_state == floatStates.MINIMIZED:
            self.state = wmState.ICONIC
            self.hide()
        else:
            # make sure x, y is on the screen
            screen = self.qtile.find_closest_screen(self.x, self.y)
            if screen is not None and self.group is not None and \
                  self.group.screen is not None and screen != self.group.screen:
                self.x = self.group.screen.x
                self.y = self.group.screen.y
            self.place(self.x,
                   self.y,
                   self.width,
                   self.height,
                   self.borderwidth,
                   self.bordercolor,
                   above=True,
                   )
        if self._float_state != new_float_state:
            self._float_state = new_float_state
            if self.group: # may be not, if it's called from hook
                self.group.mark_floating(self, True)
            hook.fire('float_change')

    def _enablefloating(self, x=None, y=None, w=None, h=None, new_float_state=floatStates.FLOATING):
        if new_float_state != floatStates.MINIMIZED:
            self.x = x
            self.y = y
            self.width = w
            self.height = h
        self._reconfigure_floating(new_float_state=new_float_state)

    def enablefloating(self):
        fi = self._float_info
        self._enablefloating(fi['x'], fi['y'], fi['w'], fi['h'])

    def disablefloating(self):
        if self._float_state != floatStates.NOT_FLOATING:
            if self._float_state == floatStates.FLOATING:
                # store last size
                fi = self._float_info
                fi['w'] = self.width
                fi['h'] = self.height
            self._float_state = floatStates.NOT_FLOATING
            self.group.mark_floating(self, False)
            hook.fire('float_change')


    def match(self, wname=None, wmclass=None, role=None):
        """
            Match window against given attributes.

            - wname matches against the window name or title, that is,
            either `_NET_WM_VISIBLE_NAME`, `_NET_WM_NAME`, `WM_NAME`.

            - wmclass matches against any of the two values in the
            `WM_CLASS` property

            - role matches against the `WM_WINDOW_ROLE` property
        """
        if not (wname or wmclass or role):
            raise TypeError, "Either a name, a wmclass or a role must be specified"
        if wname and wname == self.name:
            return True

        try:

            cliclass = self.window.get_wm_class()
            if wmclass and cliclass and wmclass in cliclass:
                return True

            clirole = self.window.get_wm_window_role()
            if role and clirole and role == clirole:
                return True

        except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
            return False

        return False

    def handle_event(self, e):
        print '>>> %s'%e.name
        if e.name == 'KeyPressEvent':
            keycode = self.conn.code_to_syms[e.detail][0]
            self.on_key_press(keycode=keycode, state=e.state, event=e)
        elif e.name == 'KeyReleaseEvent':
            keycode = self.conn.code_to_syms[e.detail][0]
            self.on_key_release(keycode=keycode, state=e.state, event=e)
        elif e.name == 'MapRequestEvent':
            self.on_map_request(event=e)
        elif e.name == 'DestroyNotifyEvent':
            self.on_destroy_notify(event=e)
        elif e.name == 'PropertyNotifyEvent':
            self.on_property_notify(event=e)
        elif e.name == 'ClientMessageEvent':
            self.on_client_message(event=e)
        elif e.name == 'ConfigureRequestEvent':
            self.on_configure_request(event=e)
        elif e.name == 'ConfigureNotifyEvent':
            self.on_configure_notify(event=e)
        elif e.name == 'EnterNotifyEvent':
            self.on_mouse_enter(event=e)
        else:
            print 'Unknown event: %s'%e.name
        
    def handle_EnterNotify(self, e):
        hook.fire("client_mouse_enter", self)
        if self.qtile.config.follow_mouse_focus and \
                        self.group.currentWindow != self:
            self.group.focus(self, False)
        if self.group.screen and self.qtile.currentScreen != self.group.screen:
            self.qtile.toScreen(self.group.screen.index)
        return True

    def handle_ConfigureRequest(self, e):
        '''
        FIXME: w okienku bedacym root, ponizsza obsluga jest niepotrzebna!
        '''
        if self.qtile._drag and self.qtile.currentWindow == self:
            # ignore requests while user is dragging window
            return
        if getattr(self, 'floating', False):
            # only obey resize for floating windows
            cw = xcb.xproto.ConfigWindow
            if e.value_mask & cw.X:
                self.x = e.x
            if e.value_mask & cw.Y:
                self.y = e.y
            if e.value_mask & cw.Width:
                self.width = e.width
            if e.value_mask & cw.Height:
                self.height = e.height
        if self.group and self.group.screen:
            self.place(
                self.x,
                self.y,
                self.width,
                self.height,
                self.borderwidth,
                self.bordercolor,
                twice=True,
            )
        return False

    def handle_PropertyNotify(self, e):
        name = self.qtile.conn.atoms.get_name(e.atom)
        if name == "WM_TRANSIENT_FOR":
            pass
        elif name == "WM_HINTS":
            self.updateHints()
        elif name == "WM_NORMAL_HINTS":
            pass
        elif name == "WM_NAME":
            self.update_name()
        elif name == "_NET_WM_NAME":
            self.update_name()
        elif name == "_NET_WM_VISIBLE_NAME":
            self.update_name()
        elif name == "_NET_WM_WINDOW_OPACITY":
            pass
        elif name == "_NET_WM_STATE":
            self.updateState()
        elif name == "WM_PROTOCOLS":
            pass
        elif name == "_NET_WM_USER_TIME":
            if not self.qtile.config.follow_mouse_focus and \
                            self.group.currentWindow != self:
                self.group.focus(self, False)

        elif self.qtile.debug:
            print >> sys.stderr, "Unknown window property: ", name
        return False

    def _items(self, name):
        if name == "group":
            return True, None
        elif name == "layout":
            return True, range(len(self.group.layouts))
        elif name == "screen":
            return True, None

    def _select(self, name, sel):
        if name == "group":
            return self.group
        elif name == "layout":
            if sel is None:
                return self.group.layout
            else:
                return utils.lget(self.group.layouts, sel)
        elif name == "screen":
            return self.group.screen

    def __repr__(self):
        return "Window(%s)"%self.name

    def cmd_static(self, screen, x, y, width, height):
        self.static(screen, x, y, width, height)

    def cmd_kill(self):
        """
            Kill this window. Try to do this politely if the client support
            this, otherwise be brutal.
        """
        self.kill()

    def cmd_togroup(self, groupName):
        """
            Move window to a specified group.

            Examples:

                togroup("a")
        """
        self.togroup(groupName)

    def cmd_move_floating(self, dx, dy):
        """
            Move window by dx and dy
        """
        self.tweak_float(dx=dx, dy=dy)

    def cmd_resize_floating(self, dw, dh):
        """
            Add dw and dh to size of window
        """
        self.tweak_float(dw=dw, dh=dh)

    def cmd_set_position_floating(self, x, y):
        """
            Move window to x and y
        """
        self.tweak_float(x=x, y=y)

    def cmd_set_size_floating(self, w, h):
        """
            Set window dimensions to w and h
        """
        self.tweak_float(w=w, h=h)

    def cmd_get_position(self):
        return self.getposition()

    def cmd_get_size(self):
        return self.getsize()

    def cmd_toggle_floating(self):
        self.togglefloating()

    def cmd_disable_floating(self):
        self.disablefloating()

    def cmd_enable_floating(self):
        self.enablefloating()

    def cmd_toggle_maximize(self):
        self.togglemaximize()

    def cmd_disable_maximimize(self):
        self.disablefloating()

    def cmd_enable_maximize(self):
        self.enablemaximize()

    def cmd_toggle_fullscreen(self):
        self.togglemaximize(state=floatStates.FULLSCREEN)

    def cmd_enable_fullscreen(self):
        self.enablemaximize(state=floatStates.FULLSCREEN)

    def cmd_disable_fullscreen(self):
        self.disablefloating()

    def cmd_toggle_minimize(self):
        self.toggleminimize()

    def cmd_enable_minimize(self):
        self.enableminimize()

    def cmd_disable_minimize(self):
        self.disablefloating()

    def cmd_bring_to_front(self):
        if self.floating:
            self.window.configure(stackmode=StackMode.Above)
        else:
            self._reconfigure_floating() #atomatically above

    def cmd_match(self, *args, **kwargs):
        return self.match(*args, **kwargs)

    def cmd_opacity(self, opacity):
        if opacity < .1:
            self.opacity = .1
        elif opacity > 1:
            self.opacity = 1
        else:
            self.opacity = opacity

    def cmd_down_opacity(self):
        if self.opacity > .2:
            # don't go completely clear
            self.opacity -= .1
        else:
            self.opacity = .1

    def cmd_up_opacity(self):
        if self.opacity < .9:
            self.opacity += .1
        else:
            self.opacity = 1
