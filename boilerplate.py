from woocommerce import API
import json
import razorpay
from os.path import join, dirname
import pandas as pd
from time import sleep
from datetime import datetime
from extlogger import ExecutionReport
import sys


outputfile = lambda: datetime.now().date().__str__() + '.txt'
setup_file_path = join(dirname(__file__), "jalsokaro.json")


def redirect_to_file(text):
    with open(outputfile(), 'a') as f:
        f.writelines([text])
        f.flush()
        print(text)

# Razor Pay

# LIVE
# "rzp_live_Ja00y9xvqXKhJ3"
# "WdWlbuVh7I4QukS8wfybM3GA"

# TEST
# "rzp_test_VZny70aeOf01QB"
# "cCGSiGBIjEQucB46BX4rQK7M"


class MyWooCom(API):

    def __init__(self, init_file=setup_file_path):
        self.init_file = init_file

        self.consumer_key = self.read_key_from_settings('consumer_key')
        self.consumer_secret = self.read_key_from_settings("consumer_secret")

        self.consumer_key = self.read_key_from_settings("consumer_key")
        if self.consumer_key is None:
            self.consumer_key = input("What is your app's consumer_key:  ")
            self.write_key_to_settings("consumer_key", self.consumer_key)

        self.consumer_secret = self.read_key_from_settings("consumer_secret")
        if self.consumer_secret is None:
            self.consumer_secret = input("What is your app's consumer_secrett:  ")
            self.write_key_to_settings("consumer_secret", self.consumer_secret)

        self.url = self.read_key_from_settings("url")
        if self.url is None:
            self.url = input("What is your app's url:  ")
            self.write_key_to_settings("url", self.url)

        super().__init__(url=self.url,
                         consumer_key=self.consumer_key,
                         consumer_secret=self.consumer_secret,
                         query_string_auth=True,
                         verify_ssl=True)

    def write_key_to_settings(self, key, value):
        try:
            file = open(self.init_file, "r")
        except IOError:
            data = {}
            with open(self.init_file, "w") as output_file:
                json.dump(data, output_file)
        file = open(self.init_file, "r")
        try:
            data = json.load(file)
        except Exception:
            data = {}
        data[key] = value
        with open(self.init_file, "w") as output_file:
            json.dump(data, output_file)

    def read_key_from_settings(self, key):
        try:
            file = open(self.init_file, "r")
        except IOError:
            file = open(self.init_file, "w")
        file = open(self.init_file, "r")
        try:
            data = json.load(file)
            return data[key]
        except Exception:
            pass
        return None

    def complete(self, cid: int):
        endpoint = f'orders/{str(cid)}'
        self.post(endpoint, data={"status": "completed"})
        redirect_to_file(f"Completed order {cid}\n")


class MyRazorPay(razorpay.Client):

    def __init__(self, init_file=setup_file_path):

        self.init_file = init_file
        self.key_id = self.read_key_from_settings("key_id")
        if self.key_id is None:
            self.key_id = input("What is your app's key_id:  ")
            self.write_key_to_settings("key_id", self.key_id)

        self.key_secret = self.read_key_from_settings("key_secret")
        if self.key_secret is None:
            self.key_secret = input("What is your app's key_secret:  ")
            self.write_key_to_settings("key_secret", self.key_secret)

        self.last_order_timestamp = self.read_key_from_settings("last_order_timestamp")
        if self.last_order_timestamp is None:
            self.last_order_timestamp = input("What is your app's last_order_timestamp:  ")
            self.write_key_to_settings("last_order_timestamp", self.last_order_timestamp)

        super().__init__(auth=(self.key_id, self.key_secret))

    def write_key_to_settings(self, key, value):
        try:
            file = open(self.init_file, "r")
        except IOError:
            data = {}
            with open(self.init_file, "w") as output_file:
                json.dump(data, output_file)
        file = open(self.init_file, "r")
        try:
            data = json.load(file)
        except Exception:
            data = {}
        data[key] = value
        with open(self.init_file, "w") as output_file:
            json.dump(data, output_file)

    def read_key_from_settings(self, key):
        try:
            file = open(self.init_file, "r")
        except IOError:
            file = open(self.init_file, "w")
        file = open(self.init_file, "r")
        try:
            data = json.load(file)
            return data[key]
        except Exception:
            pass
        return None

    def check_new_payments(self):
        ids = list()
        req = self.payment.fetch_all({"count": 100, "from": int(self.last_order_timestamp)+1})
        payments = req['items']
        if not payments:
            return False
        df = pd.DataFrame(payments)
        self.last_order_timestamp = max(df.created_at.astype(int))
        self.write_key_to_settings("last_order_timestamp", self.last_order_timestamp)
        captured = df[df.status.isin(['captured'])]
        midway = df[~df.status.isin(['captured', 'failed'])]
        if len(midway):
            redirect_to_file(f"Orders Midway {midway.notes.values}")
            self.last_order_timestamp = min(midway.created_at.astype(int)) - 1
        for record in captured.notes:
            try:
                wid = record['woocommerce_order_id']
                ids.append(wid)
            except KeyError:
                pass

        return ids


class JalsoKaro(object):
    def __init__(self):
        self.mwc = MyWooCom()
        self.mrp = MyRazorPay()
        self.sync()

    def sync(self):
        while True:
            unsyncd = self.mrp.check_new_payments()
            if unsyncd:
                for wid in unsyncd:
                    self.mwc.complete(wid)
            sleep(30)


if __name__ == '__main__':

    excrep = ExecutionReport(__file__)

    try:
        jk = JalsoKaro()
    except Exception as e:
        exc_info = sys.exc_info()
        excrep.submit(*exc_info)
        del exc_info

