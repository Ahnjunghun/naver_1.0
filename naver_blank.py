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
import sys


# --- [1. 설정 UI] ---
def get_config():
    root = tk.Tk()
    root.title("네이버 블로그 자동화 설정 (naver_1.0)")
    root.geometry("850x900") 
    root.attributes("-topmost", True)
    root.configure(bg="#f5f5f5")

    tk.Label(root, text="🎯 단일 작업 설정", font=("Malgun Gothic", 14, "bold"), bg="#f5f5f5").pack(pady=15)

    detail_frame = tk.Frame(root, bg="white", relief="solid", bd=1, padx=20, pady=10)
    detail_frame.pack(padx=20, fill="x")

    def create_input(label_text, default_val, is_pw=False):
        f = tk.Frame(detail_frame, bg="white")
        f.pack(fill="x", pady=5)
        tk.Label(f, text=label_text, width=22, anchor="w", bg="white").pack(side="left")
        ent = tk.Entry(f, show="*" if is_pw else "")
        ent.insert(0, default_val)
        ent.pack(side="right", expand=True, fill="x")
        ent.bind("<Return>", lambda e: e.widget.tk_focusNext().focus())
        return ent

    ent_id = create_input("네이버 ID:", "")
    ent_pw = create_input("네이버 PW:", "", is_pw=True)
    ent_loc = create_input("작업 지역 (단일):", "")
    ent_mid = create_input("중간 키워드 (단일):", "")
    ent_last = create_input("마지막 키워드 (단일):", "맛집") 
    ent_total_limit = create_input("총 목표 댓글 수:", "20")

    # --- 댓글 입력 UI (번호 기준 구분) ---
    tk.Label(root, text="\n💬 댓글 입력 (번호 1. 2. 를 기준으로 멘트가 구분됩니다)", 
             font=("Malgun Gothic", 10, "bold"), bg="#f5f5f5").pack(anchor="w", padx=20)
    
    comment_area = tk.Text(root, height=15, font=("Malgun Gothic", 10), relief="solid", bd=1)
    
    # 예시: 번호 사이에는 줄바꿈을 넣어도 한 묶음으로 취급됨
    default_comments = (
        "1. \n\n"
        "2. \n\n"
        "3. "
    )
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
            config_result["delay_min"], config_result["delay_max"] = 10, 20
            
            # [핵심 수정 로직] 숫자. 패턴을 기준으로 텍스트 분할
            raw_text = comment_area.get("1.0", tk.END).strip()
            
            # 정규표현식으로 '숫자.'를 기준으로 나눔
            # split 결과에서 첫 번째 빈 값 제거 및 각 묶음 앞뒤 공백 정리
            parts = re.split(r'\d+\.', raw_text)
            comment_candidates = [p.strip() for p in parts if p.strip()]
            
            if not comment_candidates:
                messagebox.showwarning("주의", "번호(1. 2.)를 포함해서 내용을 입력해주세요.")
                return

            config_result["comment_list"] = comment_candidates
            root.quit()
            root.destroy()
        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 중 에러: {e}")

    tk.Button(root, text="🚀 설정 완료 및 작업 시작", command=on_confirm, width=40, height=2, 
              bg="#03C75A", fg="white", font=("Malgun Gothic", 11, "bold")).pack(pady=20)
    root.mainloop()
    return config_result

# --- [2. 메인 로직 (기존과 동일)] ---
def main():
    config = get_config()
    if not config: return


    popup = tk.Tk()  # 독립된 새 창으로 만들기
    popup.title("알림")
    popup.geometry("300x150")
    popup.attributes("-topmost", True)
    tk.Label(popup, text="🚫 동작 중입니다.\n\n가급적 조작하지 마세요!\n잠시만 기다려주세요...", font=("Malgun Gothic", 12, "bold")).pack(expand=True)
    popup.update()


    real_drop = "리얼플레이트"
    total_success_count = 0
    excel_data = []

    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 15)

    try:
        driver.get("https://nid.naver.com/nidlogin.login")
        time.sleep(2)
        driver.execute_script(f"document.getElementsByName('id')[0].value = '{config['u_id']}'")
        driver.execute_script(f"document.getElementsByName('pw')[0].value = '{config['u_pw']}'")
        driver.find_element(By.ID, "log.login").click()
        time.sleep(3)

        loc = config["loc"]
        mid_kw = config["mid"]
        last_kw = config["last"]

        query = f"{loc} +{mid_kw} +{last_kw}"
        driver.get("https://search.naver.com/search.naver?ssc=tab.blog.all")
        time.sleep(1.5)

        search_box = wait.until(EC.presence_of_element_located((By.ID, "nx_query")))
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys("\n")
        time.sleep(2)

        try:
            sort_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '최신순')]")))
            driver.execute_script("arguments[0].click();", sort_btn)
            time.sleep(2)
        except: pass

        all_a = driver.find_elements(By.TAG_NAME, "a")
        urls = []
        for a in all_a:
            href = a.get_attribute('href')
            if href and "blog.naver.com" in href and (href.count('/') >= 4):
                if href not in urls: urls.append(href)
        
        for url in urls:
            if total_success_count >= config["total_limit"]: break
            driver.get(url)
            try:
                driver.switch_to.default_content()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "mainFrame")))
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)

                comment_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#commentCount, .btn_comment, .u_btn_comment")))
                driver.execute_script("arguments[0].click();", comment_btn)
                time.sleep(1.5)

                list_text = driver.find_element(By.CSS_SELECTOR, ".u_cbox_list").text
                if real_drop in list_text:
                    continue

                # --- 랜덤 선택 및 입력 ---
                final_text = random.choice(config["comment_list"])

                write_area = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".u_cbox_write_area")))
                write_area.click()
                ActionChains(driver).send_keys(final_text).perform()
                time.sleep(1)
                driver.find_element(By.CSS_SELECTOR, ".u_cbox_btn_upload").click()
                
                time.sleep(2)
                try:
                    alert = driver.switch_to.alert
                    alert.accept()
                except:
                    total_success_count += 1
                    excel_data.append({
                        "작성 날짜": datetime.now().strftime("%y%m%d"),
                        "작성자 아이디": config['u_id'],
                        "블로그 URL": url,
                        "검색 키워드": query,
                        "작성 내용": final_text  # 추가된 부분
                    })
                    print(f"      ㄴ ✅ 성공 ({total_success_count}/{config['total_limit']})")
                    time.sleep(random.uniform(config["delay_min"], config["delay_max"]))
            except:
                print("      ㄴ ❌ 스킵")
                continue
            finally:
                driver.switch_to.default_content()
    finally:
        if excel_data:
            df = pd.DataFrame(excel_data)
            fn = f"작성현황_{datetime.now().strftime('%y%m%d')}.xlsx"
            cols = ["작성 날짜", "작성자 아이디", "블로그 URL", "검색 키워드", "작성 내용"]
            df = df[cols]

            try:
                if os.path.exists(fn):
                    old = pd.read_excel(fn)
                    df = pd.concat([old[cols], df], ignore_index=True)
                df.to_excel(fn, index=False)
                print(f"\n✅ 엑셀 누적 저장 완료: {fn}")
            except PermissionError:
                timestamp = datetime.now().strftime("%H%M%S")
                temp_fn = f"작성현황_{datetime.now().strftime('%y%m%d')}_{timestamp}.xlsx"
                df.to_excel(temp_fn, index=False)
                print(f"\n⚠️ {fn} 파일이 열려 있어 임시 파일로 저장했습니다: {temp_fn}")
            except Exception as e:
                print(f"\n❌ 엑셀 저장 중 오류: {e}")

                
        popup.destroy()
        # ----------------------------------------------------                
        
        if driver: driver.quit()                
        print("\n모든 작업을 마쳤습니다. 😊")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Ctrl+C로 강제 종료 시 에러 메시지 없이 조용히 종료
        print("\n프로그램을 강제 종료합니다.")                
        sys.exit(0)
    except Exception:
        # 다른 예기치 못한 에러가 나도 에러 스크립트 없이 조용히 종료
        sys.exit(0)