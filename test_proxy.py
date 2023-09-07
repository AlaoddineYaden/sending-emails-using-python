# import socket
# import requests
# import logging
# from concurrent.futures import ThreadPoolExecutor
# from requests.exceptions import RequestException
# from fake_useragent import UserAgent
# import socks

# logging.basicConfig(filename='proxy_test.log', level=logging.INFO)

# def test_proxy(proxy):
#     try:
#         ua = UserAgent()
#         headers = {'User-Agent': ua.random}
        
#         socks.set_default_proxy(socks.SOCKS4, proxy.split(':')[0], int(proxy.split(':')[1]))
#         socket.socket = socks.socksocket
        
#         response = requests.get('https://www.google.com', headers=headers, timeout=20)
#         if response.status_code == 200:
#             return True
#     except RequestException as e:
#         logging.error(f'Proxy test failed for {proxy}: {str(e)}')
#         print(f'Proxy test failed for {proxy}')
#     return False

# def save_working_proxies(input_file, output_file):
#     with open(input_file, 'r') as file:
#         proxies = file.read().splitlines()

#     working_proxies = []
#     with ThreadPoolExecutor(max_workers=10) as executor:
#         futures = [executor.submit(test_proxy, proxy) for proxy in proxies]

#         for future, proxy in zip(futures, proxies):
#             if future.result():
#                 working_proxies.append(proxy)
#                 logging.info(f'Saved working proxy: {proxy}')
#                 print(f'Saved working proxy: {proxy}')

#     with open(output_file, 'w') as file:
#         file.write('\n'.join(working_proxies))

# # Example usage
# input_file = 'proxies.txt'
# output_file = 'working_proxies.txt'

# save_working_proxies(input_file, output_file)








################################### test http proxy 


import random
import time
import requests
import logging
from concurrent.futures import ThreadPoolExecutor
from requests.exceptions import RequestException
from fake_useragent import UserAgent
from dotenv import load_dotenv
import os

load_dotenv()


logging.basicConfig(filename='proxy_test.log', level=logging.INFO)

def test_proxy(proxy):
    try:
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        response = requests.get('https://www.google.com', proxies={'http': proxy, 'https': proxy}, headers=headers, timeout=10)
        if response.status_code == 200:
            return True
    except RequestException as e:
        logging.error(f'Proxy test failed for {proxy}: {str(e)}')
        print(f'Proxy test failed for {proxy}')
    return False

def save_working_proxies(input_file, output_file):
    with open(input_file, 'r') as file:
        proxies = file.read().splitlines()

    # Remove duplicate proxies
    proxies = list(set(proxies))

    working_proxies = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(test_proxy, proxy) for proxy in proxies]

        for future, proxy in zip(futures, proxies):
            if future.result():
                working_proxies.append(proxy)
                logging.info(f'Saved working proxy: {proxy}')
                print(f'Saved working proxy: {proxy}')

    with open(output_file, 'w') as file:
        file.write('\n'.join(working_proxies))

# Example usage
root = os.getenv("root")
input_file = root + os.getenv("proxies_file")
output_file = root + os.getenv("working_proxies_file")

save_working_proxies(input_file, output_file)

