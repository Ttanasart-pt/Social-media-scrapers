from tqdm import tqdm
import time
import json
import requests
import os
from argparse import ArgumentParser

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException

def errorLog(error, pbar = None):
    errors.append(error)
    if(pbar and verbose):
        pbar.write(error)

def waitFor(type, _class = ''):
    try:
        _ = WebDriverWait(driver, 30)\
            .until(EC.presence_of_element_located((By.XPATH, f".//{type}[contains(@class,'{_class}')]" if _class != '' else f".//{type}")))
    finally:
        pass

def find(driver, type, _class = ''):
    try:
        e = driver.find_element(by = By.XPATH, value = f".//{type}[contains(@class,'{_class}')]" if _class != '' else f".//{type}")
        return e
    except NoSuchElementException:
        raise NoSuchElementException
    
def finds(driver, type, _class = ''):
    return driver.find_elements(by = By.XPATH, value = f".//{type}[contains(@class,'{_class}')]" if _class != '' else f".//{type}")

def scrapping():
    data = []
    for i in (pbar := tqdm(range(max_post))):
        pbar.set_description(f'  ├─ Total progress')
        waitFor('div', '_aatk _aatl')
        try:
            post_content = find(driver, 'article', '_aatb')
        except NoSuchElementException:
            errorLog(f'  ├─ x post {i} get post error')
            break
        
        post_file = f"{opath}/media/{i:03}"
        
        if(len(finds(post_content, 'video')) == 0):
            try:
                post_img_src = find(post_content, 'img').get_attribute('src')
                post_file += '.png'
                response = requests.get(post_img_src)
                with open(post_file, "wb") as f:
                    f.write(response.content)
            except NoSuchElementException:
                pass    
        else:
            try:
                post_vid_src = find(post_content, 'video').get_attribute('src')
                post_file += '.mp4'
                response = requests.get(post_vid_src)
                with open(post_file, "wb") as f:
                    f.write(response.content)
            except NoSuchElementException:
                pass
        
        try:
            comment_container = find(driver, 'ul','_a9z6 _a9za')
            poster = find(comment_container, 'div')
            post_author = find(poster, 'h2').text.strip()
            post_text = find(poster, 'span', '_aacl').text.strip()
            
            driver.execute_script('arguments[0].scrollBy(0, arguments[0].scrollHeight)', comment_container)
            time.sleep(1)
            
            comments = finds(comment_container, 'li')
            has_comment = True
        except NoSuchElementException:
            post_author = ''
            post_text = ''
            has_comment = False
            errorLog(f'  ├─ x post {i} get comments error')
        
        comments_list = []
        
        if(has_comment):
            while(True):
                try:
                    driver.execute_script('arguments[0].scrollBy(0, arguments[0].scrollHeight)', comment_container)
                    b = find(comment_container, 'button')
                    try:
                        b.click()
                    except ElementClickInterceptedException:
                        driver.execute_script("arguments[0].click();", b)
                        #print("button cant click")
                    time.sleep(1)
                except NoSuchElementException:
                    #print("button not found")
                    break
                comments = finds(comment_container, 'li')
                if(len(comments) > max_comment):
                    break
            
            comments = finds(comment_container, 'li')
            comment_amount = min(len(comments), max_comment)
            
            for c in (c_pbar := tqdm(comments[:comment_amount], leave = False)):
                c_pbar.set_description(f'  ├─ Post {i} progress')
                try:
                    comment_author = find(c, 'h3').text.strip()
                    comment_text = find(c, 'span', '_aacl').text.strip()
                    
                    comments_list.append({
                        'author' : comment_author,
                        'text' : comment_text,
                    })
                except NoSuchElementException:
                    errorLog(f'  ├─ x post {i} get comment error')
            
        if(verbose):
            pbar.write(f'  ├─ Scraping post {i} complete with {len(comments_list)} comments')
        
        data.append({
            'author' : post_author,
            'text' : post_text,
            'content': post_file,
            'comments': comments_list
        })
        
        try:
            next_button = driver.find_element(by = By.XPATH, value = ".//div[contains(@class, '_aaqg _aaqh')]//button")
            #next_button.click()
            driver.execute_script("arguments[0].click();", next_button)
        except NoSuchElementException:
            errorLog(f'  ├─ x get navigation error, exiting...')
            break
            
    with open(f"{opath}/details.json", "w", encoding = 'utf8') as f:
        f.write(json.dumps(data, ensure_ascii = False, indent = 4))
            

def search(tag):
    url = f'https://www.instagram.com/explore/tags/{tag}/'
    driver.get(url)
    
    waitFor('a', 'oajrlxb2')

    posts = find(driver, 'a', 'oajrlxb2')
    posts.click()
    
    waitFor('div', 'll8tlv6m')
    scrapping()
    
def login(username, password):
    waitFor('input')
    
    try:
        loginBox = driver.find_element(by = By.XPATH, value = f".//input[@name='username']")
        passwordBox = driver.find_element(by = By.XPATH, value = f".//input[@name='password']")
        loginButton = driver.find_element(by = By.XPATH, value = f".//button[@type='submit']")
    except NoSuchElementException:
        errorLog('Login error, exiting...')
        return
    
    loginBox.send_keys(username)
    passwordBox.send_keys(password)
    loginButton.click()
    
    waitFor('div', '_lz6s')
    
    if(verbose):
        print("Login complete")
    

def scrapIG():
    global driver, max_post, max_comment, opath, errors, verbose
    
    parser = ArgumentParser()
    parser.add_argument('-t', help='Search tag')
    parser.add_argument('-c', help='Amount of posts')
    parser.add_argument('-r', help='Max comments')
    parser.add_argument('-o', help='Output path')
    parser.add_argument('-d', help='Driver path')
    parser.add_argument('-u', help='IG Username')
    parser.add_argument('-p', help='IG Password')
    parser.add_argument('--verbose', help='Print errors', action="store_true")

    args = parser.parse_args()
    max_post = 100 if args.c == None else int(args.c)
    max_comment = 1000 if args.r == None else int(args.r)
    opath = 'results' if args.o == None else args.o
    dpath = "../chromedriver.exe" if args.d == None else args.d
    tag = "" if args.t == None else args.t
    verbose = args.verbose
    errors = []
    
    username = args.u
    password = args.p
    
    if(not os.path.exists(opath)):
        os.makedirs(opath)
    if(not os.path.exists(f"{opath}/media")):
        os.makedirs(f"{opath}/media")
        
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(dpath, options=options, )
    
    time.sleep(1)
    driver.get(f'https://www.instagram.com')
    
    login(username, password)
    search(tag=tag)

if __name__ == "__main__":
    startTime = time.time()
    scrapIG()
    print(f' ✓ Scrap complete in {(time.time() - startTime):.2f} s, with {len(errors)} errors')
    
# cmd: python main.py -u='USERNAME' -p='PASSWORD' -t='ชัชชาติ' -c=10 -r=10