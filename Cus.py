import os
import requests
import time
from urllib.parse import quote

# কালার কোড
red = '\033[1;31m'
green = '\033[1;32m'
yellow = '\033[1;33m'
white = '\033[1;37m'
reset = '\033[0m'

def banner():
    os.system('clear')
    print(f"""
{green}  ____  _   _ _   _ _   _  ___  __  __ 
 / ___|| | | | | | | | | |/ _ \|  \/  |
 \___ \| |_| | | | | | | | | | | |\/| |
  ___) |  _  | |_| | \_ /| |_| | |  | |
 |____/|_| |_|\___/   \_/  \___/|_|  |_|
    {yellow}Coded By: Shuvom | Version: 1.0{reset}
    """)

def send_sms(number, msg):
    encoded_msg = quote(msg)
    api_url = f"http://xlahr.pro.bd/api/api.php?number={number}&msg={encoded_msg}"
    
    try:
        print(f"\n{yellow}[*] Sending SMS...{reset}")
        response = requests.get(api_url)
        if response.status_code == 200:
            print(f"{green}[+] Success! SMS Sent to {number}{reset}")
        else:
            print(f"{red}[-] Server Error! Code: {response.status_code}{reset}")
    except Exception as e:
        print(f"{red}[-] Error: {str(e)}{reset}")

def main():
    while True:
        banner()
        print(f"{white}[1] Send Custom SMS")
        print(f"{white}[2] About Developer")
        print(f"{white}[0] Exit")
        
        choice = input(f"\n{green}Select Option >> {reset}")
        
        if choice == '1':
            num = input(f"{yellow}Enter Number: {reset}")
            message = input(f"{yellow}Enter Message: {reset}")
            if num and message:
                send_sms(num, message)
                input(f"\n{white}Press Enter to continue...{reset}")
            else:
                print(f"{red}Invalid Input!{reset}")
                time.sleep(2)
        
        elif choice == '2':
            banner()
            print(f"{green}Developer: Shuvom")
            print(f"Specialist: System Breach | Proxy Manipulation")
            input(f"\n{white}Press Enter to return menu...{reset}")
            
        elif choice == '0':
            print(f"{green}Thanks for using! Goodbye.{reset}")
            break
        else:
            print(f"{red}Wrong Option!{reset}")
            time.sleep(1)

if __name__ == "__main__":
    main()
