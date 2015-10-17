#!/usr/bin/env python

try:
    from imdbpie import Imdb, Imdb
    from imdbpie.exceptions import HTTPError
    from PIL import Image
except ImportError:
    print '\nError: Modules "imdb-pie" and "Pillow" must be Installed\n'
    quit()
from urllib import urlretrieve
import os
import shutil
import sys

reload(sys)
sys.setdefaultencoding('utf8')

TEMP_DIR = 'temp_imdbcon'
TEMP_JPG = os.path.join(TEMP_DIR, 'temp_image.jpg')
TEMP_PNG = os.path.join(TEMP_DIR, 'temp_image.png')
EMPTY_PNG = os.path.join(TEMP_DIR, 'temp_empty_square_png.png')
MAGIC_SCRIPT = os.path.join(TEMP_DIR, 'set_icon_magic_temp.py')
ACCEPTED_EXTENSIONS = (
    'webm', 'mkv', 'flv', 'avi', 'wmv', 'mp4',
    'mpg', 'mp2', 'mpeg', 'mpe', 'mpv', 'm4v'
)

MOVIE_DICT = {
    'path': '',
    'title': '',
    'imdb_id': None,
    'imdb_obj': None,
    'duplicates': []
}

MAGIC_SCRIPT_STRING = """
import Cocoa
import sys

Cocoa.NSWorkspace.sharedWorkspace().setIcon_forFile_options_(
    Cocoa.NSImage.alloc().initWithContentsOfFile_(
        sys.argv[1].decode('utf-8')
    ),
    sys.argv[2].decode('utf-8'), 0
) or sys.exit("Unable to set file icon")
"""

PROCESSES = {
    'download': 'Downloading cover %s from IMDB.',
    'resize': 'Resizing cover to %s.',
    'square': 'Pasting cover to square PNG.',
    'set_icon': 'Setting icon to directory.',
    'temp': 'Creating temporary files.',
    'clean': 'Cleaning temporary files.',
    'search': 'Searching IMDB for title.',
    'complete': 'All processes are complete.',
}

ARGV_EXAMPLES = {
    '-m': {
        'use': 'Set icons for all sub-folders within main movie folder',
        'ex': 'path/to/Movies',
    },
    '-a': {
        'use': 'Set icons for ALL files and folders under main movie folder',
        'ex': 'path/to/Movies',
    },
    '-s': {
        'use': 'Set icon for single folder/file',
        'ex': 'path/to/Inception',
    },
    '-id': {
        'use': 'Set icon for folder/file with a vague title based on IMDB id',
        'ex': 'tt0060153 path/to/Batman',
    }
}


class Parser:
    def __init__(self):
        self.tag = ''
        self.arg1 = ''
        self.arg2 = ''
        self.valid = True
        self.get_args()
        self.parsed = self.tag, self.arg1, self.arg2

    def show_examples(self):
        self.valid = False
        print ''
        for key in ARGV_EXAMPLES:
            use = ARGV_EXAMPLES[key]['use']
            ex = ARGV_EXAMPLES[key]['ex']
            print '\t%s :\t%s\n\t\t\t%s %s\n' % (key, use, key, ex)

    def get_args(self):
        try:
            self.tag = sys.argv[1]
        except IndexError:
            self.show_examples()
            return
        if self.tag not in ARGV_EXAMPLES:
            self.show_examples()
            return
        try:
            self.arg1 = sys.argv[2]
        except IndexError:
            self.show_examples()
            return
        if self.tag == '-id':
            try:
                self.arg2 = sys.argv[3]
            except IndexError:
                self.show_examples()
                return



class Display:
    def __init__(self):
        self.bar_width = .1  # multiplied by 100
        self.total_processes = 0  # int for number of processes
        self.completed_processes = 0
        self.current_title = ''
        self.progress_bar = ''
        self.errors_caught = []

    def update_progress_bar(self):
        """Update self.progress_bar string based on percentage"""
        if not self.total_processes:
            return
        percent = (100 * self.completed_processes) / self.total_processes
        filled = int(percent * self.bar_width)
        unfilled = int((100 * self.bar_width) - filled)
        self.progress_bar = '  [%s%s] - %s%%' % (filled * '#', unfilled * '_', percent)

    def update_current_process(self, process):
        """Print self.current_process and self.progress_bar"""
        self.update_progress_bar()
        t = self.current_title if len(self.current_title) < 20 \
            else self.current_title[:17] + '...'
        p = process if len(process) < 30 \
            else process[:27] + '...'
        message = '%s || %s: %s\r' % (self.progress_bar, t, p)
        print ' ' * 78 + '\r',
        print message,
        sys.stdout.flush()


class IMDBcon:
    def __init__(self):
        self.parser = Parser()
        self.directory = ''
        self.imdb = Imdb()
        self.cover_size = 214, 317
        self.square_size = 317, 317
        self.current = MOVIE_DICT
        self.all_files = []
        self.display = Display()

    def update_display(self, process, args=None):
        """Send process to self.display to print to screen"""
        if args:
            process = PROCESSES[process] % args
        else:
            process = PROCESSES[process]
        self.display.update_current_process(process)

    def make_empty_square(self):
        """Make transparent .png image"""
        image = Image.new('RGBA', self.square_size, (0, 0, 0, 0))
        image.save(EMPTY_PNG, 'PNG')

    def make_magic_script(self):
        """Make temporary magic 'set_icon.py' script"""
        with open(MAGIC_SCRIPT, 'w') as script:
            script.write(MAGIC_SCRIPT_STRING)

    def make_temp_files(self):
        """Make temporary files"""
        if os.path.isdir(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
        os.mkdir(TEMP_DIR)
        self.make_empty_square()
        self.make_magic_script()

    def remove_temp_dir(self):
        """Remove temporary directory"""
        self.display.current_title = ''
        self.update_display('clean')
        shutil.rmtree(TEMP_DIR)

    def set_current(self, dict_item=None, path=''):
        """Set self.current 'title' and 'path'"""
        if dict_item:
            self.current = dict_item
        elif path:
            self.current['path'] = path
            self.current['title'] = os.path.splitext(os.path.basename(path))[0]
        self.display.current_title = self.current['title']

    def set_id(self, imdb_id):
        if os.path.isdir(self.current['path']):
            id_path = os.path.join(self.current['path'], '.imdb_id')
            with open(id_path, 'w') as id_file:
                id_file.write(imdb_id)
        self.current['imdb_id'] = imdb_id

    def get_current_title(self):
        """Set self.current.imdb to Imdb Title object"""
        self.update_display('search')
        imdb_id = os.path.join(self.current['path'], '.imdb_id')
        # User can use preset imdb_id for full accuracy
        if self.current['imdb_id']:
            try:
                self.current['imdb_obj'] = self.imdb.get_title_by_id(self.current['imdb_id'])
            except HTTPError:
                error = 'Bad IMDB id for "%s" (%s)' % (
                    self.current['title'], self.current['imdb_id'])
                self.display.errors_caught.append(error)
                return False
        elif os.path.isfile(imdb_id):
            try:
                with open(imdb_id) as id_file:
                    self.current['imdb_obj'] = self.imdb.get_title_by_id(
                        ''.join(id_file.read().split()))
            except HTTPError:
                error = 'Bad IMDB id for "%s"' % self.current['title']
                self.display.errors_caught.append(error)
                return False
        else:
            try:
                titles = self.imdb.search_for_title(self.current['title'])
                temp = titles[0]  # Not an Imdb Title object
                self.current['imdb_obj'] = self.imdb.get_title_by_id(temp['imdb_id'])
                if os.path.isdir(self.current['path']):
                    with open(imdb_id, 'w') as id_file:
                        id_file.write(temp['imdb_id'])
            except IndexError:
                error = 'No Titles Found for "%s"' % self.current['title']
                self.display.errors_caught.append(error)
                return False
        if self.current['imdb_obj'].cover_url:
            return True
        else:
            error = 'No Cover Image Found for "%s"' % self.current['title']
            self.display.errors_caught.append(error)
            return False

    def retrieve_cover(self):
        """Download .jpg cover file from IMDB"""
        url = self.current['imdb_obj'].cover_url
        self.update_display('download', url)
        urlretrieve(url, TEMP_JPG)

    def resize_icon(self):
        """Set .jpg cover to self.cover_size"""
        self.update_display('resize', str(self.cover_size))
        image = Image.open(TEMP_JPG)
        resized = image.resize(self.cover_size, Image.ANTIALIAS)
        resized.save(TEMP_JPG)

    def square_icon(self):
        """Convert .jpg cover to .png squared cover"""
        self.update_display('square')
        background = Image.open(EMPTY_PNG)
        cover = Image.open(TEMP_JPG)
        offset = (50, 0)
        background.paste(cover, offset)
        background.save(TEMP_PNG)
        os.remove(TEMP_JPG)

    def set_icon_magic(self):
        """Run 'set_icon.py' script"""
        self.update_display('set_icon')
        os.system('python2.6 %s "%s" "%s"' % (MAGIC_SCRIPT, TEMP_PNG, self.current['path']))

    def set_icon(self):
        """Set directory icon to matching IMDB cover image"""
        if not self.get_current_title():
            return
        self.retrieve_cover()
        self.resize_icon()
        self.square_icon()
        self.set_icon_magic()
        for item in self.current['duplicates']:
            self.set_current(dict_item=item)
            self.set_icon_magic()
        os.remove(TEMP_PNG)

    def exit_message(self):
        """Display exit message along with any errors"""
        self.display.update_current_process('')
        print(PROCESSES['complete'])
        if self.display.errors_caught:
            for error in self.display.errors_caught:
                print(error)
        else:
            print('No Errors.')
        print

    def is_duplicate(self, item):
        for existing in self.all_files:
            if item['title'] == existing['title']:
                existing['duplicates'].append(item)
                return True
        return False

    def find_all(self):
        """Get list of all subdirectories and their files in directory"""
        for root, dirs, files in os.walk(self.directory):
            for directory in dirs:
                item = {
                    'path': os.path.join(root, directory),
                    'title': directory,
                    'imdb_id': None,
                    'imdb_obj': None,
                    'duplicates': []
                }
                if not self.is_duplicate(item):
                    self.all_files.append(item)
            if not self.parser.tag == '-a':
                continue
            for filename in files:
                split = os.path.splitext(filename)
                title, ext = split
                if ext[1:] not in ACCEPTED_EXTENSIONS:
                    continue
                item = {
                    'path': os.path.join(root, filename),
                    'title': title,
                    'imdb_id': None,
                    'duplicates': []
                }
                if not self.is_duplicate(item):
                    self.all_files.append(item)
        self.display.total_processes = len(self.all_files)

    def set_icons(self):
        """Set icons for all sub-directories in directory"""
        self.find_all()
        for item in self.all_files:
            self.set_current(dict_item=item)
            self.set_icon()
            self.display.completed_processes += 1

    def run(self):
        if not self.parser.valid:
            return
        tag, arg1, arg2 = self.parser.parsed
        self.make_temp_files()
        print ''
        if tag in ('-m', '-a'):
            self.directory = arg1
            self.set_icons()
        if tag == '-s':
            self.set_current(path=arg1)
            self.set_icon()
        if tag == '-id':
            self.set_current(path=arg2)
            self.set_id(arg1)
            self.set_icon()
        self.remove_temp_dir()
        self.exit_message()


if __name__ == '__main__':
    imdbcon = IMDBcon()
    imdbcon.run()
