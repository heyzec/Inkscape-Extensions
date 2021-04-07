#!/usr/bin/env python3
import os
import sys
import re
import subprocess

from BaseExtension import BaseExtension

# For linting purposes
from argparse import ArgumentParser

"""If syntax error occurs here, change inkscape interpreter to python3"""

"""I have yet to find a way for an extension to call another extension with parameters,
without GUI. This extension can be run as part of a standalone extension (using BaseExtension)
or imported for use by another extension. This workaround is done via the 'option' arg in
the 'custom_effect' function"""


def custom_effect(self: BaseExtension):
    """Note: The init of the BaseExtension class will set its 'custom_effect' attr
    to this function. Hence, the self arg is of type BaseExtension."""


    selected = self.svg.selected
    root = self.document.getroot()
    actions_list = []

    proc = subprocess.run("inkscape --verb-list | grep -oP '^.+?(?=:)'",
                            shell=True,
                            capture_output=True)
    verb_list = proc.stdout.decode().split('\n')

    proc = subprocess.run("inkscape --action-list | grep -oP '^.+?(?= *:)'",
                            shell=True,
                            capture_output=True)
    action_list = proc.stdout.decode().split('\n')


    self.options.dry_run = True if self.options.dry_run == 'true' else False
    if self.options.dry_run:
        self.msg("Root:", self.show(self.find(root, '/*')))
        self.msg("Selected:", self.show(self.find(selected, '/*')))
        self.msg()

    def verify_action(action):
        if ':' in action:
            action = action.split(':')[0]
        if action not in verb_list + action_list:
            raise ValueError(action)

    def select_do_individually(objs, actions):
        for obj in objs:
            actions_list.append("EditDeselect")
            actions_list.append("select-by-id:" + obj.get_id())
            if isinstance(actions, str):
                actions = [actions]
            for action in actions:
                verify_action(action)
                actions_list.append(action)

    def select_do_on_all(objs, actions):
        for obj in objs:
            actions_list.append("select-by-id:" + obj.get_id())

        if isinstance(actions, str):
            actions = [actions]
        for action in actions:
            verify_action(action)
            actions_list.append(action)
    effects = []
    try:
        if self.options.tab_effect is None:
            if self.options.effects is not None:
                self.options.tab_effect = 'Multi'
            elif self.options.effect1 is not None:
                self.options.tab_effect = 'Simple'

        if self.options.tab_effect == 'Simple':
            for attr in ('effect1', 'effect2', 'effect3'):
                e = getattr(self.options, attr)
                if e != None:
                    effects += [e.strip()]
                if effects == []:
                    raise ValueError
        elif self.options.tab_effect == 'Multi':
            if self.options.effects is None:
                raise ValueError
            for line in self.options.effects.split('\\n'):
                effects += [e.strip() for e in line.split(';') if e != '']
    except ValueError:
        self.msg("No effects inputted! Quitting...")
        sys.exit(0)

    if self.options.target == 'root':
        objects = self.find(root, self.options.xpath)
    elif self.options.target == 'selected':
        objects = self.find(selected, self.options.xpath)
    if objects == []:
        self.msg(f"No objects to apply on.")
        self.msg("Root:", self.show(root))
        self.msg("Selected:", self.show(selected))
        sys.exit(0)


    try:
        if self.options.mode == 'all':
            select_do_on_all(objects, effects)
        elif self.options.mode == 'indiv':
            select_do_individually(objects, effects)
    except ValueError as e:
        self.msg(f"'{e.args[0]}' is not a valid action or verb in inkscape.")
        sys.exit(1)

    return actions_list


def args_adder(arg_parser: ArgumentParser):

    arg_parser.add_argument("--target",
                                default='root',
                                help="Object to apply xpath find on")
    arg_parser.add_argument("--xpath",
                                default='/*',
                                help="For selection of objects")
    arg_parser.add_argument("--tab_main",
                                default=None)
    arg_parser.add_argument("--Simple",
                                default=None)
    arg_parser.add_argument("--Multi",
                                default=None)
    arg_parser.add_argument("--mode",
                                default="all",
                                help="Mode to apply effects on objects")
    arg_parser.add_argument("--tab_effect",
                                default=None)
    for arg in ('effect1', 'effect2', 'effect3', 'effects'):
        arg_parser.add_argument(f"--{arg}",
                                default=None,
                                help="Inkscape verb for path op")
    arg_parser.add_argument("--dry_run",
                                default='false')
    arg_parser.add_argument("--null_notebook",
                                default='false')


BatchTask = BaseExtension(custom_effect, args_adder=args_adder)
if __name__ == '__main__':
    BatchTask.run()




# Namespace(Multi='SelectionDiff', Simple='SelectionDiff', dry_run='false', effect1='SelectionBreakApart', effect2=None, effect3=None, effects=None, ids=['image25'], input_file='/tmp/ink_ext_XXXXXX.svgIDCKU0', mode='all', null='null', output=<_io.BufferedWriter name='<stdout>'>, selected_nodes=[], tab_effect='Simple', tab_main='Options', target='root', xpath='/*')


# Namespace(Multi=None, Simple=None, dry_run='false', effect1='SelectionDelete', effect2=None, effect3=None, effects=None, mode='all', null='false', tab_effect=None, tab_main=None, target='root', xpath='/*')
