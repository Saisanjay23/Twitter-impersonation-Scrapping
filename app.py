import streamlit as st
import datetime
import pandas as pd
import time
import random
import base64
import contextlib
import io
import undetected_chromedriver as uc
from PIL import Image
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from retrying import retry
import sys
import streamlit as st

st.write("🔍 Running on Python version:", sys.version)


st.set_page_config(page_title="Twitter Impersonation Checker", layout="wide")
st.title("🕵 Twitter/X Impersonation Checker")
st.markdown("Paste up to 20 Twitter profile URLs (one per line) to scrape impersonator data.")

@contextlib.contextmanager
def get_driver(headless=True):
    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--high-dpi-support=1")
        options.add_argument("--force-device-scale-factor=1")
        if headless:
            options.add_argument("--headless=new")
        driver = uc.Chrome(version_main=137, options=options)
        driver.set_page_load_timeout(30)
        driver.get("https://x.com")
        time.sleep(2)
        yield driver
    except Exception as e:
        st.error(f"❌ WebDriver launch failed: {e}")
        yield None
    finally:
        if driver:
            driver.quit()

@retry(stop_max_attempt_number=3, wait_fixed=2000)
def safe_find_element(driver, by, value, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))

def evaluate_priority(result):
    def parse_date(date_str):
        try:
            return datetime.datetime.strptime(date_str, "%d-%m-%Y")
        except:
            return None

    now = datetime.datetime.now()
    has_keyword = bool(result["Original Name"]) or bool(result["Original feed"])
    has_logo = result["Logo (Yes / No)"] == "Yes"
    has_bio = result["Name (Yes / No)"] == "Yes"
    has_location = bool(result["Location"])
    followers = int(result["Followers"].replace(",", "")) if result["Followers"].replace(",", "").isdigit() else 0
    created = parse_date(result["Created Date"])
    last_post = parse_date(result["Last Post (DD-MM-YYYY) (Optional)"])

    def months_diff(date):
        return (now - date).days / 30 if date else None

    created_months = months_diff(created)
    last_post_months = months_diff(last_post)

    if has_keyword and has_logo and created_months is not None and created_months <= 6 and last_post_months is not None and last_post_months <= 6 and has_bio and has_location and followers > 100:
        return 9, "High"
    elif has_keyword and has_logo and created_months is not None and created_months <= 6 and has_bio and has_location and last_post_months is None:
        return 8, "High"
    elif has_keyword and has_logo and created_months is not None and created_months <= 6:
        return 7, "Medium"
    elif has_keyword and has_logo and last_post_months is not None and last_post_months <= 6 and created_months is not None and created_months > 6:
        return 6, "Medium"
    elif has_keyword and has_logo and created_months is not None and created_months > 6 and last_post_months is not None and last_post_months > 6:
        return 5, "Medium"
    elif has_keyword and created_months is not None and created_months <= 6:
        return 4, "Low"
    elif has_keyword and created_months is not None and created_months > 6:
        return 3, "Low"
    return 2, "Low"

def scrape_profile(driver, url):
    result = {
        "Original Name": "", "Original feed": "", "IMPERSONATED": url,
        "Profile name": "", "Created Date": "", "Logo (Yes / No)": "No",
        "Followers": "", "Active (Yes / No)": "No", "Name (Yes / No)": "No",
        "Location": "", "Last Post (DD-MM-YYYY) (Optional)": "",
        "Risk Score": 4, "priority": "Low",
        "Date": datetime.datetime.now().strftime("%d-%m-%Y"),
        "Comments": ""
    }

    try:
        driver.get(url)
        safe_find_element(driver, By.CSS_SELECTOR, 'div[data-testid="UserName"]', timeout=15)

        try:
            name = safe_find_element(driver, By.CSS_SELECTOR, 'div[data-testid="UserName"] span').text
            result["Profile name"] = name
            result["Name (Yes / No)"] = "Yes"
        except NoSuchElementException:
            pass

        try:
            followers = driver.find_element(By.XPATH, '//a[contains(@href,"/followers")]/span/span').text
            result["Followers"] = followers
        except Exception:
            try:
                followers = driver.find_element(
                    By.XPATH, "(//span[contains(@class, 'css-1jxf684 r-bcqeeo r-1ttztb7 r-qvutc0 r-poiln3 r-1b43r93 r-1cwl3u0 r-b88u0q')])[2]"
                ).text
                result["Followers"] = followers
            except Exception:
                
                result["Followers"] = "?"

        try:
            joined = safe_find_element(driver, By.CSS_SELECTOR, 'span[data-testid="UserJoinDate"]').text
            result["Created Date"] = joined.replace("Joined", "").strip()
        except NoSuchElementException:
            pass

        try:
            location_element = driver.find_element(By.CSS_SELECTOR, 'span[data-testid="UserLocation"]')
            result["Location"] = location_element.text.strip()
        except NoSuchElementException:
            result["Location"] = ""

        # ✅ Fixed and reliable last post logic
        try:
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(random.uniform(1.5, 2.5))

            all_tweets = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')
            non_pinned_datetimes = []

            for tweet in all_tweets:
                is_pinned = tweet.find_elements(By.XPATH, ".//*[contains(text(), 'Pinned')]")
                if not is_pinned:
                    try:
                        time_tag = tweet.find_element(By.TAG_NAME, 'time')
                        dt_str = time_tag.get_attribute('datetime')
                        if dt_str:
                            non_pinned_datetimes.append(dt_str)
                    except NoSuchElementException:
                        continue
                   
        except Exception as e:
            result["Last Post (DD-MM-YYYY) (Optional)"] = ""
            result["Active (Yes / No)"] = "No"
            print(f"⚠ Error in last post: {e}")

        result["Risk Score"], result["priority"] = evaluate_priority(result)

    except Exception as e:
        st.error(f"Scraping failed for {url}: {e}")

    return result, {}

def capture_profile_screenshot(driver, url):
    images = {"profile_screenshot": None}
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="UserName"]')))
        driver.set_window_size(1920, 1080)
        time.sleep(2)
        images["profile_screenshot"] = driver.get_screenshot_as_png()
    except Exception as e:
        st.warning(f"⚠ Failed to capture screenshot for {url}: {e}")
    return images

# --- UI Form ---
with st.form(key="url_form"):
    browser_mode = st.selectbox("Browser Mode", ["Headless (No Popup)", "Visible Browser"])
    urls_input = st.text_area("🔗 Twitter Profile URLs", height=200, placeholder="https://x.com/username")
    submit_button = st.form_submit_button("🔍 Scrape Profiles")

if "scraped_results" not in st.session_state:
    st.session_state.scraped_results = []

if submit_button and urls_input.strip():
    urls = list(dict.fromkeys(u.strip() for u in urls_input.strip().split("\n") if u.strip()))
    if len(urls) > 20:
        st.error("❌ Please provide no more than 20 URLs.")
        st.stop()

    headless_mode = browser_mode == "Headless (No Popup)"
    results = []
    images_dict = {}
    progress_bar = st.progress(0)

    with get_driver(headless=headless_mode) as driver:
        if not driver:
            st.stop()
        for i, url in enumerate(urls):
            try:
                result, _ = scrape_profile(driver, url)
                screenshot_images = capture_profile_screenshot(driver, url)
                results.append(result)
                images_dict[url] = screenshot_images
            except Exception:
                results.append({
                    "Original Name": "", "Original feed": "", "IMPERSONATED": url,
                    "Profile name": "", "Created Date": "", "Logo (Yes / No)": "Yes",
                    "Followers": "", "Active (Yes / No)": "No", "Name (Yes / No)": "No",
                    "Location": "", "Last Post (DD-MM-YYYY) (Optional)": "",
                    "Risk Score": 4, "priority": "High",
                    "Date": datetime.datetime.now().strftime("%d-%m-%Y"),
                    "Comments": ""
                })
                images_dict[url] = {"profile_screenshot": None}
            progress_bar.progress((i + 1) / len(urls))
            time.sleep(random.uniform(2, 4))

    df = pd.DataFrame(results)
    st.session_state.scraped_results = (df, images_dict)
    st.success("✅ Scraping complete!")

# --- Display and Export ---
if "scraped_results" in st.session_state and st.session_state.scraped_results:
    df, images_dict = st.session_state.scraped_results
    st.subheader("📊 Results")
    st.dataframe(df, use_container_width=True)

    for i, row in df.iterrows():
        st.markdown("---")
        col1, col2 = st.columns([5, 2])
        with col1:
            row_text = "\t".join(str(row[col]) for col in df.columns)
            st.code(row_text, language="text")
        with col2:
            screenshot_bytes = images_dict[row["IMPERSONATED"]].get("profile_screenshot")
            if screenshot_bytes:
                img_b64 = base64.b64encode(screenshot_bytes).decode()
                st.markdown(f"<details><summary>📸 Screenshot</summary><img src='data:image/png;base64,{img_b64}' width='300'/></details>", unsafe_allow_html=True)
            else:
                st.write("No screenshot available")

    with st.expander("📋 Copy All Results"):
        all_text = "\n".join("\t".join(str(row[col]) for col in df.columns) for _, row in df.iterrows())
        st.code(all_text, language="text")

    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name="Results", index=False)
        ws = writer.sheets["Results"]
        ws.set_row(1, 200)
        for idx, row in df.iterrows():
            img_data = images_dict[row["IMPERSONATED"]].get("profile_screenshot")
            if img_data:
                ws.insert_image(f'O{idx+2}', f"screenshot_{idx+1}.png", {
                    "image_data": io.BytesIO(img_data),
                    "x_scale": 0.3,
                    "y_scale": 0.3,
                    "positioning": 1
                })

    st.download_button("📥 Download Excel with Screenshots", data=excel_buf.getvalue(), file_name="twitter_profiles.xlsx")
