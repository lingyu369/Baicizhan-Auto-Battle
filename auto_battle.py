import win32gui, win32ui, win32con, win32api
import time
import re
import ctypes
import os
import csv
import json
import numpy as np
import logging
import random
import cv2
from PIL import Image
from paddleocr import PaddleOCR
from difflib import SequenceMatcher

# ==================== 配置 ====================
WINDOW_TITLE = '雷电模拟器'
DICT_FILENAME = 'ecdict.csv'
CHEAT_SHEET_FILENAME = 'cheat_sheet.json'  # 偷题本文件

# 屏蔽日志
logging.getLogger("ppocr").setLevel(logging.WARNING)

print("🚀 正在加载本地 OCR 模型...")
ocr = PaddleOCR(use_angle_cls=False, lang="ch", show_log=False)
print("✅ OCR 模型加载完毕！")

# 强制 DPI 感知
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()


class OptimizedBot:
    def __init__(self):
        self.hwnd = win32gui.FindWindow(None, WINDOW_TITLE)
        if not self.hwnd:
            print(f"❌ 未找到窗口: {WINDOW_TITLE}")
            print("请启动雷电模拟器！")
            exit()

        self.dictionary = {}
        self.cheat_sheet = {}

        # 加载两个词库
        self.load_dictionary()
        self.load_cheat_sheet()

        self.last_word = ""
        self.last_action_time = 0

    def load_dictionary(self):
        """加载通用大词典"""
        if not os.path.exists(DICT_FILENAME):
            print(f"❌ 错误: 未找到 {DICT_FILENAME}")
            exit()

        print(f"📂 正在载入通用词典 (约 5 秒)...")
        try:
            with open(DICT_FILENAME, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 4:
                        word = row[0].lower()
                        trans = row[3]
                        if trans:
                            self.dictionary[word] = trans
            print(f"✅ 通用词典就绪！收录 {len(self.dictionary)} 词。")
        except Exception as e:
            print(f"❌ 词典读取失败: {e}")
            exit()

    def load_cheat_sheet(self):
        """加载偷题本"""
        if os.path.exists(CHEAT_SHEET_FILENAME):
            try:
                with open(CHEAT_SHEET_FILENAME, 'r', encoding='utf-8') as f:
                    self.cheat_sheet = json.load(f)
                print(f"😈 偷题本已加载！包含 {len(self.cheat_sheet)} 个满分答案")
            except:
                self.cheat_sheet = {}
        else:
            self.cheat_sheet = {}

    def save_cheat_sheet(self):
        """保存偷题本"""
        try:
            with open(CHEAT_SHEET_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(self.cheat_sheet, f, ensure_ascii=False, indent=2)
            print(f"💾 偷题本已更新，当前收录: {len(self.cheat_sheet)}")
        except:
            pass

    def capture_window(self):
        left, top, right, bot = win32gui.GetWindowRect(self.hwnd)
        w, h = right - left, bot - top

        hwndDC = win32gui.GetWindowDC(self.hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)

        result = ctypes.windll.user32.PrintWindow(self.hwnd, saveDC.GetSafeHdc(), 2)
        if result == 0:
            ctypes.windll.user32.PrintWindow(self.hwnd, saveDC.GetSafeHdc(), 0)

        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        img_pil = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)

        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, hwndDC)

        return img_pil, w, h

    def preprocess_image(self, img_pil):
        """视觉增强：二值化 + 遮罩"""
        img = cv2.cvtColor(np.asarray(img_pil), cv2.COLOR_RGB2BGR)
        h, w = img.shape[:2]

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 阈值 180，提取白色文字
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        # 涂黑顶部干扰
        cv2.rectangle(binary, (0, 0), (w, int(h * 0.12)), (0, 0, 0), -1)
        # 涂黑底部干扰
        cv2.rectangle(binary, (0, int(h * 0.98)), (w, h), (0, 0, 0), -1)

        return binary

    def click_relative(self, x, y):
        rect = win32gui.GetWindowRect(self.hwnd)
        abs_x = rect[0] + int(x)
        abs_y = rect[1] + int(y)
        win32api.SetCursorPos((abs_x, abs_y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.01)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def learn_from_result(self, img_pil):
        """
        核心功能：扫描结算界面，学习正确答案
        """
        # 为了OCR准确，这里重新转换一次原始图片，不使用带遮罩的processed_img
        # 因为结算界面的列表可能在屏幕中偏下的位置
        img = cv2.cvtColor(np.asarray(img_pil), cv2.COLOR_RGB2BGR)
        h, w = img.shape[:2]

        # 裁剪出中间列表区域 (经验值：高度30%~80%，宽度10%~90%)
        # 避开顶部的分数和底部的按钮
        roi = img[int(h * 0.3):int(h * 0.8), int(w * 0.1):int(w * 0.9)]

        # 对该区域进行OCR
        result = ocr.ocr(roi, cls=False)
        if not result or not result[0]: return

        learned_count = 0
        print("🕵️‍♂️ 正在扫描结果页偷取答案...")

        for line in result[0]:
            text = line[1][0]
            # 典型格式: "apple 苹果" 或 "apple n. 苹果"
            # 寻找中文起始位置
            match = re.search(r'[\u4e00-\u9fa5]', text)
            if match:
                split_idx = match.start()
                en_part = text[:split_idx].strip()
                cn_part = text[split_idx:].strip()

                # 清洗英文部分 (去掉前面的对勾、叉号等干扰字符)
                en_clean = re.sub(r'[^a-zA-Z\s\-\']', '', en_part).strip().lower()

                if len(en_clean) > 1 and len(cn_part) > 0:
                    # 如果不在偷题本里，或者解释更新，则保存
                    if en_clean not in self.cheat_sheet:
                        self.cheat_sheet[en_clean] = cn_part
                        learned_count += 1
                        print(f"   [学习] {en_clean} = {cn_part}")

        if learned_count > 0:
            self.save_cheat_sheet()

    def calculate_similarity(self, meaning_str, option_text, is_exact_match_mode=False):
        """
        匹配算法
        is_exact_match_mode: 如果是True，表示meaning_str来自偷题本，直接判断包含关系即可
        """
        opt_clean = re.sub(r'[^\w\u4e00-\u9fa5]', '', option_text)
        if not opt_clean: return 0.0

        # === 模式1：偷题本模式 (暴力精准匹配) ===
        if is_exact_match_mode:
            # 偷来的答案通常完全对应选项，直接看是否包含
            # 去掉解释里的特殊符号
            mean_clean = re.sub(r'[^\w\u4e00-\u9fa5]', '', meaning_str)
            if opt_clean in mean_clean or mean_clean in opt_clean:
                return 1.0
            # 如果不包含，可能是OCR误差，降级到模糊匹配
            return SequenceMatcher(None, mean_clean, opt_clean).ratio()

        # === 模式2：通用字典模式 (切词匹配) ===
        meaning_clean = re.sub(r'\b[a-z]+\.', '', meaning_str)
        keywords = re.split(r'[,，;；]', meaning_clean)

        max_score = 0.0
        for kw in keywords:
            kw = re.sub(r'[^\w\u4e00-\u9fa5]', '', kw)
            if not kw: continue

            if opt_clean == kw: return 1.0
            if opt_clean in kw: return 1.0
            if kw in opt_clean: return 1.0

            score = SequenceMatcher(None, kw, opt_clean).ratio()
            if score > max_score:
                max_score = score

        return max_score

    def run(self):
        print("🚀 V13.0 自进化版已启动！")

        while True:
            try:
                img_pil, w, h = self.capture_window()
                # 答题时使用二值化图像提高准确率
                processed_img = self.preprocess_image(img_pil)

                result = ocr.ocr(processed_img, cls=False)

                if not result or not result[0]:
                    time.sleep(0.05)
                    continue

                res_data = result[0]
                all_text = "".join([line[1][0] for line in res_data]).lower()

                # --- 1. 状态判断：结算页面 ---
                if "win" in all_text or "lose" in all_text or "返回" in all_text or "战绩" in all_text:
                    # === 优化点1：先学习，后点击 ===
                    # 传入原始彩色图片用于学习（避免遮罩挡住中间列表）
                    self.learn_from_result(img_pil)

                    print("🏆 结算操作：准备点击返回")
                    found = False
                    for line in res_data:
                        if "返回" in line[1][0]:
                            box = line[0]
                            self.click_relative((box[0][0] + box[2][0]) / 2, (box[0][1] + box[2][1]) / 2)
                            found = True
                            break
                    if not found:
                        self.click_relative(w * 0.25, h * 0.88)

                    # 学习完且点击后，稍微多睡一会防止连点
                    time.sleep(2.0)
                    continue

                # --- 2. 状态判断：开始/继续 ---
                if "开始" in all_text or "再来" in all_text:
                    print("🔘 点击开始")
                    for line in res_data:
                        if "开始" in line[1][0] or "再来" in line[1][0]:
                            box = line[0]
                            self.click_relative((box[0][0] + box[2][0]) / 2, (box[0][1] + box[2][1]) / 2)
                            time.sleep(1.5)
                    continue

                # --- 3. 答题逻辑 ---
                en_word = None
                options = []

                for line in res_data:
                    text = line[1][0].strip()
                    box = line[0]
                    cy = (box[0][1] + box[2][1]) / 2
                    rel_y = cy / h

                    is_valid = re.search(r'[a-zA-Z]{2,}', text) and not re.search(r'[\u4e00-\u9fa5]', text)

                    if 0.10 < rel_y < 0.48:
                        if is_valid:
                            if text.upper() not in ["VS", "PK", "LOSE", "WIN", "SCORE"]:
                                en_word = text

                    elif 0.50 < rel_y < 0.98:
                        options.append({'text': text, 'x': (box[0][0] + box[2][0]) / 2, 'y': cy})

                if en_word == self.last_word and (time.time() - self.last_action_time < 2.0):
                    time.sleep(0.05)
                    continue

                if en_word and len(options) >= 2:
                    # 清洗单词
                    clean_word = re.sub(r'[^\w\s\-\']', '', en_word).strip().lower()

                    # === 优化点2：优先查偷题本 ===
                    meaning = None
                    is_exact_mode = False

                    # A. 查偷题本
                    if clean_word in self.cheat_sheet:
                        meaning = self.cheat_sheet[clean_word]
                        is_exact_mode = True
                        print(f"😈 [偷题本命中] {en_word} -> {meaning[:10]}...")

                    # B. 查通用词典 (A未命中时)
                    if not meaning:
                        meaning = self.dictionary.get(clean_word)
                        if not meaning:
                            # 尝试去空格容错
                            meaning = self.dictionary.get(clean_word.replace(" ", ""))
                        if meaning:
                            print(f"📖 [通用库查询] {en_word} -> {meaning[:10]}...")

                    # C. 匹配选项
                    if meaning:
                        best_opt = None
                        max_score = 0.0

                        for opt in options:
                            # 传入匹配模式参数
                            score = self.calculate_similarity(meaning, opt['text'], is_exact_match_mode=is_exact_mode)

                            if score > max_score:
                                max_score = score
                                best_opt = opt

                        # 如果是偷题本来源，阈值可以低一点(因为内容是精准的)；如果是通用库，要求高一点
                        threshold = 0.3 if is_exact_mode else 0.5

                        if max_score > threshold:
                            print(f"⚡ 命中: {best_opt['text']} (分值:{max_score:.2f})")
                            self.click_relative(best_opt['x'], best_opt['y'])
                        else:
                            print(f"   ⚠️ 分数过低({max_score:.2f})，根据相关性强行选一个最优的...")
                            # 优化点2后半部分：若仍没有，选择意思最相关的(即当前分值最高的那个，即使很低)
                            # 如果连0分都没有，那就只能蒙了
                            if best_opt and max_score > 0:
                                print(f"   ⚡ 强行选择: {best_opt['text']}")
                                self.click_relative(best_opt['x'], best_opt['y'])
                            else:
                                print("   🎲 没看懂，随机蒙！")
                                target_opt = random.choice(options)
                                self.click_relative(target_opt['x'], target_opt['y'])
                    else:
                        print(f"   🎲 生词({en_word})，随机蒙！")
                        target_opt = random.choice(options)
                        self.click_relative(target_opt['x'], target_opt['y'])

                    # 记录操作防止连点
                    self.last_word = en_word
                    self.last_action_time = time.time()
                    time.sleep(0.3)

                time.sleep(0.05)

            except Exception as e:
                # print(f"Err: {e}")
                time.sleep(0.1)


if __name__ == '__main__':
    bot = OptimizedBot()
    bot.run()