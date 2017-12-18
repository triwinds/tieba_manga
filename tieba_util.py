import re
import requests
import requests_cache
import time
import json
from bs4 import BeautifulSoup

requests_cache.install_cache('tieba_cache')
session = requests.session()
g_see_lz = '1'
with open('headers.json') as f:
    headers = json.load(f)
    session.headers = headers


def get_all_main_content_from_tid(tid, see_lz=g_see_lz):
    s = get_first_page_soup(tid)
    max_page = get_max_page_from_soup(s)
    title = s.find('h3', attrs={'class': 'core_title_txt'})
    if title:
        title = title.text
    else:
        print('No title found, tid: {tid}'.format(tid=tid))
        return None
    res = {'tid': tid, 'title': title, 'content_list': []}
    for page in range(1, max_page + 1):
        res['content_list'] += get_main_content_list_from_tid_page(tid, page, see_lz)

    return res


def get_all_comment_data_from_tid(tid, see_lz=g_see_lz):
    max_page = get_max_page_from_tid(tid, see_lz)
    fid = get_forum_id_from_tid(tid, see_lz)

    comment_list = {}
    for page in range(1, max_page + 1):
        comment_list_data = get_comment_from_tid_fid_page(tid, fid, page, see_lz)['data']['comment_list']
        comment_list.update(comment_list_data)
    return comment_list


def get_thread_info(tid):
    s = get_first_page_soup(tid)
    info = {'author': s.find('a', attrs={'class': 'p_author_name'}).text,
            'tid': tid,
            'push_date': s.find_all('span', attrs={'class': 'tail-info'})[1].text.split(' ')[0],
            'max_page': get_max_page_from_soup(s),
            'title': s.find('h3', attrs={'class': 'core_title_txt'}).text}
    return info


def get_first_page_soup(tid, see_lz=g_see_lz):
    base_url = 'http://tieba.baidu.com/p/{tid}?pn={page}&see_lz={see_lz}' \
        .format(tid=tid, page=1, see_lz=see_lz)
    p = session.get(base_url)
    return BeautifulSoup(p.text, 'lxml')


max_page_re = re.compile(r'共(\d+)页')


def get_max_page_from_soup(soup):
    li = soup.find('li', attrs={'class': 'l_reply_num'})
    if li:
        max_page = max_page_re.findall(li.text)
        return int(max_page[0]) if max_page else 1


forum_id_re = re.compile(r'"forum_id":(\d+)')


def get_forum_id_from_text(text):
    fid = forum_id_re.findall(text)
    return fid[0] if fid else None


def get_forum_id_from_tid(tid, see_lz=g_see_lz):
    base_url = 'http://tieba.baidu.com/p/{tid}?pn={page}&see_lz={see_lz}' \
        .format(tid=tid, page=1, see_lz=see_lz)
    p = session.get(base_url)
    return get_forum_id_from_text(p.text)


def get_max_page_from_tid(tid, see_lz=g_see_lz):
    s = get_first_page_soup(tid, see_lz)
    return get_max_page_from_soup(s)


def get_comment_from_tid_fid_page(tid, fid, page, see_lz=g_see_lz):
    comment_url = 'http://tieba.baidu.com/p/totalComment?t={nowtime}&tid={tid}&fid={fid}&pn={page}&see_lz={see_lz}' \
        .format(tid=tid, fid=fid, page=page, nowtime=int(time.time() * 1000), see_lz=see_lz)
    p = session.get(comment_url)
    try:
        return p.json()
    except:
        return None


def get_main_content_list_from_tid_page(tid, page, see_lz=g_see_lz):
    """
    :param tid: tieba id
    :param page: page
    :param see_lz: see_lz param in url
    :return:
    content_list: [
            {
                post_id: post_id(str),
                content: content,
                page: page
            }
        ]
    """
    if not tid:
        return None

    base_url = 'http://tieba.baidu.com/p/{tid}?pn={page}&see_lz={see_lz}' \
        .format(tid=tid, page=page, see_lz=see_lz)
    p = session.get(base_url)
    soup = BeautifulSoup(p.content, 'lxml')

    content_div = soup.find_all('div', attrs={'class': 'd_post_content'})

    res = []
    for div in content_div:
        div_id = div.get('id')
        post_id = None
        if div_id and div_id.startswith('post_content_'):
            post_id = div_id[13:]
        content = [str(i).strip() for i in div]
        res.append({'content': '\n'.join(content), 'post_id': post_id, 'page': page})

    return res


tid_re = re.compile(r'/p/(\d+)')


def get_tid_from_text(text):
    tid = tid_re.findall(text)
    return tid[0] if tid else None


def get_tid_from_url(url):
    tid = get_tid_from_text(url)
    if tid:
        return tid

    tmp = session.get(url)
    s = BeautifulSoup(tmp.text, 'lxml')
    a = s.find('a', attrs={'id': 'lzonly_cntn'})
    return get_tid_from_text(a.get('href')) if a else None


def get_main_content_from_url(url):
    """
    :param url: tieba page url
    :return: {
        tid: tieba_id,
        title: title,
        content_list: [
            {
                post_id: post_id(str),
                content: content,
                page: page
            }
        ]
    }
    """
    tid = get_tid_from_url(url)
    return get_all_main_content_from_tid(tid)





if __name__ == '__main__':
    data = get_main_content_from_url('https://tieba.baidu.com/p/3549982451?red_tag=3033558797')
    print(data)
