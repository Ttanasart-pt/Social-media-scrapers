from tqdm import tqdm
import time
import json
import requests
import os
import base64
from argparse import ArgumentParser

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

def get_file_content_chrome(driver, uri):
  result = driver.execute_async_script("""
    var uri = arguments[0];
    var callback = arguments[1];
    var toBase64 = function(buffer){for(var r,n=new Uint8Array(buffer),t=n.length,a=new Uint8Array(4*Math.ceil(t/3)),i=new Uint8Array(64),o=0,c=0;64>c;++c)i[c]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".charCodeAt(c);for(c=0;t-t%3>c;c+=3,o+=4)r=n[c]<<16|n[c+1]<<8|n[c+2],a[o]=i[r>>18],a[o+1]=i[r>>12&63],a[o+2]=i[r>>6&63],a[o+3]=i[63&r];return t%3===1?(r=n[t-1],a[o]=i[r>>2],a[o+1]=i[r<<4&63],a[o+2]=61,a[o+3]=61):t%3===2&&(r=(n[t-2]<<8)+n[t-1],a[o]=i[r>>10],a[o+1]=i[r>>4&63],a[o+2]=i[r<<2&63],a[o+3]=61),new TextDecoder("ascii").decode(a)};
    var xhr = new XMLHttpRequest();
    xhr.responseType = 'arraybuffer';
    xhr.onload = function(){ callback(toBase64(xhr.response)) };
    xhr.onerror = function(){ callback(xhr.status) };
    xhr.open('GET', uri);
    xhr.send();
    """, uri)
  if type(result) == int :
    raise Exception("Request failed with status %s" % result)
  return base64.b64decode(result)

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
    except Exception as e:
        raise e
    
def finds(driver, type, _class = ''):
    return driver.find_elements(by = By.XPATH, value = f".//{type}[contains(@class,'{_class}')]" if _class != '' else f".//{type}")

def scrapping():
    data = []
    
    pbar = tqdm(range(max_post))
    pbar.set_description(f'  ├─ Total progress')
    index = 0
    resIndex = 0
    
    while(len(data) < max_post):
        profile_div = driver.find_element(by = By.XPATH, value = f".//div[@data-pagelet='ProfileTimeline']")
        posts = profile_div.find_elements(by = By.XPATH, value = f"div")
        if(index >= len(posts)): # no more post
            break
        
        for p in posts[index:]:
            # post content
            try:
                post_author = find(p, 'strong').text.strip()
                post_text = p.find_element(by = By.XPATH, value = f".//div[contains(@class, 'qzhwtbm6 knvmm38d')]//div[@dir='auto']").text.strip()
            except NoSuchElementException:
                errorLog(f'  ├─ x get post error')
                continue
            except StaleElementReferenceException:
                errorLog(f'  ├─ x post disconnected')
                break
            
            # post media
            post_resources = []
            if(len(finds(p, 'video')) > 0):
                post_file = f"{opath}/media/{resIndex:03}.mp4"
                resIndex += 1
                
                try:
                    post_vid_src = find(p, 'video').get_attribute('src')
                    vid_bytes = get_file_content_chrome(driver, post_vid_src)
                    with open(post_file, "wb") as f:
                        f.write(vid_bytes)
                    post_resources.append(post_file)
                except NoSuchElementException:
                    errorLog(f'  ├─ x post {index} error: Get video failed', pbar)
                except Exception as e:
                    errorLog(f'  ├─ x post {index} error: Save video failed {e}', pbar)
                    
            elif(len(finds(p, "div[@class='l9j0dhe7']//img", 'i09qtzwb')) > 0):
                for img in finds(p, 'img'):
                    post_file = f"{opath}/media/{resIndex:03}.png"
                    resIndex += 1
                    post_img_src = img.get_attribute('src')
                    try:
                        response = requests.get(post_img_src)
                        with open(post_file, "wb") as f:
                            f.write(response.content)
                        post_resources.append(post_file)
                    except Exception as e:
                        errorLog(f'  ├─ x post {index} error: Save image failed {e}', pbar)
            
            #comments
            container_path = ".//div[@class='cwj9ozl2 tvmbv18p']/ul"
            try:
                comment_container = driver.find_element(by = By.XPATH, value = container_path)
                comments = finds(comment_container, 'li')
                comment_amount = min(len(comments), max_comment)
            except NoSuchElementException:
                comment_amount = 0
                errorLog(f'  ├─ x get comments error')
            
            comments_list = []
            
            if(comment_amount > 0):
                while(True):
                    try:
                        b = driver.find_element(by = By.XPATH, value = container_path + "/following-sibling::div//div[@role='button']")
                        driver.execute_script("arguments[0].click();", b)
                        time.sleep(1)
                        
                        comment_container = driver.find_element(by = By.XPATH, value = container_path)
                        comments = finds(comment_container, 'li')
                    except NoSuchElementException:
                        break
                    
                    if(len(comments) >= max_comment):
                        break
                
                try:
                    comment_container = driver.find_element(by = By.XPATH, value = container_path)
                    comments = finds(comment_container, 'li')
                    comment_amount = min(len(comments), max_comment)
                except NoSuchElementException:
                    break
                    
                c_pbar = tqdm(total = comment_amount, leave = False)
                c_pbar.set_description(f'  ├─ Post {index} progress')
                for c in comments:
                    try:
                        comment_author = find(c, 'span', 'pq6dq46d').text.strip()
                        comment_boxes = c.find_elements(by = By.XPATH, value = ".//div[contains(@dir, 'auto')]")
                        comment_line = [comment.text.strip() for comment in comment_boxes]
                        comment_text = "".join(comment_line)
                        
                        comments_list.append({
                            'author' : comment_author,
                            'text' : comment_text,
                        })
                        c_pbar.update(1)
                        if(len(comments_list) >= max_comment):
                            break
                    except NoSuchElementException:
                        errorLog(f'  ├─ x get comment error')
                c_pbar.close()
                  
            if(verbose):
                pbar.write(f'  ├─ Scraping post {index} complete with {len(comments_list)} comments')
            
            data.append({
                'author' : post_author,
                'text' : post_text,
                'resources': post_resources,
                'comments': comments_list
            })
            if(len(data) >= max_post):
                break
        
            index += 1 
            pbar.update(1)
            
        driver.execute_script('''scrollBy(0, document.body.scrollHeight)''')
        time.sleep(1)
    pbar.close()
            
    with open(f"{opath}/details.json", "w", encoding = 'utf8') as f:
        f.write(json.dumps(data, ensure_ascii = False, indent = 4))

def searchAccount(acc):
    url = f'https://www.facebook.com/{acc}'
    driver.get(url)
    
    try:
        _ = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, f".//div[@data-pagelet='ProfileTimeline']")))
    finally:
        pass
    
    scrapping()

def login(username, password):
    waitFor('input')
    
    try:
        loginBox = driver.find_element(by = By.XPATH, value = f".//input[@name='email']")
        passwordBox = driver.find_element(by = By.XPATH, value = f".//input[@name='pass']")
        loginButton = driver.find_element(by = By.XPATH, value = f".//button[@type='submit']")
    except NoSuchElementException:
        print('Login error, exiting...')
        exit()
    
    loginBox.send_keys(username)
    passwordBox.send_keys(password)
    loginButton.click()
    
    waitFor('div', 'kr520xx4')

def scrapFB():
    global driver, max_post, max_comment, opath, errors, verbose
    
    parser = ArgumentParser()
    parser.add_argument('-a', help='Account to search')
    parser.add_argument('-c', help='Amount of posts')
    parser.add_argument('-r', help='Max comments')
    parser.add_argument('-o', help='Output path')
    parser.add_argument('-d', help='Driver path')
    parser.add_argument('-u', help='FB Username')
    parser.add_argument('-p', help='FB Password')
    parser.add_argument('--verbose', help='Print errors', action="store_true")

    args = parser.parse_args()
    acc = "" if args.a == None else args.a
    max_post = 100 if args.c == None else int(args.c)
    max_comment = 1000 if args.r == None else int(args.r)
    opath = 'results' if args.o == None else args.o
    dpath = "../chromedriver.exe" if args.d == None else args.d
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
    driver.get(f'https://www.facebook.com')
    
    login(username, password)
    if(args.a):
        searchAccount(acc=acc)

if __name__ == "__main__":
    startTime = time.time()
    scrapFB()
    print(f' ✓ Scrap complete in {(time.time() - startTime):.2f} s, with {len(errors)} errors')
    
# cmd: python main.py -u='USERNAME' -p='PASSWORD' -a='chadchartofficial' -c=10 -r=10