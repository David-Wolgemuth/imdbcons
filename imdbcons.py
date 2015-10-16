#!/usr/bin/env python

from imdbpie import Imdb
from PIL import Image
from urllib import urlretrieve
import os
import shutil
import sys

TEMP_DIR = 'temp_imdbcon'
TEMP_JPG = os.path.join(TEMP_DIR, 'temp_image.jpg')
TEMP_PNG = os.path.join(TEMP_DIR, 'temp_image.png')
EMPTY_PNG = os.path.join(TEMP_DIR, 'temp_empty_square_png.png')
MAGIC_SCRIPT = os.path.join(TEMP_DIR, 'set_icon_magic_temp.py')

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
    def __init__(self, directory):
        self.directory = directory
        self.imdb = Imdb()
        self.cover_size = 214, 317
        self.square_size = 317, 317
        self.current = {
            'dir': '',
            'path': '',
            'imdb': None
        }
        self.subdirectories = []
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

    def set_current(self, directory):
        """Set self.current 'dir' and 'path'"""
        self.current['dir'] = directory
        self.current['path'] = os.path.join(self.directory, directory)
        self.display.current_title = directory

    def get_current_title(self):
        """Set self.current.imdb to Imdb Title object"""
        self.update_display('search')
        imdb_id = os.path.join(self.current['path'], '.imdb_id')
        # User can use preset imdb_id for full accuracy
        if os.path.isfile(imdb_id):
            try:
                with open(imdb_id) as id_file:
                    self.current['imdb'] = self.imdb.get_title_by_id(id_file.read())
            except:
                error = 'Bad IMDB id for "%s."' % self.current['dir']
                self.display.errors_caught.append(error)
        else:
            try:
                titles = self.imdb.search_for_title(self.current['dir'])
                temp = titles[0]  # Not an Imdb Title object
                self.current['imdb'] = self.imdb.get_title_by_id(temp['imdb_id'])
                with open(imdb_id, 'w') as id_file:
                    id_file.write(temp['imdb_id'])
            except IndexError:
                error = 'No Titles Found for "%s."' % self.current['dir']
                self.display.errors_caught.append(error)

    def retrieve_cover(self):
        """Download .jpg cover file from IMDB"""
        url = self.current['imdb'].cover_url
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
        os.remove(TEMP_PNG)

    def set_icon(self):
        """Set directory icon to matching IMDB cover image"""
        self.get_current_title()
        self.retrieve_cover()
        self.resize_icon()
        self.square_icon()
        self.set_icon_magic()

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

    def get_subdirectories(self):
        """Get list of all subdirectories in directory"""
        for item in os.listdir(self.directory):
            path = os.path.join(self.directory, item)
            if os.path.isdir(path):
                self.subdirectories.append(item)
        self.display.total_processes = len(self.subdirectories)

    def set_icons(self):
        """Set icons for all sub-directories in directory"""
        print
        self.make_temp_files()
        self.get_subdirectories()
        for subdirectory in self.subdirectories:
            self.set_current(subdirectory)
            self.set_icon()
            self.display.completed_processes += 1
        self.remove_temp_dir()
        self.exit_message()


if __name__ == '__main__':
    from sys import argv
    imdbcon = IMDBcon(argv[1])
    imdbcon.set_icons()
