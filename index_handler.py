import tieba_util
import re
from urllib.parse import urljoin
from epub_maker import EpubMaker


def get_all_href_from_text(text):
    href_re = re.compile(r'/p/(\d+)')
    # href_re = re.compile(r'href="([^"]+)"')
    return href_re.findall(text)


def get_tid_from_href_list(href_list, origin_url):
    res = []
    for href in href_list:
        if not href.startswith('http'):
            href = urljoin(origin_url, href)
        tid = tieba_util.get_tid_from_url(href)
        if tid:
            res.append(tid)
    return res


def get_sub_tid_list_by_index_thread(index_tid, see_lz='1'):
    res = []
    tid = index_tid
    tieba_util.g_see_lz = '0'
    main_data = tieba_util.get_all_main_content_from_tid(tid, see_lz)
    comment_data = tieba_util.get_all_comment_data_from_tid(tid, see_lz)

    for content_data in main_data['content_list']:
        origin_url = 'http://tieba.baidu.com/p/{tid}?see_lz=1'.format(tid=main_data['tid'])

        href_list = get_all_href_from_text(content_data['content'])
        res += get_tid_from_href_list(href_list, origin_url)
        comment_detail = comment_data.get(content_data['post_id'], {})
        for comment in comment_detail.get('comment_info', []):
            href_list = get_all_href_from_text(comment['content'])
            res += get_tid_from_href_list(href_list, origin_url)
    tieba_util.g_see_lz = '1'
    return res


if __name__ == '__main__':
    tid = '3549982451'
    sub_tid_list = get_sub_tid_list_by_index_thread(tid, '0')
    thread_info = tieba_util.get_thread_info(tid)
    print(thread_info)
    em = EpubMaker('result/{tid}/'.format(tid=tid), thread_info['title'], thread_info['author'], thread_info['push_date'], tid)
    count = 0
    for sub_tid in sub_tid_list:
        sub_data = tieba_util.get_all_main_content_from_tid(sub_tid)
        if not sub_data:
            print('Fail in handle tid: {tid}, skip!'.format(tid=sub_tid))
            continue
        tc = '\n'.join([content_data['content'] for content_data in sub_data['content_list']])
        em.add_chapter(sub_data['title'], tc, sub_tid)
        count += 1
        print(count, sub_tid, sub_data['title'])
        # break
    print('Making epub file...')
    em.make_epub_file()
    print(len(sub_tid_list), sub_tid_list)
