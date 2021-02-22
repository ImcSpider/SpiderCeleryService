import sys
import os
import time
import datetime
import json
import re
import threading
import copy
from dateutil.relativedelta import relativedelta
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
from foo.helper import common
from foo import params

logger = common.logging
lock = threading.Lock()
spider_name = params.spider_name


class MainSpider(object):
    def __init__(self, browserOauth, nameShort, url, port):
        self.url = url
        self.browserOauth = browserOauth
        self.nameShort = nameShort
        self.port = port
        self.loginNum = 0
        self.loan_message = []
        self.refund_message = []
        self.year_month_dic = {'01': '31', '02': '28', '03': '31', '04': '30', '05': '31', '06': '30', '07': '31',
                               '08': '31',
                               '09': '30', '10': '31', '11': '30', '12': '31'}
        self.load_base_url = "https://gsp-gw.aliexpress.com/openapi/param2/1/gateway.seller/api.fund.report.page.data?_timezone=-8&spm={}&type=orderLoan&dateRange={}%2C{}&current={}&total={}&pageSize=100"
        self.refund_base_url = "https://gsp-gw.aliexpress.com/openapi/param2/1/gateway.seller/api.fund.report.page.data?_timezone=-8&spm={}&type=orderRefund&dateRange={}%2C{}&current={}&total={}&pageSize=100"
        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:{}".format(port))
        self.driver = webdriver.Chrome(options=options, executable_path=params.chrome_cpu)
        self.driver.implicitly_wait(7)
        self.driver.set_page_load_timeout(180)
        self.driver.maximize_window()

    def get_index_url(self):
        t1 = time.time()
        try:
            self.driver.get(self.url)
        except Exception:
            logger.error("打开店铺 : %s 首页超时重新放入队列......" % self.nameShort)
            self.driver.quit()
            exit(-99)
        logger.info("打开店铺 : %s 首页用时 %d 秒......" % (self.nameShort, int(time.time() - t1)))

    def login_before(self, page_name):
        while True:
            if "login" in self.driver.current_url and "authControl" not in self.driver.current_url:
                self.loginNum += 1
                logger.info("店铺 : %s  开始第  %d  次进入  %s   登录...." % (self.nameShort, self.loginNum, page_name))
                if self.loginNum > 1:
                    self.driver.refresh()
                if self.loginNum < 6:
                    self.login()
                else:
                    logger.error("店铺 : %s  进入   %s    超过最大登录次数,登录失败,请检查登录元素是否变更..." %
                                 (self.nameShort, page_name))
                    self.driver.quit()
                    exit(-99)
            elif "authControl" in self.driver.current_url:
                # 遇到永久关店店铺需要点击
                auth_control_ele = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='alibaba']/div[@class='page grid-c']/div[2]/p[2]/a[1]")))
                logger.info("永久关店店铺 : %s 的登录跳转text : %s" % (self.nameShort, auth_control_ele.text))
                self.driver.execute_script("arguments[0].click()", auth_control_ele)
                time.sleep(5)

            else:
                logger.info("店铺 : %s  登录成功进入  %s ..." % (self.nameShort, page_name))
                self.loginNum = 0
                break

    def distance(self, lenth):
        mid_lenth = 0.7 * lenth
        start_a = 1.4
        end_a = -2.3
        actully_lenth = 0
        lst = []
        v0 = 1
        while True:
            if actully_lenth < mid_lenth:
                v = v0 + start_a
                x = v + 0.5 * start_a
                actully_lenth += x
                lst.append(x)
                v0 = v
            else:
                v = v0 + end_a
                if v <= 0 or actully_lenth >= lenth:
                    break
                x = v + 0.5 * end_a
                actully_lenth += x
                lst.append(x)
                v0 = v
        return lst

    def login(self):
        # 修改页面语言为中文
        try:
            language_ele = self.driver.find_element_by_id("header-lang-switch-select")
            Select(language_ele).select_by_value("zh_CN")
        except Exception:
            logger.error("店铺 : %s  在选择页面语言为中文时出错...可能存在xpath变更...重入队列" % self.nameShort)
            self.driver.quit()
            exit(-99)
        global login_ele
        # 判断此时是快速登录按钮还是正常登录按钮
        try:
            iframe_ele = self.driver.find_element_by_id("alibaba-login-box")
            self.driver.switch_to.frame(iframe_ele)
        except Exception:
            pass
        try:
            try:
                login_ele = self.driver.find_element_by_id('has-login-submit')
            except Exception:
                login_ele = self.driver.find_element_by_id("fm-login-submit")
            ActionChains(self.driver).move_to_element(login_ele).perform()
            self.driver.execute_script("arguments[0].click()", login_ele)
            time.sleep(5)
            # 判断是否出现滑块验证
            captcha_hua_list = self.driver.find_elements_by_id("nc_1_n1z")
            if captcha_hua_list:
                logger.info("店铺 :  %s  存在滑块验证..." % self.nameShort)
                self.driver.save_screenshot("10.png")
                ActionChains(self.driver).move_to_element(captcha_hua_list[0]).perform()
                ActionChains(self.driver).click_and_hold(captcha_hua_list[0]).perform()
                lst = self.distance(420)
                logger.info(lst)
                for i in lst:
                    ActionChains(self.driver).move_by_offset(i, 0).perform()
                logger.info("执行完成")
                time.sleep(2)
                ActionChains(self.driver).release().perform()
                self.driver.save_screenshot("11.png")
                time.sleep(2)
                logger.info("滑块移动完成")
                login_ele_list = self.driver.find_elements_by_id("fm-login-submit")
                if login_ele_list:
                    ActionChains(self.driver).move_to_element(login_ele_list[0]).perform()
                    self.driver.execute_script("arguments[0].click()", login_ele_list[0])
        except Exception:
            logger.error("店铺 : %s  登录按钮变迁,登录失败" % self.nameShort)
            self.driver.refresh()
        time.sleep(3)

    def start_browser(self):
        # 打开首页
        self.get_index_url()
        # 判断是否需要登录
        self.login_before("Index Page")

        # 等待进入首页
        try:
            global orders_ele
            orders_ele = WebDriverWait(self.driver, 20, poll_frequency=3).until(
                EC.presence_of_element_located((By.XPATH,
                                                "//div[@class='left-panel ae-header-panel']/div\
                                          [@class='head-menu-section-left']/div[@class='head-menu-section']/div[3]/a")))
            a_href = orders_ele.get_attribute('href')
            if 'order' not in a_href:
                logger.error("店铺: %s  头部导航栏的 Orders交易 标签有变更...重新入队..." % self.nameShort)
                self.driver.quit()
                exit(-99)
        except Exception:
            logger.error("店铺 ： %s  登录成功后跳转至首页超时..重新入队.." % self.nameShort)
            self.driver.quit()
            exit(-99)
        try:
            ActionChains(self.driver).move_to_element(orders_ele).perform()
            self.driver.execute_script("arguments[0].click()", orders_ele)
        except Exception:
            logger.error("店铺 : %s 进入Orders订单页异常...重新入队.." % self.nameShort)
            self.driver.quit()
            exit(-99)
        logger.info("店铺 : %s 成功进入 Orders  订单页...." % self.nameShort)

        try:
            spm_ele = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH,
                                                                                           "//div[@id='ae-layout']/div\
                                                   [@class='aside-menu']/div[@class='ae-navigation-aside-container']")))
            self.spm = spm_ele.get_attribute("data-spm-anchor-id").replace('0', '18')
        except Exception:
            logger.error("店铺 : %s  spm参数未成功加载,重新入队..." % self.nameShort)
            self.driver.quit()
            exit(-99)

        # 进入资金明细页面
        try:
            global ali_pay_ele
            ali_pay_ele = WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH,
                                                                                               "//aside/ul\
                         [@class='ae-layout-next-menu ae-layout-next-ver navigation-menu-container']/li[3]/ul\
                         [@class='ae-layout-next-menu-sub-menu']/li[1]/div/span/a")))
        except Exception:
            logger.error("店铺 :  %s  未找到资金明细按钮,请检查网页是否存在变更.....重入队列" % self.nameShort)
            self.driver.quit()
            exit(-99)

        ActionChains(self.driver).move_to_element(ali_pay_ele).perform()
        self.driver.execute_script("arguments[0].click()", ali_pay_ele)

    def load_refund_money(self, flag):
        # 点击按钮进入退/放款页面
        try:
            if flag == "loan":
                number = 2
            else:
                number = 3
            payout_history_ele = WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH,
                                                                                                      "//div\
                            [@class='filter-tab']/div[@class='next-tabs next-tabs-wrapped next-tabs-top next-medium']\
                            /div[@class='next-tabs-bar']/div[@class='next-tabs-nav-container']/div\
                            [@class='next-tabs-nav-wrap']/div[@class='next-tabs-nav-scroll']/ul/li[%d]/div" % number)))
            self.driver.execute_script("arguments[0].click()", payout_history_ele)
        except Exception:
            logger.error("店铺 : %s  点击按钮进入  %s  页面时发生错误,请检查xpath是否变更....重入队列.." % (self.nameShort, flag))
            self.driver.quit()
            exit(-99)

        # 拼凑需要采集数据的时间并访问退/放款url，首次访问记录数据总条数
        try:
            global first_total_num
            first_total_num_ele = WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH,
                                                                                                       "//div\
                                            [@class='main-page']/div[last()]/div[@class='pagination-zone']/span\
                                            [@class='pagination-total']")))
            ele_text = first_total_num_ele.text
            first_total_num = ''.join(re.findall(r"[\d+]", ele_text))
        except Exception:
            logger.error("店铺 ： %s  查找首次进入  %s  页面的当前页数据总条数元素时失败，请检查XAPTH...重入队列.." %
                         (self.nameShort, flag))
            self.driver.quit()
            exit(-99)

        # 访问退/放款第一页
        date_time = datetime.datetime.today() - relativedelta(months=1)
        year_ = str(date_time.year)
        month_ = str(date_time.month)
        if len(month_) < 2:
            month_ = '0' + month_
        # start_time = year_ + '-' + month_ + '-' + '01'
        # end_time = year_ + '-' + month_ + '-' + self.year_month_dic[month_]
        start_time = params.start_date
        end_time = params.end_date
        start_timestamp = int(time.mktime(time.strptime("%s 00:00:00" % start_time, "%Y-%m-%d %H:%M:%S"))) * 1000
        end_timestamp = int(time.mktime(time.strptime("%s 00:00:00" % end_time, "%Y-%m-%d %H:%M:%S"))) * 1000
        html = self.driver.page_source
        csrf_token = re.search(r"[\s\S]*?tokenValue: \"([\s\S]*?)\"[\s\S]*?}[\s\S]*", html).group(1)
        retry_num = 3
        while retry_num:
            retry_num -= 1
            if flag == "loan":
                load_refund_url = self.load_base_url.format(self.spm, start_timestamp, end_timestamp, '1',
                                                            first_total_num)
            else:
                load_refund_url = self.refund_base_url.format(self.spm, start_timestamp, end_timestamp, '1',
                                                              first_total_num)
            js = """var xmlhttp= new XMLHttpRequest();
                    xmlhttp.open('GET','%s',false);
                    xmlhttp.setRequestHeader('x-csrf','%s');
                    xmlhttp.setRequestHeader("Content-Type","application/x-www-form-urlencoded;charset=utf-8");
                    xmlhttp.setRequestHeader("Accept","*/*");
                    xmlhttp.withCredentials = 'true';
                    xmlhttp.send();
                    return xmlhttp.responseText;
                    """ % (load_refund_url, csrf_token)
            response = json.loads(self.driver.execute_script(js))
            try:
                flag_ = response["success"]
            except KeyError:
                response["success"] = ""
            if response["success"]:
                global total_load_num
                try:
                    total_load_num = int(response["data"]["modules"][0]["data"]["total"])
                except Exception:
                    logger.info("店铺: %s  的  %s  数据总量为空..." % (self.nameShort, flag))
                    total_load_num = 0
                break
            if retry_num == 0:
                logger.error("店铺： %s  多次访问  %s  第一页失败,请检查...重新入队..." % (self.nameShort, flag))
                self.driver.quit()
                exit(-99)

        if total_load_num:
            logger.info("店铺 : %s  开始循环采集  %s 页数据...总数据量条数为：%d 条..." %
                        (self.nameShort, flag, total_load_num))
            self.load_intervl(start_timestamp, end_timestamp, total_load_num, flag, csrf_token)

    # 循环采集退/放款数据
    def load_intervl(self, start_timestamp, end_timestamp, total_load_num, flag, csrf_token):
        if total_load_num % 100 == 0:
            request_num = int(total_load_num / 100)
        else:
            request_num = int(total_load_num // 100) + 1
        for page in range(1, request_num + 1):
            if flag == "loan":
                base_url = self.load_base_url.format(self.spm, start_timestamp, end_timestamp, page, total_load_num)
            else:
                base_url = self.refund_base_url.format(self.spm, start_timestamp, end_timestamp, page, total_load_num)
            retry_num = 3
            while retry_num:
                retry_num -= 1
                js = """var xmlhttp= new XMLHttpRequest();
                        xmlhttp.open('GET','%s',false);
                        xmlhttp.setRequestHeader('x-csrf','%s');
                        xmlhttp.setRequestHeader("Content-Type","application/x-www-form-urlencoded;charset=utf-8");
                        xmlhttp.setRequestHeader("Accept","*/*");
                        xmlhttp.withCredentials = !0;
                        xmlhttp.send();
                        return xmlhttp.responseText;
                        """ % (base_url, csrf_token)
                global load_content
                load_content = json.loads(self.driver.execute_script(js))
                try:
                    flag_ = load_content["success"]
                except KeyError:
                    load_content["success"] = ""
                if load_content["success"]:
                    break
                elif retry_num == 0:
                    logger.error("店铺 ：%s  在循环访问api获取  %s  数据时第  %d  页失败,重新放入队列..." %
                                 (self.nameShort, flag, page))
                    self.driver.quit()
                    exit(-99)
                time.sleep(1)
            # 解析退/放款数据
            self.resolution(load_content, page, flag)

    # 解析放/退款数据
    def resolution(self, load_content, page, flag):
        message_list = load_content["data"]["modules"][4]["dataSource"]
        if flag == "loan":
            for dic in message_list:
                dic_message = {}
                try:
                    # 放款金额
                    try:
                        dic_message["loanAmt"] = dic["loanAmt"]
                    except KeyError:
                        dic_message["loanAmt"] = ""
                    # 放款时间：
                    try:
                        loan_time = dic["loanTime"]["dates"][0]["timestamp"]
                        dic_message["loanTime"] = str(datetime.datetime.strptime(
                            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(loan_time) / 1000)),
                            "%Y-%m-%d %H:%M:%S") - datetime.timedelta(hours=15))
                    except KeyError:
                        dic_message["loanTime"] = ""
                    # 订单号 ：
                    try:
                        dic_message["parentId"] = dic["parentId"]
                    except KeyError:
                        dic_message["parentId"] = ""
                    # 商品总额 ：
                    try:
                        dic_message["realPaidOrderAmount"] = dic["realPaidOrderAmount"]
                    except KeyError:
                        dic_message["realPaidOrderAmount"] = ""
                    # 平台佣金扣款：
                    try:
                        dic_message["loanEscrowFeeAmt"] = dic["loanEscrowFeeAmt"]
                    except KeyError:
                        dic_message["loanEscrowFeeAmt"] = ""
                    # 联盟佣金扣款：
                    try:
                        dic_message["loanAffiliateFeeAmt"] = dic["loanAffiliateFeeAmt"]
                    except KeyError:
                        dic_message["loanAffiliateFeeAmt"] = ""
                    # 商品ID：
                    try:
                        dic_message["productId"] = dic["productId"]
                    except KeyError:
                        dic_message["productId"] = ""
                    # 商品编码：
                    try:
                        dic_message["productCode"] = dic["productCode"]
                    except KeyError:
                        dic_message["productCode"] = ""
                    # 商品数量
                    try:
                        dic_message["productCount"] = dic["productCount"]
                    except KeyError:
                        dic_message["productCount"] = ""
                    # 下单时间
                    try:
                        ordercreate_time = dic["orderCreateTime"]["dates"][0]["timestamp"]
                        dic_message["orderCreateTime"] = str(datetime.datetime.strptime(
                            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(ordercreate_time) / 1000)),
                            "%Y-%m-%d %H:%M:%S") - datetime.timedelta(hours=15))
                    except KeyError:
                        dic_message["orderCreateTime"] = ""
                    # 付款时间
                    try:
                        pay_time = dic["payTime"]["dates"][0]["timestamp"]
                        dic_message["payTime"] = str(datetime.datetime.strptime(
                            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(pay_time) / 1000)),
                            "%Y-%m-%d %H:%M:%S") - datetime.timedelta(hours=15))
                    except KeyError:
                        dic_message["payTime"] = ""
                    # 商品名称
                    try:
                        dic_message["productName"] = dic["productName"]
                    except KeyError:
                        dic_message["productName"] = ""
                    self.loan_message.append(dic_message)
                except Exception:
                    logger.error(
                        "店铺 : %s  解析第  %d  页  %s  数据时错误...请检查出错json：%s,,重入队列 .... " % (
                            self.nameShort, page, flag, dic))
                    self.driver.quit()
                    exit(-99)
        else:
            for dic in message_list:
                dic_message = {}
                try:
                    # 退款总额
                    try:
                        dic_message["refundAmt"] = dic["refundAmt"]
                    except KeyError:
                        dic_message["refundAmt"] = ""
                        # 退款时间
                    try:
                        refund_time = dic["refundTime"]["dates"][0]["timestamp"]
                        dic_message["refundTime"] = str(datetime.datetime.strptime(
                            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(refund_time) / 1000)),
                            "%Y-%m-%d %H:%M:%S") - datetime.timedelta(hours=15))
                    except KeyError:
                        dic_message["refundTime"] = ""
                    # 订单号
                    try:
                        dic_message["orderId"] = dic["orderId"]
                    except KeyError:
                        dic_message["orderId"] = ""
                    # 退款出资方
                    try:
                        dic_message["refundSponsor"] = dic["refundSponsor"]
                    except KeyError:
                        dic_message["refundSponsor"] = ""
                    # 商品总额
                    try:
                        dic_message["realPaidOrderAmount"] = dic["realPaidOrderAmount"]
                    except KeyError:
                        dic_message["realPaidOrderAmount"] = ""
                    # 平台佣金退回
                    try:
                        dic_message["refundEscorwFeeAmt"] = dic["refundEscorwFeeAmt"]
                    except KeyError:
                        dic_message["refundEscorwFeeAmt"] = ""
                    # 联盟佣金退回
                    try:
                        dic_message["refundAffiliateFeeAmt"] = dic["refundAffiliateFeeAmt"]
                    except KeyError:
                        dic_message["refundAffiliateFeeAmt"] = ""
                    # 商品ID
                    try:
                        dic_message["productId"] = dic["productId"]
                    except KeyError:
                        dic_message["productId"] = ""
                    # 商品编码
                    try:
                        dic_message["productCode"] = dic["productCode"]
                    except KeyError:
                        dic_message["productCode"] = ""
                    # 商品数量
                    try:
                        dic_message["productCount"] = dic["productCount"]
                    except KeyError:
                        dic_message["productCount"] = ""
                    # 下单时间
                    try:
                        ordercreate_time = dic["orderCreateTime"]["dates"][0]["timestamp"]
                        dic_message["orderCreateTime"] = str(datetime.datetime.strptime(
                            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(ordercreate_time) / 1000)),
                            "%Y-%m-%d %H:%M:%S") - datetime.timedelta(hours=15))
                    except KeyError:
                        dic_message["orderCreateTime"] = ""
                    # 付款时间：
                    try:
                        pay_time = dic["payTime"]["dates"][0]["timestamp"]
                        dic_message["payTime"] = str(datetime.datetime.strptime(
                            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(pay_time) / 1000)),
                            "%Y-%m-%d %H:%M:%S") - datetime.timedelta(hours=15))
                    except KeyError:
                        dic_message["payTime"] = ""
                    # 商品名称：
                    try:
                        dic_message["productName"] = dic["productName"]
                    except KeyError:
                        dic_message["productName"] = ""
                    self.refund_message.append(dic_message)
                except Exception:
                    logger.error("店铺 : %s  解析第  %d  页  %s  数据时错误...请检查json: %s ,,重入队列 .... " % (
                        self.nameShort, page, flag, dic))
                    self.driver.quit()
                    exit(-99)

    def ready_link_oa(self):
        items = dict()
        items["browserName"] = self.nameShort
        items["createPerson"] = "爬虫"
        items["message"] = self.loan_message
        items['flag'] = 'loan'
        if self.loan_message:
            items["status"] = "0"
        else:
            items["status"] = "1"
        # 分解数据量
        # logger.info(json.dumps(items,ensure_ascii=False))
        loan_lenth = len(self.loan_message)
        if loan_lenth > params.max_oa_num:
            fenjie_content(items, loan_lenth, self.nameShort)
        else:
            common.link_oa(items)
        # 退款
        item = copy.deepcopy(items)
        if self.refund_message:
            item["status"] = "0"
        else:
            item["status"] = "1"
        item['flag'] = 'refund'
        item["message"] = self.refund_message
        # logger.info(json.dumps(item, ensure_ascii=False))
        refund_lenth = len(self.refund_message)
        if refund_lenth > params.max_oa_num:
            fenjie_content(item, refund_lenth, self.nameShort)
        else:
            common.link_oa(item)


def fenjie_content(content, lenth, nameShort):
    link_num = round(lenth / params.max_oa_num)
    for i in range(link_num):
        if i == link_num - 1:
            content_message = content["message"][i * params.max_oa_num:]
        else:
            content_message = content["message"][i * params.max_oa_num:(i + 1) * params.max_oa_num]
        content_copy = copy.deepcopy(content)
        content_copy["message"] = content_message
        logger.info("店铺 : %s  第  %d 次传输量为 : %d   条" % (nameShort, i + 1, len(content_message)))
        common.link_oa(content_copy)
        time.sleep(1)


def save_storeName(nameShort):
    with open(os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'foo', 'spiderMsg',
                           '%s_storeName.txt' % spider_name), 'a',
              encoding='utf-8') as fp:
        fp.write(nameShort + '\n')


def main():
    if len(sys.argv) is 5:
        list_item_data = json.loads(sys.argv[1])
        start_browser_result = json.loads(sys.argv[2])
        user_info = json.loads(sys.argv[3])
        xhr_data_path = sys.argv[4]
        # 使用driver访问店铺并采集相应信息
        browserOauth = list_item_data['browserOauth']
        nameShort = list_item_data['browserName']
        url = start_browser_result.get("launcherPage")
        port = start_browser_result.get("debuggingPort")
        print(browserOauth, nameShort, url, port)
        mainspider = MainSpider(browserOauth, nameShort, url, port)
        # 登录执行至订单页
        mainspider.start_browser()
        # 放款数据收集
        mainspider.load_refund_money("loan")
        # 退款数据收集
        mainspider.load_refund_money("refund")

        # 准备调用OA进行传输
        # logger.info(mainspider.loan_message)
        # logger.info(mainspider.refund_message)
        if params.link_oa_enabled:
            mainspider.ready_link_oa()
        # 保存店铺名至storeName文本,方便后续做增量爬取
        save_storeName(nameShort)
        mainspider.driver.quit()
        exit(1000)
    else:
        exit(-1)


if __name__ == "__main__":
    main()
