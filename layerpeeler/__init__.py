from __future__ import print_function
from docker import Client
from treelib import Node, Tree
import sys
import urwid


class ExampleTreeWidget(urwid.TreeWidget):
    def __init__(self, node):
        self.__super.__init__(node)
        add_widget(node.get_value().get_node(node.get_value().root).identifier, self)
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

    """ Display widget for leaf nodes """
    def get_display_text(self):
        tree = self.get_node().get_value()
        tag = tree.get_node(tree.root).tag
        data = tree.get_node(tree.root).data
        if data is not None and data[u'Dangling']:
            return ('flag', tag)
        else:
            return tag


class ExampleNode(urwid.TreeNode):
    """ Data storage object for leaf nodes """
    def load_widget(self):
        return ExampleTreeWidget(self)


class ExampleParentNode(urwid.ParentNode):
    """ Data storage object for interior/parent nodes """
    def load_widget(self):
        return ExampleTreeWidget(self)

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
        return childclass(childdata, parent=self, key=key, depth=childdepth)


class ExampleTreeBrowser:
    palette = [
        ('body', 'light gray', 'black'),
        ('focus', 'light gray', 'dark blue', 'standout'),
        ('head', 'yellow', 'black', 'standout'),
        ('foot', 'black', 'dark blue'),
        ('key', 'light cyan', 'dark blue','underline'),
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

    def __init__(self, data=None):
        self.topnode = ExampleParentNode(data)
        self.listbox = urwid.TreeListBox(urwid.TreeWalker(self.topnode))
        self.listbox.offset_rows = 0
        self.header = urwid.Text( "Docker Images" )
        self.footer = urwid.AttrWrap( urwid.Text( self.footer_text ),
            'foot')
        self.view = urwid.Frame(
            urwid.AttrWrap( self.listbox, 'body' ),
            header=urwid.AttrWrap(self.header, 'head' ),
            footer=self.footer )

    def main(self):
        """Run the program."""

        self.loop = urwid.MainLoop(self.view, self.palette,
            unhandled_input=self.unhandled_input)
        self.loop.run()

    def unhandled_input(self, k):
        if k in ('q','Q'):
            raise urwid.ExitMainLoop()


class DockerTree:
    def __init__(self):
        self.client = Client(base_url='unix://var/run/docker.sock')
        self.tree = Tree()
        self.tree.create_node('', '/')
        self.pending = dict()
        dangling_images = self.client.images(filters={u'dangling': True})
        self.dangling = []
        for image in dangling_images:
            self.dangling.append(image[u'Id'])
        for image in self.client.images(all=True):
            if u'ParentId' in image and image[u'ParentId'] != '':
                if self.tree.contains(image[u'ParentId']) or image[u'ParentId'] == '':
                    self.add_node(image, image[u'Id'], parent=image[u'ParentId'])
                else:
                    if image[u'ParentId'] not in self.pending:
                        self.pending[image[u'ParentId']] = []
                    self.pending[image[u'ParentId']].append((image, image[u'Id']))
            else:
                self.add_node(image, image[u'Id'])

    def add_node(self, image, image_id, parent=''):
        is_dangling = image_id in self.dangling

        node="%s (%s)" % (image[u'RepoTags'], image[u'Id'])

        if parent == '':
            self.tree.create_node(node, image_id, parent='/', data={u'image': image, u'Dangling': is_dangling})
        else:
            self.tree.create_node(node, image_id, parent=parent, data={u'image': image, u'Dangling': is_dangling})

        if image[u'Id'] in self.pending:
            for node in self.pending[image[u'Id']]:
                self.add_node(node[0], node[1], parent=image[u'Id'])

    def get_tree(self):
        return self.tree


def main():
    sample = DockerTree().get_tree()
    ExampleTreeBrowser(sample).main()
    images = get_tagged_images()
    if len(images) > 0:
        print("You've chosen for deletion the following images:")
        for image in images:
            im = image.get_node(image.root).data[u'image']
            print("%s (%s)" % (im[u'RepoTags'], im[u'Id']))
        s = ' '
        while s.lower() not in ['y', 'n', '']:
            s = raw_input("Proceed? [y/N] ")
        if s.lower() == 'y':
            for image in reversed(images):
                im = image.get_node(image.root).data[u'image']
                print("Removing image %s (%s)" % (im[u'RepoTags'], im[u'Id']))
                try:
                    Client(base_url='unix://var/run/docker.sock').remove_image(image=im[u'Id'])
                except:
                    print('FAILED')
                else:
                    print('OK')


#######
# global cache of widgets
_widget_cache = {}

def add_widget(image, widget):
    """Add the widget for a given path"""

    _widget_cache[image] = widget

def get_tagged_images():
    """Return a list of all filenames marked as flagged."""

    l = []
    for w in _widget_cache.values():
        if w.tagged:
            l.append(w.get_node().get_value())
    return l


if __name__=="__main__":
    main()
