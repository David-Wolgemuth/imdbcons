###Dependencies

Requires **Python 2**.
*Pillow* and *imdb-pie* must be installed.  Both available with pip install.

###Usage

Script will set icons for all subdirectories within main directory.

`python imdbcons.py 'path-to-main-directory'`

If image is incorrect (due to misleading foldername / broad movie title) Find the hidden .imdb_id file within the movie's directory and set it to the correct imdb id found at imdb.com, then re-run the script.
