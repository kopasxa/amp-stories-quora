from lib2to3.pgen2 import driver
from os import mkdir
import os
import pickle
import re
import time
from urllib import request
import config
from bs4 import BeautifulSoup as bs
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from requests_html import HTMLSession
from assets.page_builder import PageBuilder

class Parse:
    def __init__(self):
        from selenium import webdriver

        self.search_url = config.initial_query_for_search
        #self.options = webdriver.ChromeOptions()
        self.options = webdriver.FirefoxOptions()
        self.articles = []

        self.options.add_argument("--log-level=OFF")
        try:
            pass#self.options.add_argument('--headless') # for firefox on server
        except:
            pass # for chrome of debug mode

        #self.driver = webdriver.Chrome(options=self.options, executable_path="assets/chromedriver.exe")
        self.driver = webdriver.Firefox(options=self.options)

    def search(self, filter):
        self.driver.get(url=self.search_url)

        wait = WebDriverWait(self.driver, 5)
        try:
            wait.until(lambda x: x.find_element(By.CSS_SELECTOR, "div#mainContent"))
        except:
            raise Exception("Timeout error")

        time.sleep(3)
        
        while True:
            if self.driver.find_element(By.CSS_SELECTOR, "#mainContent > div > div > div:nth-child(2) > div:last-child").text == "":
                time.sleep(1)
                self.driver.execute_script("window.scrollTo(0, document.querySelector('#root').scrollHeight);")
            else:
                break

        result = self.get_articles_by_filter(self.driver.page_source, filter)
        self.articles += result
        return result

    def get_articles_by_filter(self, page, filter):
        soup = bs(page, 'html.parser')
        arcticles_list = []
        articles = soup.select('div.qu-borderColor--raised:nth-child(1) div:nth-child(2) div span.q-text a.qu-display--block')

        for idx, article in enumerate(articles):
            arcticles_list.append(article['href'])

        return arcticles_list

    def find_poster_path(self, page, title):
        soup = bs(page, 'html.parser')
        try:
            reg = re.compile('[^0-9\s^a-zA-Z]')
            title = reg.sub('', title)

            pathDir = f'{config.path_to_stories}/{"_".join(title.split(" ")).split(".")[0]}'
            path = f'{config.path_to_stories}/{"_".join(title.split(" ")).split(".")[0]}/img/poster.jpg'
            pathToImage = './img/poster.jpg'
            result = soup.find('div', {'class': 'content-lede-image'}).find('img')['src'].split("?")[0]

            if result in "https://hips.hearstapps.com/hmg-prod.s3.amazonaws.com/images/legacy-fre-image-placeholder-1648561128.png":
                return None

            try:
                if result != None:
                    if not os.path.exists(pathDir):
                        mkdir(pathDir)
                        mkdir(pathDir + "/img")
            except Exception as e:
                pass
                #print(e)

            if not os.path.exists(path):
                request.urlretrieve(result, path)

            return pathToImage
        except Exception as e:
            #print(e)
            return None

    def find_stories(self, page, title):
        reg = re.compile('[^0-9\s^a-zA-Z]')
        title = reg.sub('', title)

        soup = bs(page, 'html.parser')
        stories = []
        try:
            container = soup.find('div', {'class': 'content-container'})
            container_type = container.attrs['class'][1]

            for el in container.find_all('p'):
                if not len(el.text) > 0:
                    el.extract()

            for el in container.find_all('div'):
                if not len(el.text) > 0:
                    el.extract()

            if container_type == "standard-container":
                images = container.select('.article-body-content h2 ~ div.embed img')
                headers = container.select('.article-body-content hr + .body-h2, div.embed + .body-h2, .body-text + .accordion ~ .body-h2')
                links = container.select('.article-body-content h2 ~ div.embed a')

                if len(images) < len(headers):
                    headers = headers[:-(len(headers) - len(images))]
                
            elif container_type == 'listicle-container':
                images = container.select('.listicle-body-content .listicle-slide-product .listicle-slide-media-outer img')
                headers = container.select('.listicle-body-content .listicle-slide-product .listicle-slide-hed-text')
                links = container.select('.listicle-body-content .listicle-slide-product .listicle-slide-media-outer a')
            else:
                return None

            if len(images) == len(headers) and len(images) == len(links):
                for idx, story in enumerate(images):
                    pathToImage = f'./img/{idx}.jpg'
                    path = f'{config.path_to_stories}/{"_".join(title.split(" ")).split(".")[0]}/img/{idx}.jpg'
                    result = story['data-src'].split("?")[0]
                    
                    if not os.path.exists(path):
                        request.urlretrieve(result, path)

                    stories.append({'header': headers[idx].text, 'image': pathToImage, 'link': links[idx]['href']})

            return stories

        except Exception as e:
            print(e)
            return None

    def register_sitemap(self, url):
        import xml.etree.ElementTree as ET
        from datetime import datetime

        mytree = ET.parse(f'{config.path_root}/sitemap.xml')
        myroot = mytree.getroot()
        
        el = ET.SubElement(myroot, 'url')
        ET.SubElement(el, 'loc').text = url
        ET.SubElement(el, 'lastmod').text = datetime.strftime(datetime.now(), '%Y-%m-%d')

        ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")

        mytree.write(f'{config.path_root}/sitemap.xml')

    def run_page_builder(self, pages):
        for url in pages:
            session = HTMLSession()
            res = session.get('https://www.cosmopolitan.com' + url)
            article_soup = bs(res.text, 'html.parser')
            content_header = article_soup.find('div', {'class': 'content-header-inner'})
            content_header_title = content_header.find('h1', {'class': 'content-hed'}).text
            content_header_description = content_header.find('div', {'class': 'content-dek'}).text
            content_poster = self.find_poster_path(res.text, content_header_title)
            stories = self.find_stories(res.text, content_header_title)
            #print(content_poster)

            if content_poster != None and stories != None:
                build = PageBuilder()
                build.set_page_title(content_header_title)
                build.set_page_poster(content_poster)

                build.build_start_page()
                build.build_page_head()
                build.build_story_start(config.publisher, config.publisher_logo)
                build.build_story("", "", content_header_description, story_type="first_story")

                for story in stories:
                    build.build_story(story['image'], story['header'], "", story['link'])

                build.build_end_page()

                reg = re.compile('[^0-9\s^a-zA-Z]')
                title = reg.sub('', content_header_title)
                path = f'{config.path_to_stories}/{"_".join(title.split(" ")).split(".")[0]}/index'

                build.build_page(path)

                self.register_sitemap(f'{config.my_domain}{path.split(config.path_root)[1]}.html')

                time.sleep(config.timeout_page_generate * 60)

    def __del__(self):
        time.sleep(100)
        self.driver.quit()