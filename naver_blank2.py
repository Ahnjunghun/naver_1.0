import time
import random
import os
import re
import pandas as pd
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import sys

# --- [1. 설정 UI] ---
def get_config():
    root = tk.Tk()
    root.title("네이버 블로그 자동화 설정 (이웃추가+댓글 ver)")
    root.geometry("850x950") 
    root.attributes("-topmost", True)
    root.configure(bg="#f5f5f5")

    tk.Label(root, text="🎯 작업 설정", font=("Malgun Gothic", 14, "bold"), bg="#f5f5f5").pack(pady=15)

    detail_frame = tk.Frame(root, bg="white", relief="solid", bd=1, padx=20, pady=10)
    detail_frame.pack(padx=20, fill="x")

    def create_input(label_text, default_val, is_pw=False):
        f = tk.Frame(detail_frame, bg="white")
        f.pack(fill="x", pady=5)
        tk.Label(f, text=label_text, width=22, anchor="w", bg="white").pack(side="left")
        ent = tk.Entry(f, show="*" if is_pw else "")
        ent.insert(0, default_val)
        ent.pack(side="right", expand=True, fill="x")
        return ent

    ent_id = create_input("네이버 ID:", "")
    ent_pw = create_input("네이버 PW:", "", is_pw=True)
    ent_loc = create_input("작업 지역:", "")
    ent_mid = create_input("중간 키워드:", "")
    ent_last = create_input("마지막 키워드:", "맛집") 
    ent_total_limit = create_input("총 목표 댓글 수:", "20")

    # 옵션 선택 (이웃추가 여부만 남김)
    tk.Label(root, text="\n🛠️ 작업 옵션 선택", font=("Malgun Gothic", 10, "bold"), bg="#f5f5f5").pack(anchor="w", padx=20)
    opt_frame = tk.Frame(root, bg="#f5f5f5")
    opt_frame.pack(fill="x", padx=20)

    var_neighbor = tk.BooleanVar(value=True)
    tk.Checkbutton(opt_frame, text="서로이웃 신청 진행", variable=var_neighbor, bg="#f5f5f5", font=("Malgun Gothic", 10)).pack(side="left", padx=10)

    tk.Label(root, text="\n💬 댓글 입력 (번호 1. 2. 를 기준으로 멘트가 구분됩니다)", 
             font=("Malgun Gothic", 10, "bold"), bg="#f5f5f5").pack(anchor="w", padx=20)
    
    comment_area = tk.Text(root, height=12, font=("Malgun Gothic", 10), relief="solid", bd=1)
    default_comments = "1. \n\n2. \n\n3. "
    comment_area.insert(tk.END, default_comments)
    comment_area.pack(padx=20, fill="x", pady=5)

    config_result = {}

    def on_confirm():
        try:
            config_result["u_id"] = ent_id.get().strip()
            config_result["u_pw"] = ent_pw.get().strip()
            config_result["loc"] = ent_loc.get().strip()
            config_result["mid"] = ent_mid.get().strip()
            config_result["last"] = ent_last.get().strip() 
            config_result["total_limit"] = int(ent_total_limit.get())
            config_result["do_neighbor"] = var_neighbor.get()
            
            raw_text = comment_area.get("1.0", tk.END).strip()
            parts = re.split(r'\d+\.', raw_text)
            config_result["comment_list"] = [p.strip() for p in parts if p.strip()]
            
            root.quit()
            root.destroy()
        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 중 에러: {e}")

    tk.Button(root, text="🚀 작업 시작", command=on_confirm, width=40, height=2, 
              bg="#03C75A", fg="white", font=("Malgun Gothic", 11, "bold")).pack(pady=20)
    root.mainloop()
    return config_result

def main():
    config = get_config()
    if not config: return

    popup = tk.Tk()
    popup.title("알림")
    popup.geometry("300x150")
    popup.attributes("-topmost", True)
    tk.Label(popup, text="🚫 동작 중입니다.\n\n가급적 조작하지 마세요!", font=("Malgun Gothic", 12, "bold")).pack(expand=True)
    popup.update()

    real_drop = "리얼플레이트"
    total_success_count = 0
    excel_data = []

    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 15)
    short_wait = WebDriverWait(driver, 3)

    try:
        # 로그인 및 검색 (생략 없이 유지)
        driver.get("https://nid.naver.com/nidlogin.login")
        time.sleep(2)
        driver.execute_script(f"document.getElementsByName('id')[0].value = '{config['u_id']}'")
        driver.execute_script(f"document.getElementsByName('pw')[0].value = '{config['u_pw']}'")
        driver.find_element(By.ID, "log.login").click()
        time.sleep(3)

        query = f"{config['loc']} +{config['mid']} +{config['last']}"
        driver.get(f"https://search.naver.com/search.naver?ssc=tab.blog.all&query={query}")
        time.sleep(2)

        try:
            sort_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '최신순')]")))
            driver.execute_script("arguments[0].click();", sort_btn)
            time.sleep(2)
            print("      ㄴ ✅ 최신순 정렬 완료")
        except:
            print("      ㄴ ⚠️ 최신순 정렬 버튼을 찾지 못했습니다.")

        all_a = driver.find_elements(By.TAG_NAME, "a")
        urls = list(dict.fromkeys([a.get_attribute('href') for a in all_a if a.get_attribute('href') and "blog.naver.com" in a.get_attribute('href') and a.get_attribute('href').count('/') >= 4]))
        
        for url in urls:
            if total_success_count >= config["total_limit"]: break
            driver.get(url)
            comment_done = False 

            try:
                driver.switch_to.default_content()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "mainFrame")))
                main_win = driver.current_window_handle

                def step_neighbor():
                    try:
                        driver.execute_script("window.scrollTo(0, 0);")
                        neighbor_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn_buddy, .u_btn_buddy")))
                        neighbor_btn.click()
                        short_wait.until(lambda d: len(d.window_handles) > 1)
                        for handle in driver.window_handles:
                            if handle != main_win:
                                driver.switch_to.window(handle)
                                break
                        for _ in range(2):
                            try:
                                next_btn = short_wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '다음')] | //*[contains(text(), '확인')]")))
                                next_btn.click()
                                time.sleep(0.7)
                            except: break
                        try:
                            close_btn = short_wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '닫기')] | //*[contains(text(), '완료')] | //*[@class='btn_close']")))
                            close_btn.click()
                        except: driver.close()
                        driver.switch_to.window(main_win)
                        driver.switch_to.default_content()
                        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "mainFrame")))
                        print("      ㄴ 🤝 이웃 신청 완료")
                    except: print("      ㄴ 🤝 이웃 신청 스킵")

                def step_comment():
                    nonlocal total_success_count, comment_done
                    try:
                        time.sleep(1)
                        comment_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#commentCount, .btn_comment, .u_btn_comment")))
                        driver.execute_script("arguments[0].click();", comment_btn)
                        time.sleep(2)
                        list_text = driver.find_element(By.CSS_SELECTOR, ".u_cbox_list").text
                        if real_drop in list_text:
                            print("      ㄴ ⏭️ 이미 작성됨 (스킵)")
                            return
                        final_text = random.choice(config["comment_list"])
                        write_area = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".u_cbox_write_area")))
                        write_area.click()
                        ActionChains(driver).send_keys(final_text).perform()
                        time.sleep(1)
                        driver.find_element(By.CSS_SELECTOR, ".u_cbox_btn_upload").click()
                        time.sleep(2)
                        try: driver.switch_to.alert.accept()
                        except:
                            total_success_count += 1
                            comment_done = True
                            excel_data.append({
                                "작성 날짜": datetime.now().strftime("%y%m%d"),
                                "작성자 아이디": config['u_id'],
                                "블로그 URL": url,
                                "검색 키워드": query,
                                "작성 내용": final_text
                            })
                            print(f"      ㄴ ✅ 성공 ({total_success_count}/{config['total_limit']})")
                    except Exception: pass

                # 순서 랜덤화 (이웃추가 + 댓글만)
                actions = []
                if config["do_neighbor"]: actions.append(step_neighbor)
                actions.append(step_comment)

                random.shuffle(actions)
                for action in actions: action()
                
                if comment_done:
                    time.sleep(random.uniform(10, 20))

            except Exception: continue
            finally: driver.switch_to.default_content()
    finally:
        # 엑셀 저장
        if excel_data:
            df = pd.DataFrame(excel_data)
            fn = f"작성현황_{datetime.now().strftime('%y%m%d')}.xlsx"
            if os.path.exists(fn):
                try:
                    old = pd.read_excel(fn)
                    df = pd.concat([old, df], ignore_index=True)
                except: pass
            df.to_excel(fn, index=False)
            print(f"\n✅ 엑셀 저장 완료: {fn}")
        popup.destroy()
        if driver: driver.quit()
        print("\n모든 작업을 마쳤습니다. 😊")

if __name__ == "__main__":
    main()