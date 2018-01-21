import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("-q","--quiet",help="only print errors to console log",action="store_true")
parser.add_argument("-d","--debug",help="print debug messages to console log",action="store_true")
parser.add_argument("--helpkivy",help="Print Kivy's built-in argument list",action="store_true")

def main_app():
    # since kivy has it's own argparsing, it's necessary to do some argv mangling
    args,unknown = parser.parse_known_args()
    sys.argv[1:] = unknown
    # if --helpkivy is passed, print Kivy's argument list
    if args.helpkivy:
        sys.argv.append('-h')
    # if -d/--debug is passed, use Kivy's -d flag
    if args.debug:
        sys.argv.append('-d')
    from kivy.config import Config
    if args.quiet:
        Config.set('kivy','log_level','warning')
    from kmpc import kmpcapp
    kmpcapp.KmpcApp(args).run()

def manager_app():
    # since kivy has it's own argparsing, it's necessary to do some argv mangling
    args,unknown = parser.parse_known_args()
    sys.argv[1:] = unknown
    # if --helpkivy is passed, print Kivy's argument list
    if args.helpkivy:
        sys.argv.append('-h')
    # if -d/--debug is passed, use Kivy's -d flag
    if args.debug:
        sys.argv.append('-d')
    from kivy.config import Config
    if args.quiet:
        Config.set('kivy','log_level','warning')
    from kmpc import kmpcmanager
    kmpcmanager.ManagerApp(args).run()
