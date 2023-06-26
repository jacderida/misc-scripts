#!/usr/bin/env python

import os
import re
import subprocess
import sys

DVD_BASE_DIRECTORY_PATH = "/mnt/seagate-ext/9-11-archive/video/dvd2"

def select_dvd():
    result = subprocess.run(
        'ls {} | fzf'.format(DVD_BASE_DIRECTORY_PATH), stdout=subprocess.PIPE, shell=True)
    return result.stdout.decode().strip()

def extract_fields(filename):
    with open(filename, 'r') as file:
        data = file.read()
    
    title = re.search(r'Title: (.*)', data)
    released = re.search(r'Released: (.*)', data)
    imdb_url = re.search(r'IMDB: (.*)', data)
    rumble_url = re.search(r'Rumble: (.*)', data)
    description = re.search(r'Description:\n(.*?)(?=\nDVD Description:)', data, re.DOTALL)
    dvd_description = re.search(r'DVD Description:\n(.*?)(?=\nEncoded Feature Technical Detail)', data, re.DOTALL)

    return {
        'Title': title.group(1).strip() if title else None,
        'Released': released.group(1).strip() if released else None,
        'IMDB': imdb_url.group(1).strip() if imdb_url else None,
        'Rumble': rumble_url.group(1).strip() if rumble_url else None,
        'Description': description.group(1).strip() if description else None,
        'DVD Description': dvd_description.group(1).strip() if dvd_description else None
    }

def get_image_url(filename):
    with open(filename, 'r') as file:
        for line in file:
            if 'front-small.jpg' in line:
                return line.strip()
    return None

def build_post(image_url, fields):
    post = f"[B][I][SIZE=17px]{fields['Title']}[/SIZE][/I][/B]\n"
    post += f"[IMG]{image_url}[/IMG]\n"
    post += f"Released: {fields['Released']}\n"
    post += f"[URL='{fields['IMDB']}']IMDB[/URL]\n"
    post += f"[URL unfurl=\"true\"]{fields['Rumble']}[/URL]\n\n"
    post += fields['Description']
    post += "\n"
    post += "Description from the DVD:\n"
    post += "[quote]\n"
    post += fields['DVD Description']
    post += "\n"
    post += "[/quote]\n"
    return post

def main():
    selected_dvd = select_dvd()
    dvd_path = os.path.join(DVD_BASE_DIRECTORY_PATH, selected_dvd)
    dvd_readme_path = os.path.join(dvd_path, 'README')
    image_links_path = os.path.join(dvd_path, 'images', 'links.txt')
    image_url = get_image_url(image_links_path)
    fields = extract_fields(dvd_readme_path)
    post = build_post(image_url, fields)
    print(post)

if __name__ == "__main__":
    sys.exit(main())
