import sys
import os
import time
import json
import ast
import requests
import re
import threading
from suds.client import Client
from functools import wraps
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

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
        self.retry_num = 3
        self.account_message = {"browserName": self.nameShort}
        # self.service = Service("../crawlers/chromedriver74.exe")
        # self.service.command_line_args()
        # self.service.start()
        options = webdriver.ChromeOptions()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:{}".format(port))
        self.driver = webdriver.Chrome(options=options, executable_path=params.chrome_cpu)
        self.driver.implicitly_wait(10)
        self.driver.set_page_load_timeout(120)
        self.driver.maximize_window()

    def get_index_url(self):
        t1 = time.time()
        try:
            self.driver.get(self.url)
        except Exception:
            logger.error("店铺 ：%s  打开首页超时...." % self.nameShort)
            self.driver.quit()
            exit(-99)
        logger.info("打开店铺 : %s 首页用时 %d 秒......" % (self.nameShort, int(time.time() - t1)))

    def send_sms(self, sms_capture_list):
        # 循环发送验证码
        sms_success = False
        for sms in sms_capture_list:
            try:
                input_sms_ele = self.driver.find_element_by_xpath("//input[@class='tfa_input']")
                input_sms_ele.clear()
                input_sms_ele.send_keys(sms)
                button_submit = self.driver.find_element_by_xpath(
                    "//button[@class='btn btn-primary btn-block two_factor_submit']")
                ActionChains(self.driver).move_to_element(button_submit).perform()
                self.driver.execute_script("arguments[0].click()", button_submit)
            except Exception:
                logger.error("店铺 ： %s 发送验证码时出错, 重入队列" % self.nameShort)
                self.quit()
            # 等待是否出现error提示验证码错误
            time.sleep(10)
            error_sms_list = self.driver.find_elements_by_xpath("//a[@id='error-btn']")
            if error_sms_list:
                ActionChains(self.driver).move_to_element(error_sms_list[0]).perform()
                self.driver.execute_script("arguments[0].click()", error_sms_list[0])
                continue
            # 判断是否验证成功
            current_url = self.driver.current_url
            if "login" not in current_url:
                sms_success = True
                logger.info("店铺 : %s 短信验证成功.." % self.nameShort)
                break
            else:
                continue
        return sms_success

    def click_send_sms(self):
        # 点击发送按钮
        try:
            resend_sms_ele = self.driver.find_element_by_xpath("//a[@class='tfa_resend']")
            ActionChains(self.driver).move_to_element(resend_sms_ele).perform()
            self.driver.execute_script("arguments[0].click()", resend_sms_ele)
        except Exception as e:
            logger.error("店铺 : %s  未找到发送短信按钮,退出" % self.nameShort)
            self.quit()
        # 关闭点击发送成功后的弹窗
        time.sleep(7)
        try:
            success_alert = self.driver.find_element_by_xpath(
                "//div[@class='modal hide fade in']/div[@class='modal-footer']/a")
            ActionChains(self.driver).move_to_element(success_alert).perform()
            self.driver.execute_script("arguments[0].click()", success_alert)
        except Exception:
            logger.info("店铺 : %s  点击重新发送短信后未找到弹窗...重入队列" % self.nameShort)
            pass

    def wcf_client(self, items, num):
        retries = 5
        while retries:
            retries -= 1
            try:
                client = Client(params.sms_oa_api)
                client.set_options(timeout=600)
                if num == 1:
                    result_msg = client.service.GetFnSmtDevicePhoneTask('1Dij+5Ck6HcV4oZF4ngPKR0z9zQK2F13pzO0lE3lzfw=',
                                                                        items)
                elif num == 2:
                    result_msg = client.service.GetFnSmtDevicePhoneStatus(
                        '1Dij+5Ck6HcV4oZF4ngPKR0z9zQK2F13pzO0lE3lzfw=', items)
                elif num == 3:
                    result_msg = client.service.GetFnSmsDecicePhone(
                        '1Dij+5Ck6HcV4oZF4ngPKR0z9zQK2F13pzO0lE3lzfw=', items)
                else:
                    result_msg = ""
                return result_msg
            except Exception as e:
                logger.error("店铺 : %s  wcf_client  error : %s" % (self.nameShort, e))
        self.quit()

    def get_phone_first_step(self):
        try:
            result_msg = self.wcf_client(self.nameShort, 1)
            logger.info("店铺 ： %s  第 1 步获取手机号返回信息: %s" % (self.nameShort, result_msg))
            content = json.loads(result_msg)
            if not content["Success"]:
                logger.info("店铺 ： %s  第 1 步调用接口失败." % self.nameShort)
                self.get_phone_first_step()
            if content["status"] == "3":
                logger.info("店铺 : %s 第 1 步获取手机号失败." % self.nameShort)
                self.quit()
            phone_number = content["phone"]
            return phone_number
        except Exception as e:
            logger.error("店铺: %s  get_phone_first_step  error : %s" % (self.nameShort, e))
            self.quit()

    def get_ready_status_second_step(self, phone_number):
        # 此步需要循环访问
        retries_times = 40
        while retries_times:
            retries_times -= 1
            if retries_times == 0:
                logger.warning("店铺  ： %s  第 2 步获取机器就绪状态超过次数限制,EXIT" % self.nameShort)
                self.quit()
            try:
                result_msg = self.wcf_client(phone_number, 2)
                logger.info("店铺  ： %s  第 2 步获取机器就绪状态返回信息 : %s " % (self.nameShort, result_msg))
                content = json.loads(result_msg)
                if not content["Success"]:
                    logger.info("店铺 ： %s  第 2 步调用接口失败." % self.nameShort)
                    continue
                if content["status"] == "0":
                    time.sleep(15)
                    continue
                elif content["status"] == "1":
                    logger.info("店铺 : %s 第 2 步机器状态准备就绪,准备第3步" % self.nameShort)
                    break
                else:
                    logger.error("店铺 ： %s  第 2  步获取机器准备状态失败." % self.nameShort)
                    self.quit()
            except Exception as e:
                logger.error("店铺： %s   get_ready_status_second_step  error : %s " % (self.nameShort, e))
                self.quit()

    def get_sms_message_third_step(self, phone_number):
        retries = 20
        while retries:
            time.sleep(5)
            retries -= 1
            try:
                result_msg = self.wcf_client(phone_number, 3)
                logger.info("店铺  ： %s  第 3 步获取短信码返回信息 : %s " % (self.nameShort, result_msg))
                content = json.loads(result_msg)[0]
                if not content["Success"]:
                    logger.info("店铺 ： %s  第 3 步调用接口失败." % self.nameShort)
                    continue
                if content["status"] == "2":
                    sms_list = list()
                    sms_msg_list = content["smtDevicePhones"]
                    if not sms_msg_list:
                        continue
                    sms_msg_list = sorted(sms_msg_list, key=lambda x: x["CreateTime"], reverse=True)
                    for dic in sms_msg_list[:2]:
                        sms_list.append(dic["VerificationCode"].strip())
                    return sms_list
                else:
                    logger.error("店铺 ： %s  第 3  步获取短信码失败." % self.nameShort)
                    self.quit()
            except Exception as e:
                logger.error("店铺： %s   get_sms_message_third_step  error : %s " % (self.nameShort, e))
                self.quit()
        self.quit()

    def sms_verify(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 判断是否出现短信验证
            tfa_ele_list = self.driver.find_elements_by_xpath("//div[@class='tfa_container']")
            if tfa_ele_list:
                logger.info("店铺 : %s  存在二步验证..." % self.nameShort)
                # 判断是否存在短信验证
                sms_ele_list = self.driver.find_elements_by_xpath("//div[@id='tfa-tab-phone']/div/a")
                if sms_ele_list:
                    logger.info("店铺 : %s  存在短信验证..." % self.nameShort)
                    ActionChains(self.driver).move_to_element(sms_ele_list[0]).perform()
                    self.driver.execute_script("arguments[0].click()", sms_ele_list[0])
                    time.sleep(5)
                    # 判断是否切换到短信验证
                    times = 0
                    while True:
                        times += 1
                        sms_ele = self.driver.find_element_by_xpath("//div[@id='tfa-tab-phone']")
                        sms_ele_class = sms_ele.get_attribute("class")
                        if "tfa-tab-active" not in sms_ele_class:
                            sms_ele = self.driver.find_element_by_xpath("//div[@id='tfa-tab-phone']")
                            ActionChains(self.driver).move_to_element(sms_ele).click().perform()
                        else:
                            break
                        if times == 3:
                            logger.error("店铺 : %s 切换至短信验证窗口失败." % self.nameShort)
                            self.quit()
                        time.sleep(5)

                    # 第一步通过OA获取手机号
                    time.sleep(2)
                    phone_number = self.get_phone_first_step()
                    # 第二步通过OA获取接收短信机器是否准备就绪
                    self.get_ready_status_second_step(phone_number)
                    # 点击发送短信验证码
                    self.click_send_sms()
                    # 第三步获取验证码
                    sms_list = self.get_sms_message_third_step(phone_number)
                    # 发送获取的验证码进行页面验证
                    result_msg = self.send_sms(sms_list)
                    if not result_msg:
                        logger.info("店铺 ：%s  输入短信验证失败.退出" % self.nameShort)
                        self.quit()
                else:
                    logger.info("店铺 ： %s  只存在二维码验证...退出" % self.nameShort)
                    self.quit()
            else:
                logger.info("店铺: %s  不需要进行二步验证..." % self.nameShort)

            return func(self, *args, **kwargs)

        return wrapper

    def quit(self):
        self.driver.quit()
        exit(-99)

    def select_language(self):
        global account_ele
        try:
            ActionChains(self.driver).move_by_offset(200, 100).double_click().perform()
            time.sleep(4)
            language_ele = self.driver.find_element_by_xpath("//div[contains(@class,'navButton')]/div/div")
        except Exception:
            logger.info("店铺 :  %s  在首页未找到语言标签,跳过" % self.nameShort)
            return

        # 判断页面是否有弹窗通知
        alert_msg_ele = self.driver.find_elements_by_xpath("//button[contains(@class,'show-on-delay')]")
        if alert_msg_ele:
            ActionChains(self.driver).move_to_element(alert_msg_ele[0]).perform()
            self.driver.execute_script("arguments[0].click()", alert_msg_ele[0])

        # 选择中文
        time.sleep(3)
        ActionChains(self.driver).move_to_element(language_ele).perform()
        option_list = self.driver.find_elements_by_xpath(
            "//div[contains(@class,'optionList')]/div/div/div[contains(@class,'textContainer')]/section")
        for section in option_list:
            section_text = section.text.strip()
            if section_text == "中文":
                ActionChains(self.driver).move_to_element(section).perform()
                self.driver.execute_script("arguments[0].click()", section)
                break

    def start_browser(self):
        # 判断首页是否为登录页
        if "login" in self.driver.current_url:
            self.driver.execute_script("window.__AUTO_FILL_UP__();")
            time.sleep(5)
            try:
                login_ele = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//button[@class='btn btn-large btn-primary btn-login']/span")))
                ActionChains(self.driver).move_to_element(login_ele).perform()
                self.driver.execute_script("arguments[0].click()", login_ele)
            except Exception:
                logger.error("店铺： %s  在登录首页未找到登录按钮...重入队列" % self.nameShort)
                self.quit()

    @sms_verify
    def index(self):
        global account_ele
        # 等待进入首页
        try:
            account_ele = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//li[@id='menu-account']/a")))
        except Exception:
            logger.error("店铺 : %s 进入首页超时...重新入队" % self.nameShort)
            self.quit()

        # 选择语言
        self.select_language()
        time.sleep(8)
        try:
            account_ele = self.driver.find_element_by_xpath("//li[@id='menu-account']/a")
            ActionChains(self.driver).move_to_element(account_ele).perform()
            self.driver.execute_script("arguments[0].click()", account_ele)
        except Exception:
            logger.error("店铺  : %s 在选择完语言后点击账户出错...重入队列" % self.nameShort)
            self.quit()

        # 选择付款设置
        account_list = self.driver.find_elements_by_xpath("//li[@id='menu-account']/ul/li/a")
        payment_setting_flag = False
        for ele in account_list:
            a_href = ele.get_attribute("href")
            if a_href and "payment-settings" in a_href:
                payment_setting_flag = True
                ActionChains(self.driver).move_to_element(ele).perform()
                self.driver.execute_script("arguments[0].click()", ele)
                break

        return payment_setting_flag

    @sms_verify
    def resend_username(self, num):
        # 等待页面加载完成
        try:
            try:
                login_submit = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@id='login-form']/div[@class='inputs']/button")))
                # self.driver.execute_script("arguments[0].style.marginBottom = 0px;", login_submit)
                # self.driver.execute_script("window.__AUTO_FILL_UP__();")
                # time.sleep(5)
                ActionChains(self.driver).move_to_element(login_submit).perform()
                self.driver.execute_script("arguments[0].click()", login_submit)
                time.sleep(5)
            except Exception:
                self.driver.refresh()
                if num < 5:
                    num += 1
                    return self.resend_username(num)
                logger.error("店铺 : %s  通过付款设置也进入重新填写账号密码页超过失败次数...重入队列" % self.nameShort)
                self.quit()
        except Exception:
            logger.error("店铺 : %s  通过付款设置也进入重新填写账号密码页超时...重入队列" % self.nameShort)
            self.quit()

    @sms_verify
    def get_message(self):
        global pay_platform
        global payments_paidto_ele1
        global account_id
        # 判断是否出现弹窗完善账户信息
        try:
            alert_button = WebDriverWait(self.driver, 7).until(
                EC.presence_of_element_located((By.XPATH, "//button[@id='agree-button']")))
            ActionChains(self.driver).move_to_element(alert_button).perform()
            self.driver.execute_script("arguments[0].click()", alert_button)
            time.sleep(5)
        except Exception:
            pass
        # 等待页面加载完成
        try:
            WebDriverWait(self.driver, 60).until(EC.presence_of_element_located((By.XPATH, "//div[@id='change-info']")))
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//div[@id='currency-area']")))
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//table[@id='current-provider-table']")))
        except Exception as e:
            logger.error("店铺 : %s  在进入付款设置页时超时...重入队列%s" % (self.nameShort, e))
            self.quit()
        logger.info("店铺: %s  成功进入付款设置页，准备采集..." % self.nameShort)
        # 将所有内容标签展开
        change_info_ele = self.driver.find_elements_by_xpath("//div[@id='change-info']/div[@class='section']")
        for section in change_info_ele:
            self.driver.execute_script("arguments[0].style = 'display: block;';", section)
        time.sleep(2)
        # 收款平台
        pay_platform_ele_list = self.driver.find_elements_by_xpath(
            "//table[@id='current-provider-table']/tbody/tr[contains(@class,'table-row')]")
        pay_platform = ""
        for ele in pay_platform_ele_list:
            ele_style = ele.get_attribute('style')
            logger.info("店铺 : %s style ==%s" % (self.nameShort, ele_style))
            if 'table-row' in ele_style:
                pay_platform = ele.find_element_by_xpath("./td[1]").text
                break
        # 本币代码
        try:
            money_code_ele = self.driver.find_element_by_xpath("//span[contains(@class,'currencyCode')]")
            money_code = money_code_ele.text
        except Exception as e:
            logger.info("店铺 ： %s 获取Currency Exception: %s" % (self.nameShort, e))
            money_code = ""
        if not pay_platform or not money_code:
            if self.retry_num:
                self.retry_num -= 1
                self.driver.refresh()
                return self.get_message()
            logger.error("店铺 ： %s 获取Currency Exception,关键字非法" % self.nameShort)
            self.quit()
        self.retry_num = 3
        # 收款人类型
        try:
            payments_paidto_ele1 = self.driver.find_element_by_xpath(
                "//div[@id='change-info']/div[@class='control-group collector-inputs']/div/div[1]/input")
        except Exception as e:
            logger.error("店铺 : %s 获取收款人类型时出错.%s " % (self.nameShort, e))
            self.quit()
        if payments_paidto_ele1.is_selected():
            payments_paidto = '个人'
        else:
            payments_paidto = '企业'

        # 个人信息
        try:
            full_name_ele = self.driver.find_element_by_xpath(
                "//input[@id='input-personal_name']")
            full_name = full_name_ele.get_attribute('value')
        except Exception as e:
            logger.info("店铺 ： %s 获取full_name Exception: %s" % (self.nameShort, e))
            full_name = ""

        try:
            national_id_ele = self.driver.find_element_by_xpath(
                "//input[@id='input-personal_id_number']")
            national_id = national_id_ele.get_attribute('value')
        except Exception as e:
            logger.info("店铺 ： %s 获取national_id Exception: %s" % (self.nameShort, e))
            national_id = ''
        try:
            phone_number_ele = self.driver.find_element_by_xpath(
                "//input[@id='input-personal_phone_number']")
            phone_number = phone_number_ele.get_attribute('value')
        except Exception as e:
            logger.info("店铺 ： %s 获取phone_number Exception: %s" % (self.nameShort, e))
            phone_number = ""

        # account id
        try:
            account_id_ele = self.driver.find_element_by_xpath(
                "//div[@id='change-info']/div[@class='section']/div/div[@class='controls']/input\
                [contains(@id,'account_id')]")
            account_id = account_id_ele.get_attribute('value')
        except Exception as e:
            logger.error("店铺 ： %s 获取account_id Exception,关键字非法:ErrorMsg %s" % (self.nameShort, e))
            self.quit()

        create_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        self.account_message["payPlatform"] = pay_platform
        self.account_message['paymentsPaidTo'] = payments_paidto
        self.account_message['fullName'] = full_name
        self.account_message['nationalId'] = national_id
        self.account_message['phoneNumber'] = phone_number
        self.account_message['accountId'] = account_id
        self.account_message['moneyCode'] = money_code
        self.account_message['createTime'] = create_time
        self.account_message['status'] = "0"

    def ready_link_oa(self):
        # 验证采集信息是否合法
        logger.info("店铺 ： %s  的回款信息: %s" % (self.nameShort, self.account_message))
        common.link_oa(self.account_message)


def saveStoreName(nameShort):
    with open(os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'foo', 'spiderMsg',
                           '%s_storeName.txt' % spider_name), 'a', encoding='utf-8') as fp:
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
        mainspider = MainSpider(browserOauth, nameShort, url, port)
        # 打开店铺
        mainspider.get_index_url()
        # 登录
        mainspider.start_browser()
        # 进入首页，返回结果BOOL是否有付款设置项
        payment_setting_flag = mainspider.index()
        if not payment_setting_flag:
            logger.info("店铺 : %s  的账户下拉列表中未找到付款设置,重入队列" % nameShort)
            mainspider.quit()
        else:
            # 进入重新填写账号密码页
            mainspider.resend_username(1)
            # 采集信息
            mainspider.get_message()
        # 调用OA传输
        if params.link_oa_enabled:
            mainspider.ready_link_oa()
        # 采集完成后保存店铺名并传输OA
        saveStoreName(nameShort)
        exit(1000)

    else:
        exit(-1)


if __name__ == "__main__":
    main()
