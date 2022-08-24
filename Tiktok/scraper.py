from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException, ElementNotInteractableException
from seleniumwire.utils import decode

from tqdm import tqdm
import requests
import time
import json
import os
from argparse import ArgumentParser

def errorLog(error, pbar = None):
    errors.append(error)
    if(pbar and verbose):
        pbar.write(error)
        
def xpathFormatter(type, **kwargs):
    if(not kwargs):
        return f".//{type}"
    
    def contain(attr, val):
        return f"contains(@{attr},'{val}')"
    contains = []
    for key, value in kwargs.items():
        contains.append(contain(key[1:], value))
    return f".//{type}[{' and '.join(contains)}]"
        
def waitFor(driver, type, **kwargs):
    try:
        _ = WebDriverWait(driver, 30)\
            .until(EC.presence_of_element_located((By.XPATH, xpathFormatter(type, **kwargs))))
        foundElement = find(driver, type, **kwargs)
    except Exception as e:
        raise e
    return foundElement

def waitForNot(driver, type, **kwargs):
    try:
        _ = WebDriverWait(driver, 30)\
            .until(EC.invisibility_of_element_located((By.XPATH, xpathFormatter(type, **kwargs))))
    except Exception as e:
        raise e

def find(driver, type, **kwargs):
    try:
        e = driver.find_element(by = By.XPATH, value = xpathFormatter(type, **kwargs))
        return e
    except Exception as e:
        raise e
    
def finds(driver, type, **kwargs):
    return driver.find_elements(by = By.XPATH, value = xpathFormatter(type, **kwargs))

def findText(driver, type, **kwargs):
    try:
        element = find(driver, type, **kwargs)
        return element.text.strip()
    except NoSuchElementException:
        return ""
    
def capchaDetector(pbar = None):
    try:
        find(driver, 'div', _class = 'captcha_verify_container')
        capchaCatcher(pbar)
    except Exception:
        return

def capchaCatcher(pbar = None):
    captShowed = 0
    captAppeared = False
    if(pbar):
        pbar.write("  ├─ ⏳ Waiting for CAPTCHA screen...")
    else:
        print("⏳ Waiting for CAPTCHA screen...")
    
    while(True):
        try:
            container = find(driver, 'div', _class = 'captcha_verify_container')
            captAppeared = True
            if(captShowed == 0):
                if(pbar):
                    pbar.write("  ├─ ⏸️  Solve CAPTCHA on browser to continue")
                else:
                    print("⏸️  Solve CAPTCHA on browser to continue")
            captShowed += 1
        except NoSuchElementException:
            if (captAppeared):
                break

def nextPage(index):
    close_button = waitFor(driver, 'button', _class = 'bqtu1e-ButtonBasicButtonContainer')
    close_button.click()
    
    moreContainer = find(driver, 'div', _class = 'DivMoreContainer')
    load_more_button = waitFor(moreContainer, 'button')
    load_more_button.click()
    
    waitForNot(moreContainer, 'svg')
    time.sleep(3)
    
    videos = finds(driver, 'div', _class = 'DivPlayerContainer')
    if(index >= len(videos)):
        raise NoSuchElementException
    videos[index].click()
    capchaDetector()

def getTitle(idx, pbar):
    try:
        container = find(driver, 'div', _class = 'DivBrowserModeContainer')
    except NoSuchElementException:
        errorLog(f'  ├─ ❌ post {idx} error: post not found', pbar)
        raise NoSuchElementException
        
    try:
        author = find(container, 'span', _class = 'tiktok-1r8gltq-SpanUniqueId')
        author_string = author.text.strip()
    except NoSuchElementException:
        errorLog(f'  ├─ ❌ post {idx} error: author not found', pbar)
        author_string = "[Author not found]"

    labels = finds(container, 'span', _class = 'tiktok-j2a19r-SpanText')
    label_text = [label.text.strip() for label in labels]
    label_string = "".join(label_text)

    tags = finds(container, 'strong', _class = 'tiktok-f9vo34-StrongText')
    tag_list = [tag.text.strip() for tag in tags]
    
    return (author_string, label_string, tag_list)
    
# def getCommentAPI(idx, pbar):
#     has_more = True
#     startIndex = 0
#     currIndex = 0
#     comments = []
    
#     for request in driver.requests:  
#         if request.response and 'https://www.tiktok.com/api/comment' in request.url: 
#             body = decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity')).decode(encoding='utf8')
#             res = json.loads(body)
#             if('total' in res):
#                 total_comment = int(res['total'])
#     if(max_comment != -1):
#         total_comment = min(total_comment, max_comment)
#     pbar.write(f'  ├─ Post {idx} progress')
    
#     while(has_more):
#         driver.execute_script('''
# ele = document.querySelector('.tiktok-46wese-DivCommentListContainer')
# ele.scrollBy(0, ele.scrollHeight)
# ''')
#         time.sleep(1)

#         for request in driver.requests[startIndex:]:  
#             currIndex += 1
#             if request.response and 'https://www.tiktok.com/api/comment' in request.url:  
#                 body = decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity')).decode(encoding='utf8')
#                 res = json.loads(body)
#                 if('comments' in res):
#                     for c in res['comments']:
#                         comments.append({
#                             'author': c['user']['nickname'],
#                             'text': c['text']
#                         })
#                     has_more = str(res['has_more']) == '1' and len(comments) < total_comment
#                     break
#         else:
#             has_more = False
#         startIndex = currIndex
#     return comments

def getCommentScrap(idx, pbar):
    comments = []
    
    pbar = tqdm(total = max_comment, leave = False)
    pbar.set_description(f'  ├─ Post {idx} progress')
    index = 0
    
    while(index < max_comment):
        comment_container = find(driver, 'div', _class = 'DivCommentListContainer')
        driver.execute_script("arguments[0].scrollBy(0, arguments[0].scrollHeight);", comment_container)
        capchaDetector(pbar)
        waitForNot(driver, 'div', _class = 'skeleton')
        #time.sleep(1)
        
        comment_list = finds(comment_container, 'div', _class = 'DivCommentItemContainer')
        if(index >= len(comment_list)):
            break
            
        for c in comment_list[index : min(max_comment, len(comment_list) - 1)]:
            # comment
            commenter = findText(c, 'span', _class = 'SpanUserNameText')
            comment_text = findText(c, 'p', _class = 'CommentText')
            comment_likes = findText(c, 'span', _class = 'SpanCount')
            
            # replies
            replies = []
            try:
                try:
                    while(reply_button := find(c, 'p', _class = 'ReplyActionText')):
                        driver.execute_script("arguments[0].click();", reply_button)
                        capchaDetector(pbar)
                        waitForNot(c, 'svg')
                except Exception:
                    pass
            
                reply_div = find(c, 'div', _class = 'DivReplyContainer')
                replies_div = finds(reply_div, 'div', _class = 'DivCommentContentContainer')
                for r in replies_div:
                    replier = findText(r, 'span', _class = 'SpanUserNameText')
                    reply_text = findText(r, 'p', _class = 'CommentText')
                    reply_likes = findText(r, 'span', _class = 'SpanCount')
                    
                    if(replier and reply_text):
                        replies.append({
                            'author': replier,
                            'text': reply_text,
                            'likes': reply_likes,
                        })
            except NoSuchElementException:
                pass
            
            comments.append({
                'author': commenter,
                'text': comment_text,
                'likes': comment_likes,
                'replies': replies,
            })
            pbar.update(1)
        index = len(comment_list)
    pbar.close()
    return comments

def getPosts():
    print(f'▶️ Start scraping {max_posts} posts')
    
    data = []
    for i in (pbar := tqdm(range(max_posts))):
        index = start_index + i
        capchaDetector(pbar)
        pbar.set_description(f" Total progress")
        
        # get title, comment
        try:
            author_string, label_string, tag_list = getTitle(index, pbar)
        except NoSuchElementException:
            errorLog(f'  ├─ ❌ post {index} error: Post not found', pbar)
            continue
        comments = getCommentScrap(index, pbar)
        
        # get content warning
        content_warning = findText(driver, 'div', _class = 'DivWarnInfoPosition')
        
        # get video
        try:
            video = waitFor(driver, 'video')
            video_url = video.get_attribute('src')

            response = requests.get(video_url)
            with open(f"{opath}/videos/{index:03}.mp4", "wb") as f:
                f.write(response.content)
            
            rec = {
                'video' : f'./videos/{index:03}.mp4',
                'author' : author_string,
                'label' : label_string,
                'tags' : tag_list,
                'warning' : content_warning,
                'comments' : comments,
            }   
            data.append(rec)
        except NoSuchElementException:
            errorLog(f'  ├─ ❌ post {index} error: Get video failed', pbar)
        except Exception as e:
            errorLog(f'  ├─ ❌ post {index} error: Save video failed {e}', pbar)
        
        capchaDetector(pbar)
        
        if(checkpoint and i and i % checkpoint == 0):
            if(verbose):
                pbar.write('  ├─ 🚩 Saving checkpoint...')
            with open(f"{opath}/details.json", "w", encoding = 'utf8') as f:
                f.write(json.dumps(data, ensure_ascii = False, indent = 4))
                
        # next post
        try:
            button = find(driver, 'button', **{'_class': 'ButtonBasicButtonContainer', '_data-e2e': 'arrow-right'})
            capchaDetector(pbar)
            button.click()
        except (NoSuchElementException, ElementNotInteractableException):
            if(verbose):
                pbar.write('  ├─ ➕ Loading more content...')
            try:
                nextPage(i)
            except NoSuchElementException:
                errorLog(f'  ├─ ❌ No more post found', pbar)
                break
        except ElementClickInterceptedException:
            errorLog(f'  ├─ ❌ post {index} error: Next button pressing intercepted', pbar)
            capchaDetector(pbar)
            continue
        
        time.sleep(1)
    
    with open(f"{opath}/details.json", "w", encoding = 'utf8') as f:
        f.write(json.dumps(data, ensure_ascii = False, indent = 4))

def scrapTK(search_query):
    use_search = search_query != ''
    driver.get(f'https://www.tiktok.com/search?q={search_query}' if use_search else 'https://tiktok.com/')
    
    # wait until page load & get capcha
    if(use_search):
        capchaCatcher()
    
    try:
        if use_search:
            xpath = ".//div[contains(@class, 'DivTab')][3]"
            try:
                _ = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, xpath)))
                videoTab = driver.find_element(by = By.XPATH, value = xpath)
            except Exception as e:
                pass
            driver.execute_script("arguments[0].click();", videoTab)
            
            video = waitFor(driver, 'div', _class = 'DivPlayerContainer')
        else:
            video = waitFor(driver, 'div', _class = 'DivVideoPlayerContainer')
    except Exception as e:
        print(f'❌ Access failed {e}, terminating...')
        exit()
    
    video.click()
    
    time.sleep(1)
    if(not use_search):
        capchaCatcher()
    
    # start scraping
    getPosts()

def main():
    global driver, opath, driver, errors, verbose
    global max_posts, max_comment, start_index, checkpoint
    
    # parsing arguments
    parser = ArgumentParser()
    parser.add_argument('-s', help='Search query')
    parser.add_argument('-c', help='Amount of posts to scrap')
    parser.add_argument('-r', help='Max comment')
    parser.add_argument('-o', help='Output path')
    parser.add_argument('-d', help='Driver path')
    parser.add_argument('-i', help='Start index')
    parser.add_argument('-ch', help='Save every')
    parser.add_argument('--verbose', help='Print errors', action="store_true")

    args = parser.parse_args()
    search = "" if args.s == None else args.s
    max_posts = 100 if args.c == None else int(args.c)
    max_comment = -1 if args.r == None else int(args.r)
    start_index = 0 if args.i == None else int(args.i)
    checkpoint = 12 if args.ch == None else int(args.ch)
    opath = 'results' if args.o == None else args.o
    dpath = "../chromedriver.exe" if args.d == None else args.d
    verbose = args.verbose
    errors = []
    
    # prepare output folder
    if(not os.path.exists(opath)):
        os.makedirs(opath)
    if(not os.path.exists(f'{opath}/videos')):
        os.makedirs(f'{opath}/videos')

    # start up driver and goto url
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(dpath, options = options)
    
    scrapTK(search)

if __name__ == "__main__":
    startTime = time.time()
    main()
    print(f' ✔️  Scrap complete in {(time.time() - startTime):.2f} s, with {len(errors)} errors')
    
# cmd: python scraper.py -s='ชัชชาติ' -c=10 -r=10