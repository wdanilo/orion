#  _________________________________________________________________________
#
#  PyUtilib: A Python utility library.
#  Copyright (c) 2008 Sandia Corporation.
#  This software is distributed under the BSD License.
#  Under the terms of Contract DE-AC04-94AL85000 with Sandia Corporation,
#  the U.S. Government retains certain rights in this software.
#  _________________________________________________________________________


from xml.dom import Node
import xml

def get_xml_text(node):
    nodetext = ""
    for child in node.childNodes:
        if child.nodeType == Node.TEXT_NODE:
            nodetext = nodetext + child.nodeValue
    nodetext = str(nodetext)
    return nodetext.strip()


_identitymap = "".join([chr(n) for n in xrange(256)])
_delchars = _identitymap[:9] + chr(11) + chr(12) + _identitymap[14:31] + chr(124)

def escape(s):
    """Replace special characters '&', "'", '<', '>' and '"' by XML entities."""
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    s = s.translate(_identitymap, _delchars)
    return s
