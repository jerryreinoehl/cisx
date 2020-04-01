#!/usr/bin/env python3
################################################################################
# update.py
################################################################################


import distutils.dir_util
import os
import shutil
import requests
import zipfile


ARCHIVE_URL = 'https://github.com/jerryreinoehl/cisx/archive/master.zip'


def main():
    print('fetching: ', ARCHIVE_URL)
    response = requests.get(ARCHIVE_URL)

    if response.status_code != 200:
        print(f'response returned with status {response.status_code}')
        exit(1)

    with open('tmp', 'wb') as zip_file:
        zip_file.write(response.content)

    with zipfile.ZipFile('tmp', 'r') as zip_file:
        archive_name = zip_file.infolist()[0].filename
        zip_file.extractall()

    for file in os.listdir(archive_name):
        filename = os.path.join(archive_name, file)
        print(f'extracting: {filename}')

    distutils.dir_util.copy_tree(archive_name, './')

    os.remove('tmp')
    distutils.dir_util.remove_tree(archive_name)

if __name__ == '__main__':
    main()
