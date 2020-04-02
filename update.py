#!/usr/bin/env python3
################################################################################
# update.py
#
# Fetches files from git repository zip archive and extracts them to current
# directory.
#
# usage: python3 update.py
#
################################################################################


import distutils.dir_util
import os
import urllib.error
import urllib.request
import zipfile


# Location of git repository.
ARCHIVE_URL = 'https://github.com/jerryreinoehl/cisx/archive/master.zi'


def main():
    print('fetching: ', ARCHIVE_URL)

    # fetch data from archive url
    try:
        response = urllib.request.urlopen(ARCHIVE_URL)
    except urllib.error.HTTPError as http_error:
        print(f'response returned with status {http_error.code}')
        exit(1)

    # ensure 200 OK status
    if response.code != 200:
        print(f'response returned with status {response.code}')
        exit(1)

    # write response content to zip file
    with open('tmp', 'wb') as zip_file:
        zip_file.write(response.read())

    # extract zip file to current directory
    with zipfile.ZipFile('tmp', 'r') as zip_file:
        archive_name = zip_file.infolist()[0].filename
        zip_file.extractall()

    walk_dir(archive_name, lambda file: print(f'extracting: {file}'))

    # copy or overwrite from archive files
    distutils.dir_util.copy_tree(archive_name, './')

    # remove temporary zip file and archive files
    os.remove('tmp')
    distutils.dir_util.remove_tree(archive_name)


# Recursively visits each file and directory within dir.
def walk_dir(dir, visit):
    if not os.path.exists(dir):
        return
    if not os.path.isdir(dir):
        return
    visit(dir)
    for file in os.listdir(dir):
        filename = os.path.join(dir, file)
        if os.path.isdir(filename):
            walk_dir(filename, visit)
        if os.path.isfile(filename):
            visit(filename)


if __name__ == '__main__':
    main()
