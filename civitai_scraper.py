import os
from bs4 import BeautifulSoup
import json
from time import sleep
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
import re

# Path for user's firefox profile. Recommend creating a separate profile for scraping so you
# can browse the internet while the script is running
PROFILE_PATH = "C:\\Users\\your_user_acct\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\profile_name"

# The text file containing the list list of image URLs to download. One url per line.
URL_LIST_FILE = "civit_url_list.txt"

# Where to save the scraped images and tags
TARGET_DIRECTORY = "saved_image_folder"


def create_webdriver(profile_path):
    # Create a new webdriver from the firefox profile. Idk if this is the best way
    # to do this, but it works so I'm not complaining 
    options = Options()
    options.set_preference("profile", profile_path) 
    options.profile = profile_path

    driver = webdriver.Firefox(service=Service(), options=options)
    return driver


def render_html(driver, url):
    driver.get(url)

    # wait for everything to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "mantine-Text-root"))
    )
    sleep(2)

    # return the complete HTML after JavaScript execution
    src = driver.page_source
    return src


def clean_tag(tag):
    # removes excess whitespace and special characters (excluding hyphens and underscores)
    # also converst to lowercase for ease of filtering out crap tags in clean_prompt_text
    return re.sub(r"[^\w\s-]", "", tag.split(':')[0]).strip().lower()


def clean_prompt_text(prompt_text):
    # Junk tags to be removed (misc. image quality tags, lora triggers, etc.)
    junk_tags= [
        'masterpiece', 'best quality', 'good quality', 'amazing quality', 'absurdres', 'safe_pos', 'lora',
        'newest', 'original', 'hires', 'high resolution', 'perfect anatomy', 'uhd', 'break', 'uncensored',
        'g0thicpxl', 'negative_hand', 'epicnegative', 'expressiveh' 'epicphoto', 'gta', 
        ]
    
    junk_partials = [
        # Some junk tags have a lot of variants so we remove anything containing these substrings
        '4k', '8k', 'aesthetic', 'hires', 'quality', 'detailed', 'details', ' lora', 'artstation',
        'award winning', 'award-winning'
        ]

    # Remove random line breaks
    prompt_text = prompt_text.replace('\n', ', ')

    # Convert to list
    tag_ls = prompt_text.split(', ')

    # Remove pony quality tags
    tag_ls = [clean_tag(tag) for tag in tag_ls if not tag.lower().startswith('score')]
    # Remove junk tags
    tag_ls = [tag for tag in tag_ls if tag not in junk_tags]
    tag_ls = [tag for tag in tag_ls if not any([part in tag for part in junk_partials])]

    return ', '.join(tag_ls)


def parse_url_ls(fname):
    with open(fname) as f:
        url_ls = f.readlines()
    return set(url_ls)


def get_prompt(soup):
    # Find all candidate text root divs
    text_roots = soup.find_all("div", class_="mantine-Text-root")

    # Iterate through until we find the "Prompt" text, and the next one will be our actual prompt
    is_prompt_tag = False
    prompt_text = ''
    for tag in text_roots:
        if is_prompt_tag:
            prompt_text = tag.get_text(strip=True)
            break

        if tag.get_text(strip=True) == 'Prompt':
            is_prompt_tag = True
            continue

    return clean_prompt_text(prompt_text)


def get_civitai_tags(soup):
    # Get civitai auto-generaged tags
    tags = soup.find_all("div", class_="mantine-Badge-root")
    common_tags = []
    for tag in tags:
        try:
            tag_text = tag.find("a", class_="mantine-Text-root mantine-ljqvxq").get_text(strip=True)
            common_tags.append(tag_text)
        except:
            continue
    
    return common_tags


def main():
        profile_path = PROFILE_PATH
        url_ls = parse_url_ls(URL_LIST_FILE)        
        os.chdir(TARGET_DIRECTORY)

        f_list = os.listdir(TARGET_DIRECTORY)
        num_list = [f.split('.')[0] for f in f_list if f.endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        url_list_cleaned = [url[:-1] for url in url_ls if url.split("/")[-1][:-1] not in num_list]

        print(f"{len(url_ls)} URLs in list")
        print(f"{len(num_list)} files already downloaded. {len(url_list_cleaned)} remaining")

        driver = create_webdriver(PROFILE_PATH)
        for url in url_list_cleaned:
            print(f"Loading {url}")
            try:
                # Numerical URL part to be used as file name
                fname_num = ''.join(c for c in url.split("/")[-1] if c.isdigit())

                # Render the web page and return the full page source
                html_rendered = render_html(driver, url) # , options)

                # Read the page source to a bs4 soup
                soup = BeautifulSoup(html_rendered, 'html5lib')

                # Get the Image URL
                script_tag = soup.find('script', {'type': 'application/json'})
                json_data = json.loads(script_tag.string)
                img_data = json_data['props']['pageProps']['trpcState']['json']['queries'][0]['state']['data']    
                img_url = f"http://image.civitai.com/xG1nkqKTMzGDvpLrqFT7WA/{img_data['url']}/original=true,quality=90/{img_data['name']}.jpeg"

                # Create Image File
                img_response = requests.get(img_url)
                img_data = img_response.content
                print(f'Image data: Response {img_response.status_code}')
                if img_response.status_code not in (200, 201, 202):
                    print(img_response.reason)
                    continue

                file_type = img_url.split('.')[-1]
                fname_img = f"{fname_num}.{file_type}"
                print(fname_img)

                # Processing the soup
                common_tags = get_civitai_tags(soup)    
                prompt_text = get_prompt(soup)
                common_prompt = ', '.join(common_tags)

                # Combine auto-tags
                try:
                    with open(fname_img, 'wb') as handler:
                        handler.write(img_data)

                    with open(f'{fname_num}.txt', 'w') as f:
                        combined_text = f'{prompt_text}, {common_prompt}'
                        f.write(prompt_text + ', ' + common_prompt)

                        if len(combined_text) > 0:
                            f.write(prompt_text + ', ' + common_prompt)

                except Exception as e:
                    print(e)
                    
                sleep(2)

            except:
                continue
        
        driver.close()


if __name__ == '__main__':
    main()
