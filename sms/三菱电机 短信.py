""" Customize the sms module """
from urllib.parse import urlencode
import requests
from common.utils import get_logger
from requests import RequestException

logger = get_logger(__file__)

def send_sms(phone_numbers, code_params, *args, **kwargs):
    logger.error('三菱电机短信认证！')
    mobile = phone_numbers[3:]
    params = {
        "account": "sanlingdianjikt-tz",  # 应用ID
        "password": "9D2B00",  # 应用密码
        "mobile": mobile,  # 手机号
        "content": f"您正在登录RAS系统，验证码：{code_params}，切勿将验证码泄露于他人，本条验证码有效期5分钟。【三菱电机空调】"
    }
    base_url = "http://api.chanzor.com/send?"
    full_url = base_url + urlencode(params, encoding='utf-8')
    try:
        response = requests.get(url=full_url)
        if response.json()["status"] != 0:
            return True
        else:
            logger.error(response.json())
    except RequestException as e:
        logger.error(e, exc_info=True)
        return False

