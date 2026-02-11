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
    root.title("네이버 블로그 자동화 설정 (v1.2)")
    root.geometry("850x1150") # UI 높이 증가
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

    # --- 댓글 조합 UI 구성 (핵심 수정) ---
    
    # 1. 랜덤 첫 줄 리스트 영역 (추가)
    tk.Label(root, text="\n📋 [1] 랜덤 첫 줄 리스트 (한 줄에 하나씩)", font=("Malgun Gothic", 10, "bold"), bg="#f5f5f5").pack(anchor="w", padx=20)
    first_comment_area = tk.Text(root, height=8, font=("Malgun Gothic", 10), relief="solid", bd=1)
    default_first = (
                "글이 너무 정성스럽게 작성되어 인상 깊었습니다.\n"
                "후기 내용을 보니 신뢰가 가네요.\n"
                "글을 읽는 동안 정보가 잘 정리되어 있어서 좋았습니다.\n"
                "후기 구성이 깔끔해서 보기 편했습니다.\n"
                "솔직한 후기라 믿음이 갔습니다.\n"
                "설명이 자세해서 도움이 많이 됐습니다.\n"
                "후기의 진솔함이 느껴졌습니다.\n"
                "글에 정성이 가득 담겨 있어서 좋았습니다.\n"
                "내용을 읽고 실제로 가보고 싶은 마음이 들었습니다.\n"
                "세심한 후기 덕분에 참고가 많이 됐습니다.\n"
                "구체적인 설명 덕분에 이해하기 쉬웠습니다.\n"
                "진심이 느껴지는 글이었습니다.\n"
                "꼼꼼하게 정리된 후기라 믿을 수 있었습니다.\n"
                "후기에서 진짜 경험담이 느껴져 신뢰가 갔습니다.\n"
                "자세한 정보 제공에 감사드립니다.\n"
                "글 흐름이 자연스러워 읽기 편했습니다.\n"
                "좋은 후기 덕분에 큰 도움이 됐습니다.\n"
                "후기 스타일이 깔끔해서 믿음이 갔습니다.\n"
                "생생한 경험담이라 더 와닿았습니다.\n"
                "솔직하고 담백한 글이라 좋았습니다.\n"
                "후기 내용이 구체적이라 신뢰가 갔습니다.\n"
                "글이 너무 잘 정리되어 있어서 참고하기 좋네요.\n"
                "후기에서 진정성이 느껴졌습니다.\n"
                "직접 다녀온 느낌이 잘 전해졌습니다.\n"
                "글 전개가 깔끔해서 이해하기 쉬웠습니다.\n"
                "정성껏 작성된 후기라 보는 내내 좋았습니다.\n"
                "후기 내용이 실질적이어서 많은 도움이 됐습니다.\n"
                "후기 자체가 매우 신뢰를 주는 스타일이네요.\n"
                "정보가 체계적으로 정리되어 있어서 편했습니다.\n"
                "현실적인 내용이 잘 녹아 있어 좋았습니다.\n"
                "후기 하나하나에 경험이 녹아 있는 느낌이었습니다.\n"
                "글에 담긴 세세한 정보가 특히 인상 깊었습니다.\n"
                "후기 덕분에 방문하고 싶은 마음이 생겼습니다.\n"
                "솔직한 평가가 인상 깊었습니다.\n"
                "후기의 진솔함이 전해져 좋았습니다.\n"
                "글 구성이 이해하기 쉽고 자연스러웠습니다.\n"
                "정보량이 많아서 정말 유익했습니다.\n"
                "후기 내용이 알차고 충실해서 신뢰가 갔습니다.\n"
                "하나하나 경험한 것들이 잘 정리되어 있었습니다.\n"
                "실제 경험을 기반으로 쓴 글이라 믿음이 갔습니다.\n"
                "솔직하고 현실적인 내용이라 좋았습니다.\n"
                "정보 전달이 명확해서 좋았습니다.\n"
                "후기 스타일이 간결하고 깔끔해서 보기 편했습니다.\n"
                "장단점을 솔직하게 정리해주셔서 유익했습니다.\n"
                "후기 전반이 믿음을 줄 만큼 탄탄했습니다.\n"
                "필요한 정보를 알기 쉽게 정리해주셔서 좋았습니다.\n"
                "글을 통해 생생한 후기를 간접 경험할 수 있었습니다.\n"
                "후기 내용이 세세하고 구체적이라 많은 도움이 됐습니다.\n"
                "글의 솔직함과 진정성이 느껴져 인상 깊었습니다.\n"
                "꼼꼼한 설명 덕분에 큰 도움이 됐습니다.\n"
    )
    first_comment_area.insert(tk.END, default_first)
    first_comment_area.pack(padx=20, fill="x", pady=2)

    # 2. 기존 상단 고정 문구
    tk.Label(root, text="\n📢 [2] 제목 및 고정 문구", font=("Malgun Gothic", 10, "bold"), bg="#f5f5f5").pack(anchor="w", padx=20)
    head_area = tk.Entry(root, font=("Malgun Gothic", 10), relief="solid", bd=1)
    head_area.insert(0, "맛집 영상 제보하고 신세계백화점 상품권(3만원 ·5만원)받으세요")
    head_area.pack(padx=20, fill="x", pady=2)

    # 3. 기존 중간 특징 문구
    tk.Label(root, text="\n✨ [3] 중간 특징 문구 (한 줄에 하나씩)", font=("Malgun Gothic", 10, "bold"), bg="#f5f5f5").pack(anchor="w", padx=20)
    mid_comment_area = tk.Text(root, height=5, font=("Malgun Gothic", 10), relief="solid", bd=1)
    mid_default = (
        "봐주지 않는 맛집 리뷰 리얼플레이트\n"
        "팩트 기반 맛집 리뷰 리얼플레이트\n"
        "돌려 말하지 않는 맛집 리뷰 리얼플레이트\n"
        "현실적인 맛집 리뷰 리얼플레이트\n"
        "속지 말자 맛집 리뷰 리얼플레이트\n"
        "직설적인 맛집 리뷰 리얼플레이트\n"
    )
    mid_comment_area.insert(tk.END, mid_default)
    mid_comment_area.pack(padx=20, fill="x", pady=2)

    # 4. 기존 하단 문의 문구
    tk.Label(root, text="\n🔗 [4] 하단 문의 문구 (한 줄에 하나씩)", font=("Malgun Gothic", 10, "bold"), bg="#f5f5f5").pack(anchor="w", padx=20)
    tail_comment_area = tk.Text(root, height=3, font=("Malgun Gothic", 10), relief="solid", bd=1)
    tail_default = (
        "영상 제보 및 문의 http://pf.kakao.com/_vWIxon\n"
        "제보나 문의는 이쪽으로 부탁드려요! http://pf.kakao.com/_vWIxon\n"
        "영상 제보/문의는 언제든 http://pf.kakao.com/_vWIxon"
    )
    tail_comment_area.insert(tk.END, tail_default)
    tail_comment_area.pack(padx=20, fill="x", pady=2)

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
            
            # 조합용 데이터 저장 (전체 4단계로 수정)
            config_result["firsts"] = [l.strip() for l in first_comment_area.get("1.0", tk.END).split('\n') if l.strip()]
            config_result["head"] = head_area.get().strip()
            config_result["mids"] = [l.strip() for l in mid_comment_area.get("1.0", tk.END).split('\n') if l.strip()]
            config_result["tails"] = [l.strip() for l in tail_comment_area.get("1.0", tk.END).split('\n') if l.strip()]

            root.quit()
            root.destroy()
            
        except Exception as e:
            messagebox.showerror("오류", f"설정 저장 중 에러: {e}")

    tk.Button(root, text="🚀 설정 완료 및 작업 시작", command=on_confirm, width=40, height=2, 
              bg="#03C75A", fg="white", font=("Malgun Gothic", 11, "bold")).pack(pady=20)
    root.mainloop()
    return config_result

# --- [특수문자 및 글자 깨트리기 로직 수정] ---
def broken_text(text):
    """지정한 단어들에 .,! 가 랜덤한 위치에 하나씩 들어가게 깨트림"""
    targets = ["리얼플레이트", "신세계백화점", "상품권"] # 깨트릴 단어들
    
    for target in targets:
        if target not in text:
            continue
        
        parts = list(target)
        special_chars = [".", ",", "!", "."]
        
        for char in special_chars:
            insert_idx = random.randint(0, len(parts))
            parts.insert(insert_idx, char)
        
        broken_target = "".join(parts)
        text = text.replace(target, broken_target) # 계속 교체
        
    return text

def add_marker(text):
    """링크 앞뒤에 랜덤 마커 추가"""
    markers = ["▶", "➔", "※", "☞", "✔"]
    marker = random.choice(markers)
    return f"{marker} {text}"

# --- [2. 메인 로직] ---
def main():
    config = get_config()
    if not config: return

    
    popup = tk.Tk()  # 독립된 새 창으로 만들기
    popup.title("알림")
    popup.geometry("300x150")
    popup.attributes("-topmost", True)
    tk.Label(popup, text="🚫 동작 중입니다.\n\n가급적 조작하지 마세요!\n잠시만 기다려주세요...", font=("Malgun Gothic", 12, "bold")).pack(expand=True)
    popup.update()

    
    real_drop = "http://pf.kakao.com/_vWIxon" # 중복 체크용은 원본 그대로 사용
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
        print(f"\n🔍 검색어 직접 입력 중: {query}")

        driver.get("https://search.naver.com/search.naver?ssc=tab.blog.all")
        time.sleep(1.5)

        search_box = wait.until(EC.presence_of_element_located((By.ID, "nx_query")))
        search_box.clear() 
        time.sleep(0.5)

        search_box.send_keys(query)
        time.sleep(0.5)
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
                
                # 중복 체크 로직 (원본으로 체크)
                if real_drop in list_text:
                    print(f"      ㄴ [패스] 중복 감지")
                    continue

                # --- [4단계 랜덤 댓글 조합 및 처리] ---
                f1 = random.choice(config["firsts"]) # 1. 랜덤 첫 줄 (추가)
                h2 = config["head"]                  # 2. 기존 고정 멘트
                h2 = broken_text(h2)                 #    글자 깨트리기
                m3 = random.choice(config["mids"])   # 3. 기존 중간 멘트
                m3 = broken_text(m3)                 #    글자 깨트리기
                t4 = random.choice(config["tails"])  # 4. 기존 문의 멘트
                t4 = add_marker(t4)                  #    링크 마커 추가
                
                final_text = f"{f1}\n{h2}\n{m3}\n{t4}"
                # ---------------------------------------

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