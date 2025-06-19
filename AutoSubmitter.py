import random
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class AutoSubmitter:
    # 接受每个课程的评教页面，完成信息填写并提交
    def __init__(self, baseUrl, session, logger=None):
        self.indicators = None
        self.hidden_fields = None
        self.course_info = None
        self.soup = None
        self.baseUrl = baseUrl
        self.session = session

        if logger is None:
            self.logger = lambda message, level="info": print(f"[{level}] {message}")
        else:
            self.logger = logger

    def load_once_course(self, url):
        response = self.session.get(url)
        html_content = response.text
        # print(html_content)
        self.soup = BeautifulSoup(html_content, 'html.parser')
        # 提取课程信息
        teacher_info = self.soup.find('th', class_='Nsb_r_list_thb').get_text(strip=True)
        self.course_info = {
            'teacher': re.search(r'任课教师：([^&]+)', teacher_info).group(1),
            'course': re.search(r'课程名称：([^&]+)', teacher_info).group(1),
            'evaluation_type': re.search(r'评教大类：(\w+)', teacher_info).group(1)
        }

        # 提取所有隐藏字段
        self.hidden_fields = {}
        for hidden in self.soup.find_all('input', type='hidden'):
            if hidden.get('name'):
                self.hidden_fields[hidden['name']] = hidden.get('value', '')

        # 提取评价指标
        self.indicators = []
        rows = self.soup.select('table.layui-table tr')
        for row in rows:
            if row.find('input', {'name': 'pj06xh'}):
                indicator_text = row.get_text(strip=True).split('：')[0]
                indicator_id = row.find('input', {'name': 'pj06xh'})['value']
                options = []

                for radio in row.find_all('input', type='radio'):
                    option_text = radio.find_next(text=True).strip()
                    option_value = radio['value']
                    options.append({
                        'text': option_text,
                        'value': option_value,
                        'is_best': 'A' in option_text or '十分满意' in option_text
                    })

                self.indicators.append({
                    'id': indicator_id,
                    'text': indicator_text,
                    'options': options
                })

    def generate_submission_data(self, submitMode="save"):
        """生成提交数据 - 最终优化版 (返回元组列表格式)"""
        # 1. 基础数据 - 只包含页面首部的隐藏input字段
        if submitMode == "submit":
            data_dict = {
                'issubmit': '1',  # 设置为提交状态
                'pj09id': self.hidden_fields.get('pj09id', ''),
                'pj01id': self.hidden_fields.get('pj01id', ''),
                'pj0502id': self.hidden_fields.get('pj0502id', ''),
                'jg0101id': self.hidden_fields.get('jg0101id', ''),
                'jx0404id': self.hidden_fields.get('jx0404id', ''),
                'xsflid': self.hidden_fields.get('xsflid', ''),
                'xnxq01id': self.hidden_fields.get('xnxq01id', ''),
                'jx02id': self.hidden_fields.get('jx02id', ''),
                'pj02id': self.hidden_fields.get('pj02id', ''),
                'pageIndex': self.hidden_fields.get('pageIndex', ''),
                'ifypjxx': self.hidden_fields.get('ifypjxx', ''),
                'pj03id': self.hidden_fields.get('pj03id', ''),
                'isxtjg': '1'  # 固定值
            }
        elif submitMode == "save":
            data_dict = {
                'issubmit': '0',  # 设置为提交状态
                'pj09id': self.hidden_fields.get('pj09id', ''),
                'pj01id': self.hidden_fields.get('pj01id', ''),
                'pj0502id': self.hidden_fields.get('pj0502id', ''),
                'jg0101id': self.hidden_fields.get('jg0101id', ''),
                'jx0404id': self.hidden_fields.get('jx0404id', ''),
                'xsflid': self.hidden_fields.get('xsflid', ''),
                'xnxq01id': self.hidden_fields.get('xnxq01id', ''),
                'jx02id': self.hidden_fields.get('jx02id', ''),
                'pj02id': self.hidden_fields.get('pj02id', ''),
                'pageIndex': self.hidden_fields.get('pageIndex', ''),
                'ifypjxx': self.hidden_fields.get('ifypjxx', ''),
                'pj03id': self.hidden_fields.get('pj03id', ''),
                'isxtjg': '1'  # 固定值
            }

        # 2. 为每个评价指标添加选项
        total_indicators = len(self.indicators)

        for i, indicator in enumerate(self.indicators):
            # 如果是最后一个指标，精确匹配"B（满意）"
            if i == total_indicators - 1:
                best_option = next(
                    (opt for opt in indicator['options']
                     if opt['text'].strip() in ["B（满意）", "B(满意)", "B（满意", "B(满意）"]),
                    None
                )
                # 如果没找到精确匹配，再尝试宽松匹配
                if not best_option:
                    best_option = next(
                        (opt for opt in indicator['options']
                         if "B" in opt['text'] or "满意" in opt['text']),
                        None
                    )
            else:
                best_option = next(
                    (opt for opt in indicator['options']
                     if opt['text'].strip() in ["A（十分满意）", "A(十分满意)", "A（十分满意", "A(十分满意）"]),
                    None
                )
                # 如果没找到精确匹配，再尝试宽松匹配
                if not best_option:
                    best_option = next(
                        (opt for opt in indicator['options']
                         if "A" in opt['text'] or "十分满意" in opt['text']),
                        None
                    )

            if best_option:
                # 添加 pj06xh 和 pj0601id_x 到字典
                data_dict[f'pj06xh'] = indicator['id']
                data_dict[f'pj0601id_{indicator["id"]}'] = best_option['value']

                # 调试输出
                # print(f"指标 {i + 1}/{total_indicators} [{indicator['text']}] 选择: {best_option['text']}")
                self.logger(f"指标 {i + 1}/{total_indicators} [{indicator['text']}] 选择: {best_option['text']}")
            else:
                self.logger(f"警告: 指标 {i + 1}/{total_indicators} 未找到匹配选项！", level="error")


        # 读取主观评价
        commentList = []
        with open('sentences.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                commentList.append(line.strip())  # 去掉每行的首尾空格和换行符

        # 随机选择一个主观评价
        if commentList:
            subjective_comment = random.choice(commentList)
            self.logger(f"从'sentences.txt‘中随机读取到客观评价:{subjective_comment}")
        else:
            subjective_comment = "非常非常好的老师和非常美妙的课程"  # 如果文件为空，提供一个默认值
            self.logger(f"'sentences.txt'为空，设置默认客观评价:{subjective_comment}")
        # 添加主观评价到 data_dict
        data_dict['jynr'] = subjective_comment

        # 3. 转换为指定格式的元组列表
        data_list = []

        # 先添加基础字段
        base_fields = [
            'issubmit', 'pj09id', 'pj01id', 'pj0502id', 'jg0101id',
            'jx0404id', 'xsflid', 'xnxq01id', 'jx02id', 'pj02id',
            'pageIndex', 'ifypjxx'
        ]

        for field in base_fields:
            if field in data_dict:
                data_list.append((field, data_dict[field]))

        # 添加评价指标字段（保持 pj06xh 和 pj0601id_x 成对出现）
        for indicator in self.indicators:
            indicator_id = indicator['id']
            if f'pj0601id_{indicator_id}' in data_dict:
                data_list.append(('pj06xh', indicator_id))
                data_list.append((f'pj0601id_{indicator_id}', data_dict[f'pj0601id_{indicator_id}']))

        # 添加剩余字段
        remaining_fields = ['pj03id', 'jynr', 'isxtjg']
        for field in remaining_fields:
            if field in data_dict:
                data_list.append((field, data_dict[field]))

        return data_list

    def parse_course_list(self, operationUrl, schoolYear):
        """解析课程列表页面"""
        requestUrl = self.baseUrl + operationUrl[6:]
        response = self.session.get(requestUrl)
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        courses = []

        # 提取所有课程行
        rows = soup.select('table#dataList tr')
        for row in rows[1:]:  # 跳过表头
            cols = row.find_all('td')
            if len(cols) >= 8:  # 确保有足够的列
                course = {
                    '序号': cols[0].get_text(strip=True),
                    '学年学期': schoolYear,
                    '课程编号': cols[1].get_text(strip=True),
                    '课程名称': cols[2].get_text(strip=True),
                    '授课教师': cols[3].get_text(strip=True),
                    '评教类别': cols[4].get_text(strip=True),
                    '已评': cols[5].get_text(strip=True),
                    '是否提交': cols[6].get_text(strip=True),
                    '操作链接': None
                }

                # 提取评价链接
                link = cols[7].find('a')
                if link and 'href' in link.attrs:
                    course['操作链接'] = urljoin(self.baseUrl, link['href'])

                courses.append(course)

        return courses
