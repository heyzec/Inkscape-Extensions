#!/usr/bin/env python3

# pylint: disable=too-many-ancestors

# standard library
import os
import sys
import re
import argparse
from shutil import copy2
# from subprocess import Popen, PIPE
# import time
# from lxml import etree

# local library
import inkex
from inkex.command import inkscape
from inkex.elements import _selected as selection

MIN_PYTHON_VERSION = (3, 6)  # Mainly for f-strings
if (sys.version_info.major, sys.version_info.minor) < (3, 6):
    inkex.Effect.msg(f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} or later required.")
    sys.exit(1)


class BaseExtension(inkex.Effect):
    """Custom class that makes creation of extensions easier.

    Users of this class need not worry about boilerplates, such as how to
    call inkscape via shell, and the management of tempfiles. Useful functions
    are also provided."""

    def __init__(self, custom_effect, args_adder=None):
        """Init base class.

        In a typical Inkscape extension that does not make use of BaseExtension,
        the effect is determined by the "effect" method of the extension class.
        This init function will take in a method, and run it in the "effect" method
        together with the other boilerplate.

        This init method takes in a function under the custom_effect argument.
        This function will handle the user's effects, minus the boilerplate. It
        has to return a list[str] object, with each str being a verb that inkscape
        can execute."""

        inkex.Effect.__init__(self)
        self.custom_effect = custom_effect

        self._msg = self.msg  # The old msg function provided by inkex (only accepts strings)
        def msg(*args, sep=' '):
            """Improved msg method, similar to Python's print"""
            self._msg(sep.join([str(arg) for arg in args]))
        self.msg = msg

        if args_adder is not None:
            args_adder(self.arg_parser)
            self.args_adder = args_adder




    def z_sort(self, alist):
        """Return new list sorted in document order (depth-first traversal)."""
        return list(self.z_iter(alist))


    def z_iter(self, alist):
        """Return iterator over ids in document order (depth-first traversal)."""
        id_list = list(alist)
        count = len(id_list)
        for element in self.document.getroot().iter():
            # element_id = element.get('id')
            # if element_id is not None and element_id in id_list:
            if element in alist:
                id_list.remove(element)
                yield element
                count -= 1
                if not count:
                    return

    @staticmethod
    def show(obj):
        def rep(obj):
            if hasattr(obj, 'get_id'):
                return f"{type(obj).__name__}({obj.get_id()})"
            return f"{type(obj).__name__}"


        if isinstance(obj, list):
            return ('[' +
                ', '.join([rep(child) for child in obj]) +
                ']')
        else:
            return rep(obj)


    def find(self, obj: any, xpath='/*', tb=None) -> list:
        """Returns a list of objects which satisfies xpath

        Args:
            obj (any): Parent object to recurse into. Examples include root, selected, or a group.
            xpath (str, optional): Defaults to '/*'.
            tb ([type], optional): Traceback object used only for debugging.

        Returns:
            list: [description]
        """

        tag_dict = {
            'l': 'Layer',
            'g': 'Group',
            'p': 'PathElement',
            'img': 'Image'
        }

        def debug(*msg, indent=0):
            if tb != None:
                self.msg(' ' * indent * 4 + ' '.join(str(i) for i in msg))

        def is_meta(obj):
            return type(obj).__name__ in (
                'Defs',
                'NamedView',
                'Metadata',
                'StyleElement'
                )


        def is_iterable(obj):
            return type(obj).__name__ in ('Group', 'Layer')

        def recurse(objects, cur_xpath, tb):
            objects = self.z_sort(objects)

            _, this_type, this_n, next_xpath = re.findall(r"""
                (//?)
                (\w+|\*)
                (?:\[(-?\d+(?::-?(?:\d+)?){0,2})\])? # Optional square brackets, -ve no. possible
                (.*)
                """, cur_xpath, re.VERBOSE)[0]

            only_immediate = _ != '//'


            if tb != None:
                indent = len(tb)
                debug('')
                debug(f"Traceback: {'->'.join(self.show(objects) for objects in tb)}", indent=indent)
                debug(f"Received: {self.show(objects)} to match {cur_xpath}", indent=indent)
            else:
                indent = None


            if this_n == '':
                this_n = None
            elif ':' in this_n:
                this_n = [int(n) if n != '' else None for n in this_n.split(':')]
            else:
                this_n = int(this_n)


            output = []
            to_recurse = []
            matching_types = []
            for obj in objects:
                match_type = this_type == '*' or type(obj).__name__ == tag_dict[this_type]

                if match_type:
                    matching_types += [obj]
                if not only_immediate:
                    to_recurse += [obj]


            try:
                if this_n is None:
                    matches = matching_types
                elif isinstance(this_n, int):
                    matches = [matching_types[this_n]]
                else:
                    assert this_n[1] is not None, "end must be specified (for now...)"
                    matches = matching_types[slice(*this_n)]
            except IndexError:
                self.msg("WARN: list index out of range")
                matches = []


            if only_immediate:
                if next_xpath == '':
                    debug(f"Desired last iteration reached: {self.show(matches)}", indent=indent)
                    output += matches
                else:
                    debug(f"Found partial match, will recurse: {self.show(matches)}", indent=indent)
                    to_recurse += matches
            else:
                debug(f"Will recurse: {matches}", indent=indent)
                output += matches



            for obj in to_recurse:
                if not is_iterable(obj):
                    # debug(self.show(obj) + " not iterable", indent=indent)
                    pass
                else:
                    # Assume iterable obj is not dict-like
                    # debug(self.show(obj) + " is iterable", indent=indent)
                    # debug(f"Before recurse: {self.show(x)}", indent=indent)
                    output += recurse([child for child in obj],
                            next_xpath if only_immediate else cur_xpath,
                            tb=tb + (obj,) if tb is not None else tb)

            return output

        if type(obj).__name__ in ('ElementList', 'SvgDocumentElement'):
            if tb is not None:
                tb += (obj,)
            if type(obj).__name__ == 'ElementList':
                obj = obj.values()
            return recurse([child for child in obj if not is_meta(child)],
                xpath, tb=tb)

        else:
            return recurse(obj, xpath, tb=tb)


    def effect(self):
        """Main entry point to process current document. Not to be called externally."""

        actions_list = self.custom_effect(self)

        if actions_list is None or actions_list == []:
            self.msg("No actions received. Perhaps you are calling inkex object methods?")
        elif isinstance(actions_list, list):
            tempfile = self.options.input_file + "-BaseExtension.svg"

            # prepare
            copy2(self.options.input_file, tempfile)

            actions_list.append("FileSave")
            actions_list.append("FileQuit")

            actions = ";".join(actions_list)
            inkscape(tempfile, "--with-gui", actions=actions)


            # finish up
            # replace current document with content of temp copy file
            self.document = inkex.load_svg(tempfile)
            # update self.svg
            self.svg = self.document.getroot()


        # Clean up tempfile
        try:
            os.remove(tempfile)
        except Exception:  # pylint: disable=broad-except
            pass

    def call(self, child, ext_options):
        """Used to call an extension from another extension"""

        old_options = self.options

        parser = argparse.ArgumentParser()
        child.args_adder(parser)
        self.options = parser.parse_args([])

        for k, v in ext_options.items():
            setattr(self.options, k, v)

        output = child.custom_effect(self)
        self.options = old_options

        return output
