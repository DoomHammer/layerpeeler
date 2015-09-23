from __future__ import print_function
from docker import Client
from treelib import Node, Tree
import sys
import urwid


class ExampleTreeWidget(urwid.TreeWidget):

    __metaclass__ = urwid.MetaSignals
    signals = ['remove_image']

    def __init__(self, node):
        self.__super.__init__(node)
        # insert an extra AttrWrap for our own use
        self._w = urwid.AttrWrap(self._w, None)
        self.tagged = False
        self.update_w()

    def selectable(self):
        return True

    def keypress(self, size, key):
        """allow subclasses to intercept keystrokes"""
        key = self.__super.keypress(size, key)
        if key:
            key = self.unhandled_keys(size, key)
        return key

    def unhandled_keys(self, size, key):
        """
        Override this method to intercept keystrokes in subclasses.
        Default behavior: Toggle flagged on space, ignore other keys.
        """
        if key == "d":
            tree = self.get_node().get_value()
            tag = tree.get_node(tree.root).tag
            data = tree.get_node(tree.root).data
            urwid.emit_signal(self, 'remove_image', {u'Tag': tag, u'Data': data})
            self.tagged = not self.tagged
            self.update_w()
        else:
            return key

    def update_w(self):
        """Update the attributes of self.widget based on self.flagged.
        """
        if self.tagged:
            self._w.attr = 'tagged'
            self._w.focus_attr = 'tagged focus'
        else:
            self._w.attr = 'body'
            self._w.focus_attr = 'focus'

    def get_display_text(self):
        """ Display widget for leaf nodes """
        tree = self.get_node().get_value()
        tag = tree.get_node(tree.root).tag
        data = tree.get_node(tree.root).data
        if data is not None and data[u'Dangling']:
            return ('flag', tag)
        else:
            return tag


class ExampleNode(urwid.TreeNode):
    """ Data storage object for leaf nodes """

    def __init__(self, data, browser, *args, **kwargs):
        urwid.TreeNode.__init__(self, data, *args, **kwargs)
        self.browser = browser

    def load_widget(self):
        widget = ExampleTreeWidget(self)
        urwid.connect_signal(widget, 'remove_image', self.browser.remove_dialog)
        return widget


class ExampleParentNode(urwid.ParentNode):
    """ Data storage object for interior/parent nodes """

    def __init__(self, data, browser, *args, **kwargs):
        urwid.ParentNode.__init__(self, data, *args, **kwargs)
        self.browser = browser

    def load_widget(self):
        widget = ExampleTreeWidget(self)
        urwid.connect_signal(widget, 'remove_image', self.browser.remove_dialog)
        return widget

    def load_child_keys(self):
        data = self.get_value()
        return data.get_node(data.root).fpointer

    def load_child_node(self, key):
        """Return either an ExampleNode or ExampleParentNode"""
        childdata = self.get_value().subtree(key)
        childdepth = self.get_depth() + 1
        if not childdata.get_node(childdata.root).is_leaf():
            childclass = ExampleParentNode
        else:
            childclass = ExampleNode
        return childclass(childdata, self.browser, parent=self, key=key, depth=childdepth)


class ExampleTreeBrowser(object):

    palette = [
        ('body', 'light gray', 'black'),
        ('focus', 'light gray', 'dark blue', 'standout'),
        ('head', 'yellow', 'black', 'standout'),
        ('foot', 'black', 'dark blue'),
        ('key', 'light cyan', 'dark blue', 'underline'),
        ('title', 'white', 'dark blue', 'bold'),
        ('flag', 'light red', 'black'),
        ('tagged', '', 'dark gray'),
        ('error', 'dark red', 'black'),
        ]

    footer_text = [
        ('title', "Docker Image Layers Browser"), "    ",
        ('key', "UP"), ",", ('key', "DOWN"), ",",
        ('key', "PAGE UP"), ",", ('key', "PAGE DOWN"),
        "  ",
        ('key', "+"), ",",
        ('key', "-"), "  ",
        ('key', "LEFT"), "  ",
        ('key', "HOME"), "  ",
        ('key', "END"), "  ",
        " ",
        ('key', 'd'), "  ",
        " ",
        ('key', "Q"),
        ]

    def __init__(self, docker_if):
        self.docker_if = docker_if
        self.header = urwid.Text("Docker Images")
        self.footer = urwid.AttrWrap(urwid.Text(self.footer_text),
                                     'foot')
        self.frame = urwid.Frame(
            None,
            header=urwid.AttrWrap(self.header, 'head'),
            footer=self.footer)
        self.loop = None
        self.update_content(True)

    def main(self):
        """Run the program."""

        self.loop = urwid.MainLoop(self.view, self.palette,
                                   unhandled_input=self.unhandled_input)
        self.loop.run()

    def unhandled_input(self, k):
        if k in ('q', 'Q'):
            raise urwid.ExitMainLoop()

    def update_content(self, reload_data=False):
        if reload_data:
            data = self.docker_if.get_image_tree()
            self.topnode = ExampleParentNode(data, self)
            self.walker = urwid.TreeWalker(self.topnode)
            self.listbox = urwid.TreeListBox(self.walker)
            self.listbox.offset_rows = 0
        self.frame.body = urwid.AttrWrap(self.listbox, 'body')
        self.view = self.frame
        if self.loop:
            self.loop.widget = self.view

    def update_cb(self, *args, **kwargs):
        if len(args) > 1 and args[1]:
            self.update_content(True)
        else:
            self.update_content(False)

    def remove_dialog(self, user_args, *args, **kwargs):
        text = urwid.Text("Are you sure you want to remove image %s?" % user_args[u'Tag'])
        yes = urwid.Button("Yes")
        no = urwid.Button("No", self.update_cb)
        urwid.connect_signal(no, 'click', self.update_cb)
        urwid.connect_signal(yes, 'click', self.remove_image, user_args=[user_args])
        question = urwid.ListBox(urwid.SimpleFocusListWalker((text, urwid.Divider(), no, yes)))
        overlay = urwid.Overlay(question, self.view, 'center', ('relative', 30), 'middle',
                                ('relative', 30))
        self.loop.widget = overlay

    def remove_image(self, *args, **kwargs):
        text = urwid.Text("Removing image %s..." % args[0][u'Tag'])
        div = urwid.Divider()
        placeholder = urwid.Text("")
        ok = urwid.Button("OK", self.update_cb, True)
        listwalker = urwid.SimpleFocusListWalker([text, div, placeholder])
        listbox = urwid.ListBox(listwalker)
        overlay = urwid.Overlay(listbox, self.view, 'center', ('relative', 30), 'middle',
                                ('relative', 30))
        self.loop.widget = overlay
        try:
            self.docker_if.remove_image(image=args[0][u'Data'][u'image'][u'Id'])
        except Exception, e:
            text.set_text(text.get_text()[0] + " FAILED (%s)" % str(e))
        else:
            text.set_text(text.get_text()[0] + " OK")
        listwalker[-1] = ok


class DockerIf(object):
    def __init__(self, base_url='unix://var/run/docker.sock'):
        self.client = Client(base_url=base_url)

    def remove_image(self, *args, **kwargs):
        self.client.remove_image(*args, **kwargs)

    def add_image_node(self, image, image_id, parent=''):
        is_dangling = image_id in self.dangling

        node = "%s (%s)" % (image[u'RepoTags'], image[u'Id'])

        if parent == '':
            self.image_tree.create_node(node, image_id, parent='/',
                                        data={u'image': image, u'Dangling': is_dangling})
        else:
            self.image_tree.create_node(node, image_id, parent=parent,
                                        data={u'image': image, u'Dangling': is_dangling})

        if image[u'Id'] in self.pending:
            for node in self.pending[image[u'Id']]:
                self.add_image_node(node[0], node[1], parent=image[u'Id'])

    def prepare_image_tree(self):
        self.image_tree = Tree()
        self.image_tree.create_node('', '/')
        self.pending = dict()
        dangling_images = self.client.images(filters={u'dangling': True})
        self.dangling = []
        for image in dangling_images:
            self.dangling.append(image[u'Id'])
        for image in self.client.images(all=True):
            if u'ParentId' in image and image[u'ParentId'] != '':
                if self.image_tree.contains(image[u'ParentId']) or image[u'ParentId'] == '':
                    self.add_image_node(image, image[u'Id'], parent=image[u'ParentId'])
                else:
                    if image[u'ParentId'] not in self.pending:
                        self.pending[image[u'ParentId']] = []
                    self.pending[image[u'ParentId']].append((image, image[u'Id']))
            else:
                self.add_image_node(image, image[u'Id'])

    def get_image_tree(self):
        self.prepare_image_tree()
        return self.image_tree


def main():
    ExampleTreeBrowser(DockerIf()).main()


if __name__ == "__main__":
    main()
