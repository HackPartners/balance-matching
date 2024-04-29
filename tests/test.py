import json
import os
import warnings

# import curlify

import logging
import requests


def main():

    # Local URL
    url = "http://localhost:4000"
    # scan_name = "ANG2304_00051"

    send_data = {"match": True}

    headers = {'Content-type': 'application/json'}
    response = requests.post(url+"/post/json/", headers=headers, data=json.dumps(send_data))

    # r is the response object from the requests library.
    # print(curlify.to_curl(requests.post(url+"/post/json/", headers=headers, data=json.dumps(send_data)).request))

    # Check response:
    if response.status_code == 200:
        print(f"Have a response. 200")
    else:
        print(f"Bad response code: {response.status_code}")


if __name__ == "__main__":
    main()
