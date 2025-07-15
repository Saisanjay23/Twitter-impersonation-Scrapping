import streamlit as st
import datetime
import pandas as pd
import time
import random
import base64
import contextlib
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from retrying import retry
from io import BytesIO
from PIL import Image
import xlsxwriter

st.set_page_config(page_title="Twitter Impersonation Checker", layout="wide")

@contextlib.contextmanager
def get_driver(headless=True):
    

    options = webdriver.ChromeOptions()
    options.binary_location = "/opt/google/chrome/google-chrome"
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_page_load_timeout(30)
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
            spans = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="UserProfileHeader_Items"] span')
            for s in spans:
                txt = s.text
                if "Joined" not in txt:
                    result["Location"] = txt
                    break
        except NoSuchElementException:
            pass

        try:
            tweet_time = driver.find_element(By.XPATH, "//time").get_attribute("datetime")
            tweet_date = datetime.datetime.fromisoformat(tweet_time.replace("Z", "+00:00"))
            result["Last Post (DD-MM-YYYY) (Optional)"] = tweet_date.strftime("%d-%m-%Y")
            delta = (datetime.datetime.now() - tweet_date).days / 30
            result["Active (Yes / No)"] = "Yes" if delta <= 6 else "No"
        except Exception:
            pass

        result["Risk Score"], result["priority"] = evaluate_priority(result)

    except Exception:
        pass

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

def display_image(img_bytes, label="View Screenshot"):
    if img_bytes:
        with st.expander(label):
            st.image(img_bytes, use_container_width=True)

def create_excel_with_images(df, images_dict):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()

    for col_num, header in enumerate(df.columns):
        worksheet.write(0, col_num, header)
    img_col_index = len(df.columns)
    worksheet.write(0, img_col_index, "Screenshot")
    worksheet.set_column(img_col_index, img_col_index, 25)

    desired_img_width = 100
    desired_img_height = 80

    for row_num, row in df.iterrows():
        excel_row = row_num + 1
        for col_num, value in enumerate(row):
            worksheet.write(excel_row, col_num, value)

        worksheet.set_row(excel_row, desired_img_height * 0.75)

        img_data = images_dict[row["IMPERSONATED"]]["profile_screenshot"]
        if img_data:
          img_buf = BytesIO(img_data)
          worksheet.insert_image(
          excel_row, img_col_index,
          "screenshot.png",
          {
              'image_data': img_buf,
              'x_offset': 5,
              'y_offset': 2,
              'x_scale': 0.25,
              'y_scale': 0.25,
              'object_position': 1,
              'positioning': 1
          }
      )



    workbook.close()
    output.seek(0)
    return output

# Streamlit UI
st.title("🕵 Twitter/X Impersonation Checker")
st.markdown("Paste up to 20 Twitter profile URLs (one per line) to scrape impersonator data.")

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
                    "Profile name": "", "Created Date": "", "Logo (Yes / No)": "No",
                    "Followers": "", "Active (Yes / No)": "No", "Name (Yes / No)": "No",
                    "Location": "", "Last Post (DD-MM-YYYY) (Optional)": "",
                    "Risk Score": 4, "priority": "Low",
                    "Date": datetime.datetime.now().strftime("%d-%m-%Y"),
                    "Comments": ""
                })
                images_dict[url] = {"profile_screenshot": None}
            progress_bar.progress((i + 1) / len(urls))
            time.sleep(random.uniform(2, 4))

    df = pd.DataFrame(results)
    st.session_state.scraped_results = (df, images_dict)
    st.success("✅ Scraping complete!")

if "scraped_results" in st.session_state and st.session_state.scraped_results:
    df, images_dict = st.session_state.scraped_results
    st.subheader("📊 Results")
    st.dataframe(df, use_container_width=True)

    for i, row in df.iterrows():
        st.markdown("---")
        col1, col2 = st.columns([5, 2])
        with col1:
            st.code("\t".join(str(row[col]) for col in df.columns), language="text")
        with col2:
            if images_dict[row["IMPERSONATED"]]["profile_screenshot"]:
                display_image(images_dict[row["IMPERSONATED"]]["profile_screenshot"], "Profile Screenshot")
            else:
                st.write("No screenshot available")

    st.download_button(
        "📥 Download CSV",
        df.to_csv(index=False).encode(),
        file_name=f"twitter_results_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

    excel_file = create_excel_with_images(df, images_dict)
    st.download_button(
        label="📥 Download Excel with Embedded Images",
        data=excel_file,
        file_name="twitter_results_with_screenshots.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
