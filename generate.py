#!/usr/bin/env python
import glob
import os
import shutil
import sys
import codecs
import urllib2
from optparse import OptionParser

import settings


# Import vendor lib.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'vendor'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'vendor', 'jinja2'))


import jinja2

import helpers
from dotlang.translate import translate


ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader([
        os.path.join(settings.ROOT, 'templates')
    ]), extensions=[])
# Hook up template filters.
helpers.load_filters(ENV)


optparser = OptionParser(usage='%prog --output-dir=/tmp/path/example')
optparser.add_option("--output-dir", action="store", dest="output_path",
                     help="Specify the output directory")
optparser.add_option('-f', '--force', action='store_true', dest='force',
                     default=False, help='Delete output dir if it exists.')
optparser.add_option('--nowarn', action='store_false', dest='warn',
                     default=True, help=("Don't warn if unknown L10n strings "
                                         "are encountered"))
optparser.add_option('-v', '--version', action='store', dest='version',
                    default=settings.BUILD_VERSION,
                    help="Version to generate. Accepts 'passive' or 'urgent'")

(options, args) = optparser.parse_args()

OUTPUT_PATH = (options.output_path if options.output_path else
                os.path.join(settings.BUILD_ROOT, 'html'))


def copy_file(output_dir, fileName):
    """Helper function that copies a file to a new folder."""
    resource_path = os.path.split(settings.ROOT)[0]
    shutil.copyfile(os.path.join(resource_path, fileName),
                    os.path.join(output_dir, fileName))


def write_output(output_dir, filename, text):
    """Helper function that writes a string out to a file."""
    f = codecs.open(os.path.join(output_dir, filename), 'w', 'utf-8')
    f.write(text)
    f.close()


def main():
    """Function run when script is run from the command line."""
    templates = {
        'html': 'index.html',
        'mobile': 'mobile.html',
        'v4': 'v4.html'
    }

    # allow parameter to override settings build version
    if options.version not in ('passive', 'urgent'):
        options.version = settings.BUILD_VERSION

    if os.path.exists(OUTPUT_PATH):
        if not options.force:
            sys.stderr.write('Output path "%s" exists, please remove it or '
                             'run with --force to overwrite automatically.\n' % (
                                 OUTPUT_PATH))
            sys.exit(1)
        else:
            shutil.rmtree(OUTPUT_PATH)
    os.makedirs(OUTPUT_PATH)

    sys.stdout.write("Writing %s template to %s\n" % (options.version, OUTPUT_PATH))

    # Copy "root" files into output dir's root.
    for f in (glob.glob(os.path.join(settings.ROOT, 'root', '*')) +
              glob.glob(os.path.join(settings.ROOT, 'root', '.*'))):
        shutil.copy(f, OUTPUT_PATH)

    # Place static files into output dir.
    STATIC_PATH = os.path.join(OUTPUT_PATH, 'static')
    MOBILE_STATIC_PATH = os.path.join(STATIC_PATH, 'mobile')
    V4_STATIC_PATH = os.path.join(STATIC_PATH, 'v4')
    for folder in settings.STATIC_FOLDERS:
        folder_path = os.path.join(STATIC_PATH, folder)
        shutil.copytree(os.path.join(settings.ROOT, folder),
                        folder_path)

    for folder in settings.MOBILE_STATIC_FOLDERS:
        mobile_folder_path = os.path.join(MOBILE_STATIC_PATH, folder)
        shutil.copytree(os.path.join(settings.MOBILE_ROOT, folder),
                        mobile_folder_path)

    for folder in settings.V4_STATIC_FOLDERS:
        v4_folder_path = os.path.join(V4_STATIC_PATH, folder)
        shutil.copytree(os.path.join(settings.ROOT, folder),
                        v4_folder_path)

    for lang in settings.LANGS:
        # Make language dir, or symlink to fallback language
        LANG_PATH = os.path.join(OUTPUT_PATH, lang)
        MOBILE_LANG_PATH = os.path.join(LANG_PATH, 'mobile')
        V4_LANG_PATH = os.path.join(LANG_PATH, 'v4')
        if lang in settings.LANG_FALLBACK:
            os.symlink(settings.LANG_FALLBACK[lang], LANG_PATH)
            continue
        else:
            os.makedirs(LANG_PATH)
            os.makedirs(V4_LANG_PATH)
            if lang in settings.LANG_MOBILE_FALLBACK:
                MOBILE_FALLBACK_PATH = os.path.join(
                                        '..',
                                        settings.LANG_MOBILE_FALLBACK[lang],
                                        'mobile')
                os.symlink(MOBILE_FALLBACK_PATH, MOBILE_LANG_PATH)
            else:
                os.makedirs(MOBILE_LANG_PATH)

        # symlink desktop static folders into language dir
        for folder in settings.STATIC_FOLDERS:
            os.symlink(os.path.join(settings.STATIC_SYMLINK_PATH, folder),
                       os.path.join(LANG_PATH, folder))

        # symlink mobile static folders into language dir
        if lang not in settings.LANG_MOBILE_FALLBACK:
            for folder in settings.MOBILE_STATIC_FOLDERS:
                os.symlink(os.path.join(settings.MOBILE_STATIC_SYMLINK_PATH, folder),
                           os.path.join(LANG_PATH, 'mobile', folder))

        # symlink v4 static folders into language dir
        for folder in settings.V4_STATIC_FOLDERS:
            os.symlink(os.path.join(settings.V4_STATIC_SYMLINK_PATH, folder),
                       os.path.join(LANG_PATH, 'v4', folder))

        # Data to be passed to template
        data = {
            'LANG': lang,
            'DIR': 'rtl' if lang in settings.RTL_LANGS else 'ltr',
            'VERSION': options.version,
        }

        # Load _() translation shortcut for jinja templates and point it to dotlang.
        ENV.globals['_'] = lambda txt: translate(lang, txt, warn=options.warn)

        for platform, template in templates.iteritems():
            if platform == 'html':
                OUTPUT_LANG_PATH = LANG_PATH
            elif platform == 'v4':
                OUTPUT_LANG_PATH = os.path.join(LANG_PATH, 'v4')
            else:
                OUTPUT_LANG_PATH = os.path.join(LANG_PATH, 'mobile')
            tmpl = ENV.get_template(template)

            if platform =='mobile' and lang in settings.LANG_MOBILE_FALLBACK:
                continue
            write_output(OUTPUT_LANG_PATH, 'index.html', tmpl.render(data))

if __name__ == '__main__':
    main()
