import os
import re
import shutil
import zipfile
import random

import requests
import requests_cache


requests_cache.install_cache('img_cache')


def rewrite_file(file_path):
    f = open(file_path, 'r', encoding='utf-8')
    file_content = f.read()
    f.close()
    f = open(file_path, 'w', encoding='utf-8')
    return file_content, f


def copy_file(src_path, dst_path):
    with open(src_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return content, open(dst_path, 'w', encoding='utf-8')


def get_random_hex(length):
    hex_str = '0123456789abcdef'
    return ''.join([random.choice(hex_str) for _ in range(length)])


src_re = re.compile(r'src="([^"]+)"')


def get_src_from_text(text):
    src = src_re.findall(text)
    return src[0] if src else None


play_order_re = re.compile(r'playOrder="([^"]+)"')


def get_all_play_order(text):
    return play_order_re.findall(text)


class EpubMaker:
    work_dir = ''
    template_dir = 'EpubTemplate/'

    def __init__(self, work_dir, title, author, push_date=None, source=None, enable_download_img=True):
        self.work_dir = work_dir
        self.title = title
        self.author = author
        self.push_date = push_date
        self.source = source
        self.play_order = 0
        self.enable_download_img = enable_download_img

        self.make_work_dir()

    def make_work_dir(self):
        if os.path.exists(self.work_dir):
            self.init_play_order()
            return
        shutil.copytree(self.template_dir, self.work_dir)
        self.init_coverpage()
        self.init_fb_ncx()
        self.init_fb_opf()
        self.init_play_order()

    def zip_dir_to_epub(self, path, file_name):
        zip_handler = zipfile.ZipFile('result/{name}.epub'.format(name=file_name), 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(path):
            for file in files:
                zip_handler.write(os.path.join(root, file), os.path.join(root.replace(self.work_dir, ''), file))

    def init_coverpage(self):
        file_content, f = rewrite_file(self.work_dir + 'OPS/coverpage.html')
        file_content = file_content.replace('{Title}', self.title)
        file_content = file_content.replace('{Author}', '作者：%s' % self.author)
        file_content = file_content.replace('{PushTime}', '发表时间：%s' % self.push_date)
        file_content = file_content.replace('{Source}', self.source)
        f.write(file_content)
        f.close()

    def init_fb_ncx(self):
        fc, f = rewrite_file(self.work_dir + 'OPS/fb.ncx')
        # 51037e82-03ff-11dd-9fbb-0018f369440e
        uid = '%s-%s-%s-%s-%s' % \
              (get_random_hex(8), get_random_hex(4), get_random_hex(4), get_random_hex(4), get_random_hex(12))
        fc = fc.replace('{Uid}', uid)
        fc = fc.replace('{Title}', self.title)
        fc = fc.replace('{Author}', self.author)
        f.write(fc)
        f.close()

    def init_fb_opf(self):
        fc, f = rewrite_file(self.work_dir + 'OPS/fb.opf')
        fc = fc.replace('{Title}', self.title)
        fc = fc.replace('{Author}', self.author)
        fc = fc.replace('{PushDate}', self.push_date)
        fc = fc.replace('{Source}', self.source)
        f.write(fc)
        f.close()

    def init_play_order(self):
        with open(self.work_dir + 'OPS/fb.ncx', encoding='utf-8') as f:
            content = f.read()
        po_list = get_all_play_order(content)
        self.play_order = max([int(po) for po in po_list])

    def add_chapter(self, chapter_name, content, file_name=None):
        if not file_name:
            file_name = self.play_order
        is_need_update_index = \
            not os.path.exists(self.work_dir + 'OPS/{file_name}.html'.format(file_name=file_name))
        fc, f = copy_file(self.template_dir + 'OPS/chapter.html',
                          self.work_dir + 'OPS/{file_name}.html'.format(file_name=file_name))

        body_html = ''
        p_content = ''

        lines = content.split('\n')
        for line in lines:
            if self.enable_download_img and line.startswith('<img'):
                src = get_src_from_text(line)
                img_src = self.download_img(src)
                p_content += '<img src="{img_src}" class="manga">'.format(img_src=img_src)
            elif line.startswith('<br'):
                body_html += '<p>{content}</p>\n'.format(content=p_content)
                p_content = ''
            else:
                p_content += line
        if len(p_content) > 0:
            body_html += '<p>{content}</p>\n'.format(content=p_content)
        fc = fc.replace('{Title}', chapter_name)
        fc = fc.replace('<!-- title -->', '<h2>{title}</h2>'.format(title=chapter_name))
        fc = fc.replace('{MainContent}', body_html)
        f.write(fc)
        f.close()
        if is_need_update_index:
            self.add_index(chapter_name, file_name)

    def add_index(self, chapter_name, file_name):
        nav_point_html = '''
            <navPoint id="chapter{play_order}" playOrder="{play_order}">
            <navLabel><text>{chapter_name}</text></navLabel>
            <content src="{file_name}.html"/>
            </navPoint>\n\n
            <!--ANOTHER NAVPOINT-->\n
            '''.format(play_order=self.play_order, file_name=file_name, chapter_name=chapter_name)
        fc, f = rewrite_file(self.work_dir + 'OPS/fb.ncx')
        f.write(fc.replace('<!--ANOTHER NAVPOINT-->', nav_point_html))
        f.close()

        item_html = """
            <item id="chapter{play_order}"  href="{file_name}.html"  media-type="application/xhtml+xml"/>\n\n<!-- ANOTHER ITEM -->
            """.format(play_order=self.play_order, file_name=file_name)

        itemref_html = """
            <itemref idref="chapter{play_order}" linear="yes"/>\n\n<!-- ANOTHER ITEMREF -->
            """.format(play_order=self.play_order)
        fc, f = rewrite_file(self.work_dir + 'OPS/fb.opf')
        fc = fc.replace('<!-- ANOTHER ITEM -->', item_html)
        fc = fc.replace('<!-- ANOTHER ITEMREF -->', itemref_html)
        f.write(fc)
        f.close()
        self.play_order += 1

    def download_img(self, img_url):
        p = requests.get(img_url)
        img_name, img_type = re.findall(r'(\w+)\.(jpg|png|gif|jpeg)', img_url)[0]
        img_path = self.work_dir + 'OPS/images/' + img_name + '.' + img_type
        with open(img_path, 'wb') as f:
            f.write(p.content)
        return 'images/' + img_name + '.' + img_type

    def make_epub_file(self, file_name=None):
        epub_name = file_name if file_name else '{author} - {title}'.format(author=self.author, title=self.title)
        self.zip_dir_to_epub(self.work_dir, epub_name)
