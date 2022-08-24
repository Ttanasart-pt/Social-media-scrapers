import twint

import json
import re
import requests
import time
import os
from argparse import ArgumentParser

from tqdm import tqdm

from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

def errorLog(error, pbar = None):
    errors.append(error)
    if(pbar and verbose):
        pbar.write(error)
        
def getReplyFromTweet(idx, url, pbar):
    #pid = re.findall('([^\/]+$)', url)[-1]
    reply_list = []
    
    driver.get(url)
    
    try:
        _ = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, ".//article")))
    finally:
        pass
    
    _h = 0
    while(True):
        driver.execute_script('''scrollBy(0, document.body.scrollHeight)''')
        time.sleep(0.75)
        
        top_reps = driver.find_elements(by = By.XPATH, value = ".//article")
        if(max_reply != -1 and len(top_reps) >= max_reply):
            break;
        
        h = driver.execute_script('''document.body.scrollHeight''')
        if(h == _h):
            break
        _h = h
    
    time.sleep(1)
    top_reps = driver.find_elements(by = By.XPATH, value = ".//article")
    total_reply = min(max_reply, len(top_reps))
    
    pbar = tqdm(total = total_reply, leave = False)
    pbar.set_description(f'  ├─ tweet {idx} replies')
    
    for t in top_reps:
        try:
            rep_aut = t.find_element(by = By.XPATH, value = ".//span[contains(@class, 'css-901oao css-16my406 css-bfa6kz r-poiln3 r-bcqeeo r-qvutc0')]").text.strip()
            rep_con = t.find_element(by = By.XPATH, value = ".//div[contains(@class, 'css-901oao r-1nao33i r-37j5jr r-a023e6 r-16dba41 r-rjixqe r-bcqeeo r-bnwqim r-qvutc0')]").text.strip()
            
            reply_list.append({
                'username': rep_aut,
                'tweet': rep_con
            })
            pbar.update(1)
            if(len(reply_list) >= max_reply):
                break
        except NoSuchElementException:
            errorLog(f'  ├─ x tweet {idx} replies error', pbar)
    
    if(verbose):
        pbar.write(f'  ├─ post {idx} : {len(reply_list)} / {len(top_reps)} replies collected')
    pbar.close()
    
    return reply_list

def getReplies(list):
    _tweets = []
    for t in list:
        _tweets.append(t)
        if(len(_tweets) >= max_tweets):
            break
    
    print(f" ✓ Found {len(_tweets)} tweets")
    
    tweet_list = []
    idx = 1
    for t in (pbar := tqdm(_tweets)):
        ps = t.photos
        pl = []
        for p in ps:
            pname = re.findall('([^\/]+$)', p)[-1]
            img = requests.get(p).content
            with open(f'{opath}/images/{pname}', 'wb') as f:
                f.write(img)
            pl.append(f'./images/{pname}')
        
        replies = getReplyFromTweet(idx, t.link, pbar)
        
        tweet_list.append({
            'username': t.username,
            'tweet': t.tweet,
            'photos': pl,
            'replies': replies,
        })
        idx += 1
        
    with open(f'{opath}/details.json', 'w', encoding = 'utf8') as f:
        f.write(json.dumps(tweet_list, ensure_ascii = False, indent = 4))
    
def getTweets(user = "", search = ""):
    tweets = []

    # Configure
    c = twint.Config()
    if(user):
        c.Username = user
    if(search):
        c.Search = search
    c.Limit = max_tweets
    c.Hide_output = True
    c.Store_object = True
    c.Store_object_tweets_list = tweets
    twint.run.Search(c)
    
    getReplies(tweets)

def scrapTW():
    global driver, max_tweets, max_reply, verbose, opath, errors
    
    parser = ArgumentParser()
    parser.add_argument('-s', help='Search query')
    parser.add_argument('-u', help='Search user')
    parser.add_argument('-c', help='Amount of tweets')
    parser.add_argument('-r', help='Max replies')
    parser.add_argument('-o', help='Output path')
    parser.add_argument('-d', help='Driver path')
    parser.add_argument('--verbose', help='Print errors', action="store_true")

    args = parser.parse_args()
    search = "" if args.s == None else args.s
    user = "" if args.u == None else args.u
    max_tweets = 100 if args.c == None else int(args.c)
    max_reply = 1000 if args.r == None else int(args.r)
    opath = 'results' if args.o == None else args.o
    dpath = "../chromedriver.exe" if args.d == None else args.d
    verbose = args.verbose
    errors = []
    
    if(not os.path.exists(opath)):
        os.makedirs(opath)
    if(not os.path.exists(f"{opath}/images")):
        os.makedirs(f"{opath}/images")
    
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(dpath, options=options)
    
    if(user):
        getTweets(user = user)
    if(search):
        getTweets(search = search)

if __name__ == '__main__':
    startTime = time.time()
    scrapTW()
    print(f' ✓ Scrap complete in {(time.time() - startTime):.2f} s, with {len(errors)} errors')
    
# cmd: python main.py -s='ชัชชาติ' -c=10 -r=10