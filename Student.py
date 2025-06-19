import base64
import ddddocr
import requests
from lxml import etree


class Student(object):

    def __init__(self, account, password):
        self.name = None
        self.className = None
        self.account = account
        self.password = password
        self.stuCode = account      # 学号=账号
        self.cookieStr = None
        self.baseUrl = "http://jwn.ccdgut.edu.cn/jsxsd"     # 内外网兼容的网址，要求必须加上后缀’jsxsd‘否则导致无法正常进入正确系统
        self.session = requests.Session()

    def login(self):
        account_encoded = base64.b64encode(self.account.encode('utf-8'))
        password_encoded = base64.b64encode(self.password.encode('utf-8'))

        encoded = account_encoded.decode('utf-8') + "%%%" + password_encoded.decode('utf-8')

        # 初始化ddddocr识别验证码
        ocr = ddddocr.DdddOcr(show_ad=False)
        # 获取验证码图片
        captchaResponse = self.session.get(self.baseUrl + "/verifycode.servlet")

        image_bytes = captchaResponse.content

        # 使用ddddocr识别
        captchaResult = ocr.classification(image_bytes)

        data = {
            'loginMethod': "LoginToXk",
            'userAccount': self.account,
            'userPassword': self.password,
            "RANDOMCODE": captchaResult,
            "encoded": encoded
        }

        # 请求登录
        self.session.post(self.baseUrl + "/xk/LoginToXk", data=data)
        # 访问主页
        response = self.session.post(self.baseUrl + "/framework/xsMain.jsp")
        html = etree.HTML(response.text)
        # 校验登录结果
        if "个人中心" in response.text:
            # 成功,保存Cookie记录个人信息
            # //*[@id="zccd"]/div[2]/div[1]/div[2]/div[4]/div/div/div/p[1]
            self.name = html.xpath('//*[@id="zccd"]/div[2]/div[1]/div[2]/div[4]/div/div/div/p[1]')[0].text.strip()
            self.className = html.xpath('//*[@id="zccd"]/div[2]/div[1]/div[2]/div[4]/div/div/div/p[3]')[0].text.strip()
            self.cookieStr = '; '.join([f'{k}={v}' for k, v in self.session.cookies.items()])
            return True, self.cookieStr
        else:
            # 失败
            msgElem = html.xpath('//*[@id="showMsg"]')  # 定位错误原因
            # print(response.text)
            if msgElem:
                errorMsg = msgElem[0].text.strip()
            else:
                errorMsg = "未知错误，可能为页面结构变化导致未读取到错误信息"
            if "验证码错误" in msgElem or "请先登录系统" == msgElem:
                print("预料之内的异常:", msgElem)
                return self.login()

            return False, "请尝试重新登陆或检查账号密码是否正确"

    def getEvaluateInfo(self):
        # 获取评教条目数据
        url = self.baseUrl + "/xspj/xspj_find.do"
        response = self.session.get(url)
        # print(response.text)
        html = etree.HTML(response.text)

        # 提取表头（列名）
        headers = html.xpath('//table[@class="layui-table"]/tr[1]/th/text()')

        # 提取数据行
        rows = html.xpath('//table[@class="layui-table"]/tr[position()>1]')

        # 存储提取的数据
        evaluation_list = []

        for row in rows:
            data = {}
            # 提取每列的文本内容
            cols = row.xpath('./td')
            for i, col in enumerate(cols):
                col_name = headers[i] if i < len(headers) else f"列{i + 1}"
                # 如果是操作列，提取链接
                if col_name == "操作":
                    link = col.xpath('.//a/@href')
                    if link:
                        data["操作链接"] = link[0]
                    text = col.xpath('.//a/text()')
                    if text:
                        data[col_name] = text[0]
                else:
                    data[col_name] = col.xpath('normalize-space(.)')

            evaluation_list.append(data)
        # print(evaluation_list)
        return evaluation_list

    def show(self):
        print(self.name, self.className, self.cookieStr)

