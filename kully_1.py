import tkinter as tk
from tkinter import messagebox, ttk
import asyncio
import re
import os
import requests
import pandas as pd
from io import BytesIO
from PIL import Image
from playwright.async_api import async_playwright
from datetime import datetime
import threading
import sys

# 🛑 중단 신호용 변수
stop_event = threading.Event()
work_popup = None

# --- GUI 콘솔 출력 리다이렉트 ---
class TextRedirector:
    def __init__(self, widget):
        self.widget = widget
    def write(self, str):
        self.widget.insert(tk.END, str)
        self.widget.see(tk.END)
    def flush(self):
        pass

# --- 이미지 처리 함수 ---
def clean_filename(filename):
    return re.sub(r'[\/:*?"<>|]', '', filename).strip()

def merge_detail_images(image_urls, save_path):
    if not image_urls: return False
    downloaded_images = []
    total_height, max_width = 0, 0
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    unique_urls = list(dict.fromkeys(image_urls))
    
    for url in unique_urls:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                img = Image.open(BytesIO(resp.content))
                if img.width < 100 or img.height < 50: continue
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                downloaded_images.append(img)
                total_height += img.height
                max_width = max(max_width, img.width)
        except: continue
        
    if not downloaded_images: return False
    canvas = Image.new('RGB', (max_width, total_height), (255, 255, 255))
    curr_y = 0
    for img in downloaded_images:
        canvas.paste(img, (0, curr_y))
        curr_y += img.height
    canvas.save(save_path, "JPEG", quality=85)
    return True

# --- 마켓컬리 크롤링 핵심 로직 ---
async def crawl_logic(urls, goal_count, collect_options):
    global work_popup
    async with async_playwright() as p:
        try:
            start_time_str = datetime.now().strftime("%Y%m%d_%H%M")
            base_folder = f"kurly_images_{start_time_str}"
            os.makedirs(base_folder, exist_ok=True)
            
            print(f"🔗 브라우저 실행... (폴더: {base_folder})")
            browser = await p.chromium.launch(headless=False) 
            context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page = await context.new_page()

            all_results = []
            
            for idx, url in enumerate(urls, 1):
                if not url.strip() or stop_event.is_set(): continue
                cat_folder = f"{base_folder}/{idx}번주소"
                print(f"🚀 [{idx}번주소] 수집 시작")
                
                await page.goto(url, wait_until="domcontentloaded")
                await asyncio.sleep(3)
                await page.mouse.wheel(0, 2000)
                await asyncio.sleep(1)

                items = await page.query_selector_all("a[href*='/goods/'], [data-testid='product-item']")
                
                success_count = 0
                processed_urls = set()

                for item in items:
                    if stop_event.is_set() or success_count >= goal_count: break 

                    try:
                        # [가격 추출] 성공했던 로직 그대로 적용
                        price = 0
                        price_el = await item.query_selector("span[class*='1mlutp'], [class*='Price']")
                        if price_el:
                            p_text = await price_el.inner_text()
                            price = int(re.sub(r'[^0-9]', '', p_text))

                        raw_url = await item.get_attribute("href")
                        if not raw_url:
                            link_el = await item.query_selector("a")
                            raw_url = await link_el.get_attribute("href") if link_el else None
                        
                        if not raw_url: continue
                        detail_url = "https://www.kurly.com" + raw_url if raw_url.startswith("/") else raw_url
                        if detail_url in processed_urls: continue

                        # 상세 페이지 이동
                        detail_page = await context.new_page()
                        await detail_page.goto(detail_url)
                        await asyncio.sleep(2)

                        full_name_el = await detail_page.query_selector("h1")
                        full_name = (await full_name_el.inner_text()).strip() if full_name_el else "이름없음"
                        clean_name = clean_filename(full_name)

                        # --- [중량/수량 계산: 네가 주신 로직 기반 보정] ---
                        weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(g|kg|ml|L|KG|Kg|kG|ML|Ml|mL)', full_name)
                        count_match = re.search(r'(\d+)\s*(개|팩|입)', full_name)
                        final_weight = "직접확인"

                        if weight_match and count_match:
                            try:
                                value = float(weight_match.group(1))
                                unit = weight_match.group(2).lower()
                                count_val = int(count_match.group(1))
                                total_value = value * count_val
                                
                                # 소수점 깔끔하게 처리하기 위해 :g 포맷 사용
                                if unit in ['kg', 'l']:
                                    final_weight = f"{total_value:g}{unit}"
                                elif unit == 'g':
                                    if total_value >= 1000: final_weight = f"{total_value/1000:g}kg"
                                    else: final_weight = f"{total_value:g}g"
                                elif unit == 'ml':
                                    if total_value >= 1000: final_weight = f"{total_value/1000:g}L"
                                    else: final_weight = f"{total_value:g}ml"
                            except:
                                final_weight = "계산실패"
                        elif weight_match:
                            # 개수 정보가 없을 때는 매칭된 문자열 그대로 (예: 2.5kg)
                            final_weight = weight_match.group(0).strip()

                        # --- [데이터 저장: 요청한 엑셀 순서 적용] ---
                        product_data = {}
                        if collect_options["브랜드"]:
                            brand_match = re.search(r'^\[(.*?)\]', full_name)
                            product_data["브랜드명"] = brand_match.group(1) if brand_match else "컬리"
                        
                        if collect_options["상품명"]: product_data["상품명"] = full_name
                        
                        origin = "국내산"
                        for o in ["호주", "미국", "캐나다", "스페인", "수입", "칠레", "멕시코", "필리핀", "노르웨이", "태국", "국내산", "페루", "뉴질랜드"]:
                            if o in full_name: origin = o; break
                        if collect_options["원산지"]: product_data["원산지"] = origin
                        if collect_options["중량/수량"]: product_data["중량/수량"] = final_weight
                        if collect_options["가격"]: product_data["가격"] = price # 숫자만 저장
                        if collect_options["상품URL"]: product_data["상품URL"] = detail_url

                        # 이미지 저장 폴더 생성 및 대표이미지 저장
                        product_folder = f"{cat_folder}/{clean_name}"
                        os.makedirs(product_folder, exist_ok=True)

                        main_img = await detail_page.query_selector("img[alt*='대표-이미지'], [class*='zjvv7'] img")
                        if main_img:
                            m_src = await main_img.get_attribute("src")
                            r = requests.get(m_src, timeout=10)
                            with open(f"{product_folder}/{clean_name}_대표이미지.jpg", "wb") as f: f.write(r.content)

                        # [상세이미지 수집] #description + #detail 합치기
                        detail_urls = []
                        for selector in ["#description", "#detail"]:
                            container = await detail_page.query_selector(selector)
                            if container:
                                imgs = await container.query_selector_all("img")
                                detail_urls.extend([await i.get_attribute("src") for i in imgs if await i.get_attribute("src")])

                        if detail_urls:
                            merge_detail_images(detail_urls, f"{product_folder}/{clean_name}_상세이미지.jpg")

                        all_results.append(product_data)
                        processed_urls.add(detail_url)
                        success_count += 1
                        print(f"✅ [{idx}번-{success_count}/{goal_count}] 완료: {clean_name} | {final_weight} | {price}")
                        
                        await detail_page.close()

                    except Exception as e:
                        print(f"⚠️ 스킵: {e}")
                        continue
            
            if all_results:
                df = pd.DataFrame(all_results)
                # 요청하신 순서대로 컬럼 재배치
                order = ["브랜드명", "상품명", "원산지", "중량/수량", "가격", "상품URL"]
                cols = [c for c in order if c in df.columns]
                df[cols].to_excel(f"마켓컬리_수집결과_{start_time_str}.xlsx", index=False)
                messagebox.showinfo("완료", f"총 {len(all_results)}개 수집 완료!")
            
            await browser.close()
        except Exception as e:
            print(f"❌ 에러: {e}")
        finally:
            if work_popup and work_popup.winfo_exists(): work_popup.destroy()

# --- GUI (기존 유지) ---
def start_thread():
    global work_popup
    stop_event.clear()
    sys.stdout = TextRedirector(log_text)
    urls = [entry.get() for entry in url_entries if entry.get().strip()]
    if not urls or not goal_entry.get(): return
    
    work_popup = tk.Toplevel(root); work_popup.title("작업 중"); work_popup.geometry("300x120")
    tk.Label(work_popup, text="마켓컬리 수집 중입니다...", font=('Arial', 10, 'bold'), pady=10).pack()
    tk.Button(work_popup, text="지금 중단하기", command=stop_crawling, bg="#f44336", fg="white", font=('Arial', 9, 'bold')).pack(pady=5)
    work_popup.grab_set()

    options = {"브랜드": var_brand.get(), "상품명": var_name.get(), "원산지": var_origin.get(), "중량/수량": var_weight.get(), "가격": var_price.get(), "상품URL": var_url.get()}
    threading.Thread(target=lambda: asyncio.run(crawl_logic(urls, int(goal_entry.get()), options)), daemon=True).start()

def stop_crawling():
    stop_event.set()
    if work_popup and work_popup.winfo_exists(): work_popup.destroy()

def add_url_entry():
    row = len(url_entries) + 1
    tk.Label(url_frame, text=f"{row}.").grid(row=row, column=0, padx=5)
    entry = tk.Entry(url_frame, width=70); entry.grid(row=row, column=1, pady=2)
    url_entries.append(entry)


root = tk.Tk(); root.title("마켓컬리 수집기 v2.0"); root.geometry("650x750")
goal_frame = tk.Frame(root); goal_frame.pack(pady=5)


tk.Label(goal_frame, text="💡 카테고리당 목표 개수: ").pack(side=tk.LEFT)


goal_entry = tk.Entry(goal_frame, width=10); goal_entry.insert(0, "30"); goal_entry.pack(side=tk.LEFT, padx=5)
check_frame = tk.LabelFrame(root, text="📊 수집 데이터 선택", padx=10, pady=5); check_frame.pack(pady=5, padx=10, fill="x")
var_brand = tk.BooleanVar(value=True); var_name = tk.BooleanVar(value=True); var_origin = tk.BooleanVar(value=True)
var_weight = tk.BooleanVar(value=True); var_price = tk.BooleanVar(value=True); var_url = tk.BooleanVar(value=True)


tk.Checkbutton(check_frame, text="브랜드", variable=var_brand).grid(row=0, column=0, sticky="w")
tk.Checkbutton(check_frame, text="상품명", variable=var_name).grid(row=0, column=1, sticky="w")
tk.Checkbutton(check_frame, text="원산지", variable=var_origin).grid(row=0, column=2, sticky="w")
tk.Checkbutton(check_frame, text="중량/수량", variable=var_weight).grid(row=1, column=0, sticky="w")
tk.Checkbutton(check_frame, text="가격", variable=var_price).grid(row=1, column=1, sticky="w")
tk.Checkbutton(check_frame, text="상품URL", variable=var_url).grid(row=1, column=2, sticky="w")


url_frame = tk.LabelFrame(root, text="🔗 컬리 카테고리 URL", padx=10, pady=5); url_frame.pack(pady=5, padx=10, fill="both", expand=True)
url_entries = []; add_url_entry()
btn_frame = tk.Frame(root); btn_frame.pack(pady=5)


tk.Button(btn_frame, text="➕ URL 추가", command=add_url_entry).pack(side=tk.LEFT, padx=10)
tk.Button(btn_frame, text="🚀 수집 시작", command=start_thread, bg="#5f0080", fg="white", font=('Arial', 10, 'bold'), width=15).pack(side=tk.LEFT, padx=10)
tk.Button(btn_frame, text="🛑 중단", command=stop_crawling, bg="#f44336", fg="white", font=('Arial', 10, 'bold'), width=15).pack(side=tk.LEFT, padx=10)


log_frame = tk.LabelFrame(root, text="📝 작업 현황", padx=10, pady=5); log_frame.pack(pady=5, padx=10, fill="both", expand=True)
log_text = tk.Text(log_frame, height=8); log_text.pack(side=tk.LEFT, fill="both", expand=True)
log_scroll = tk.Scrollbar(log_frame, command=log_text.yview); log_scroll.pack(side=tk.RIGHT, fill="y")
log_text.configure(yscrollcommand=log_scroll.set)


root.mainloop()