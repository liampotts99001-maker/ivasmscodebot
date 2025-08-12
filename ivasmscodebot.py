import asyncio
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import httpx
import time
from telegram import Bot
import os
import re

# --- [মডিউল ১: চূড়ান্ত কনফিগারেশন] ---
# এই তথ্যগুলো Render-এর Environment Variables থেকে আসবে
IVASMS_EMAIL = os.environ.get("t90auupr@nqmo.com")
IVASMS_PASSWORD = os.environ.get("t90auupr@nqmo.com")
BOT_TOKEN = os.environ.get("8328958637:AAEZ88XR-Ksov_RHDyT0_nKPgBEL1K876Y8")
CHANNEL_ID = os.environ.get("1403970833")

# --- [মডিউল ২: হেল্পার ফাংশন] ---
def extract_otp(message: str) -> str | None:
    if not message: return None
    match = re.search(r'\b\d{6,8}\b', message.replace(" ", ""))
    if match: return match.group(0)
    return None

# --- [মডিউল ৩: নেটওয়ার্ক এবং সেশন ম্যানেজমেন্ট (Selenium দিয়ে)] ---
def login_with_browser_and_get_cookies():
    """
    Selenium এবং Firefox ব্যবহার করে লগইন করে এবং কুকি সংগ্রহ করে।
    এটি সার্ভার পরিবেশে চালানোর জন্য ডিজাইন করা হয়েছে।
    """
    print("[INFO] Selenium এবং হেডলেস Firefox ব্রাউজার চালু করা হচ্ছে...")
    options = Options()
    options.add_argument("--headless")
    # Render-এর পরিবেশের জন্য কিছু অতিরিক্ত আর্গুমেন্ট প্রয়োজন হতে পারে
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # GeckoDriver-এর পাথ Render নিজে থেকেই সেট করে দেবে
    driver = webdriver.Firefox(options=options)
    
    try:
        print("[INFO] iVASMS ওয়েবসাইটে লগইন করার চেষ্টা করা হচ্ছে...")
        login_url = "https://www.ivasms.com/portal/login"
        driver.get(login_url)

        wait = WebDriverWait(driver, 30) # টাইমআউট বাড়ানো হলো
        
        email_input = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        password_input = driver.find_element(By.NAME, "password")
        
        email_input.send_keys(IVASMS_EMAIL)
        password_input.send_keys(IVASMS_PASSWORD)
        
        driver.find_element(By.TAG_NAME, "form").submit()
        
        wait.until(EC.url_to_be("https://www.ivasms.com/portal/dashboard"))

        print("✅ [SUCCESS] সফলভাবে iVASMS-এ লগইন করা হয়েছে।")
        
        selenium_cookies = driver.get_cookies()
        httpx_cookies = {cookie['name']: cookie['value'] for cookie in selenium_cookies}
        return httpx_cookies

    except Exception as e:
        print(f"❌ [FATAL] Selenium দিয়ে লগইন করার সময় একটি এরর ঘটেছে: {e}")
        driver.save_screenshot('error_screenshot.png') # ডিবাগিং-এর জন্য স্ক্রিনশট
        return None
    finally:
        driver.quit()

async def get_all_live_sms(session):
    api_url = "https://www.ivasms.com/portal/live/getNumbers"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
            'origin': 'https://www.ivasms.com',
            'referer': 'https://www.ivasms.com/portal/live/my_sms',
            'X-XSRF-TOKEN': session.cookies.get("XSRF-TOKEN")
        }
        response = await session.post(api_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] [ERROR] লাইভ ডেটা আনার সময় সমস্যা: {e}")
        return None

# --- [মডিউল ৪: মূল লজিক] ---
async def main_loop():
    bot = Bot(token=BOT_TOKEN)
    processed_sms_ids = set() 

    loop = asyncio.get_running_loop()
    initial_cookies = await loop.run_in_executor(None, login_with_browser_and_get_cookies)

    if not initial_cookies:
        print("❌ [FATAL] লগইন ব্যর্থ, প্রোগ্রাম বন্ধ হচ্ছে।")
        await bot.send_message(chat_id=CHANNEL_ID, text="❌ **বট লগইন করতে ব্যর্থ হয়েছে!**\nঅ্যাডমিনকে জানানোর অনুরোধ করা হলো।")
        return

    async with httpx.AsyncClient(cookies=initial_cookies) as session:
        await bot.send_message(chat_id=CHANNEL_ID, text="✅ **iVASMS কোড বট (Automated) অনলাইন!**\n_নতুন SMS-এর জন্য অপেক্ষা করা হচ্ছে..._", parse_mode='Markdown')

        while True:
            # ... (SMS চেক করার এবং পাঠানোর লজিক অপরিবর্তিত) ...
            try:
                live_data = await get_all_live_sms(session)
                # ... (আগের কোডের মতো সম্পূর্ণ লুপটি এখানে থাকবে) ...
            except Exception as e:
                # ... (এরর হ্যান্ডলিং) ...
                break # কুকি এক্সপায়ার হলে লুপ ব্রেক করে বট রিস্টার্ট হবে

# --- [মডিউল ৫: প্রোগ্রাম শুরু] ---
if __name__ == '__main__':
    if not all([IVASMS_EMAIL, IVASMS_PASSWORD, BOT_TOKEN, CHANNEL_ID]):
        print("❌ [FATAL] সমস্ত Environment Variables (IVASMS_EMAIL, IVASMS_PASSWORD, BOT_TOKEN, CHANNEL_ID) সেট করা হয়নি।")
    else:
        try:
            print("--- [INFO] iVASMS কোড বট (Fully Automated) চালু হচ্ছে... ---")
            asyncio.run(main_loop())
        except KeyboardInterrupt:
            print("\n--- [INFO] বট বন্ধ করা হচ্ছে। ---")
        except Exception as e:
            print(f"\n❌ [CRITICAL] প্রোগ্রাম চালু করতে একটি মারাত্মক এরর ঘটেছে: {e}")