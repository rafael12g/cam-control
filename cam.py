import cv2
import numpy as np
import mediapipe as mp
import pyautogui
import math
import time
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL

# --- CONFIGURATION ---
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0
wCam, hCam = 1280, 720
frameR = 140 # Cadre souris
SMOOTHING = 6 # Augmenté pour éviter les tremblements

# Paramètres Clic Auto
DWELL_TIME = 1.0
DWELL_DIST = 20

# --- COULEURS ---
C_MOUSE = (0, 255, 255)
C_CMD = (255, 0, 255)
C_CLICK = (0, 255, 0)
C_ALERT = (0, 0, 255)

# --- AUDIO ---
volume = None
minVol, maxVol = -65.0, 0.0
try:
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = interface.QueryInterface(IAudioEndpointVolume)
    volRange = volume.GetVolumeRange()
    minVol, maxVol = volRange[0], volRange[1]
except: pass

# --- MEDIAPIPE (Mode Haute Précision) ---
mpHands = mp.solutions.hands
hands = mpHands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    model_complexity=1, 
    min_detection_confidence=0.8,
    min_tracking_confidence=0.8
)
mpDraw = mp.solutions.drawing_utils

# --- VARIABLES ---
wScr, hScr = pyautogui.size()
plocX, plocY = 0, 0
clocX, clocY = 0, 0

# Variables Clic & Scroll
dwell_timer = 0
prev_idx_x, prev_idx_y = 0, 0
is_dwelling = False
anchor_x, anchor_y = 0, 0
is_scrolling = False

# Variables Privacy (Cross Arms)
privacy_mode = False
cross_timer = 0
cooldown_cmd = 0
feedback_text = ""
feedback_timer = 0

def main():
    global plocX, plocY, clocX, clocY, dwell_timer, prev_idx_x, prev_idx_y, is_dwelling
    global anchor_x, anchor_y, is_scrolling, privacy_mode
    global cross_timer, cooldown_cmd, feedback_text, feedback_timer

    cap = cv2.VideoCapture(0)
    cap.set(3, wCam)
    cap.set(4, hCam)
    cap.set(cv2.CAP_PROP_FPS, 60)

    print(">>> JARVIS ONLINE. Croise les bras pour couper la video.")

    while True:
        try:
            success, img = cap.read()
            if not success: continue

            img = cv2.flip(img, 1)
            h, w, _ = img.shape
            
            # --- MODE ÉCRAN NOIR (PRIVACY) ---
            if privacy_mode:
                # Écran noir avec texte rouge
                overlay = np.zeros((h, w, 3), dtype='uint8')
                cv2.putText(overlay, "SYSTEM LOCKED", (w//2 - 200, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1.5, C_ALERT, 3)
                cv2.putText(overlay, "(Croise les poignets pour deverrouiller)", (w//2 - 230, h//2 + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1)
                
                # On scanne quand même pour détecter le déverrouillage
                imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                results = hands.process(imgRGB)
                
                if results.multi_hand_landmarks and len(results.multi_hand_landmarks) == 2:
                    # On check si les poignets sont croisés (proches l'un de l'autre)
                    w1 = results.multi_hand_landmarks[0].landmark[0]
                    w2 = results.multi_hand_landmarks[1].landmark[0]
                    dist_wrists = math.hypot((w1.x-w2.x)*w, (w1.y-w2.y)*h)

                    if dist_wrists < 100: # Si poignets croisés
                        if cross_timer == 0: cross_timer = time.time()
                        # Barre de chargement déverrouillage
                        prog = (time.time() - cross_timer) / 1.0
                        cv2.rectangle(overlay, (w//2-100, h//2+100), (w//2+100, h//2+120), (50,50,50), -1)
                        cv2.rectangle(overlay, (w//2-100, h//2+100), (w//2-100+int(200*prog), h//2+120), C_CLICK, -1)
                        
                        if prog >= 1.0:
                            privacy_mode = False
                            cross_timer = 0
                            print(">>> UNLOCKED")
                    else:
                        cross_timer = 0

                cv2.imshow("JARVIS HUD", overlay)
                if cv2.waitKey(1) & 0xFF == ord('q'): break
                continue

            # --- MODE NORMAL ---
            imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(imgRGB)

            # Zones HUD
            cv2.line(img, (w//2, 0), (w//2, h), (100, 100, 100), 1)
            cv2.putText(img, "COMMANDES", (50, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, C_CMD, 2)
            cv2.putText(img, "SOURIS", (w//2 + 50, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, C_MOUSE, 2)

            if results.multi_hand_landmarks:
                
                # --- DETECTION "X" (CROSS ARMS) POUR VERROUILLER ---
                if len(results.multi_hand_landmarks) == 2:
                    w1 = results.multi_hand_landmarks[0].landmark[0]
                    w2 = results.multi_hand_landmarks[1].landmark[0]
                    dist_wrists = math.hypot((w1.x-w2.x)*w, (w1.y-w2.y)*h)
                    
                    if dist_wrists < 100:
                        cx, cy = int((w1.x+w2.x)*w/2), int((w1.y+w2.y)*h/2)
                        cv2.circle(img, (cx, cy), 50, C_ALERT, 2)
                        cv2.putText(img, "LOCKING...", (cx-60, cy-60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, C_ALERT, 2)
                        
                        if cross_timer == 0: cross_timer = time.time()
                        if time.time() - cross_timer > 1.0: # Maintenir 1s
                            privacy_mode = True
                            cross_timer = 0
                    else:
                        cross_timer = 0

                # TRAITEMENT DES MAINS INDIVIDUELLES
                for hand_lms in results.multi_hand_landmarks:
                    wrist_x = hand_lms.landmark[0].x
                    is_right_hand = wrist_x > 0.5

                    lmList = []
                    for id, lm in enumerate(hand_lms.landmark):
                        lmList.append([id, int(lm.x * w), int(lm.y * h)])

                    # =========================================================
                    # 🖱️ MAIN DROITE : SOURIS + CLIC AUTO
                    # =========================================================
                    if is_right_hand:
                        mpDraw.draw_landmarks(img, hand_lms, mpHands.HAND_CONNECTIONS, mpDraw.DrawingSpec(color=C_MOUSE))
                        
                        x1, y1 = lmList[8][1:] # Index
                        # Index levé, Majeur baissé
                        if lmList[8][2] < lmList[6][2] and lmList[12][2] > lmList[10][2]:
                            cv2.rectangle(img, (w//2 + frameR, frameR), (w - frameR, h - frameR), C_MOUSE, 1)

                            # Déplacement
                            x3 = np.interp(x1, (w//2 + frameR, w - frameR), (0, wScr))
                            y3 = np.interp(y1, (frameR, h - frameR), (0, hScr))
                            clocX = plocX + (x3 - plocX) / SMOOTHING
                            clocY = plocY + (y3 - plocY) / SMOOTHING
                            try: pyautogui.moveTo(clocX, clocY)
                            except: pass
                            plocX, plocY = clocX, clocY

                            # Clic Auto (Immobile)
                            dist_move = math.hypot(x1 - prev_idx_x, y1 - prev_idx_y)
                            if dist_move < DWELL_DIST:
                                if not is_dwelling:
                                    dwell_timer = time.time()
                                    is_dwelling = True
                                
                                prog = (time.time() - dwell_timer) / DWELL_TIME
                                # Animation Cercle
                                cv2.ellipse(img, (x1, y1), (20, 20), 0, 0, int(360*prog), C_CLICK, 2)

                                if prog >= 1.0:
                                    pyautogui.click()
                                    cv2.circle(img, (x1, y1), 25, C_CLICK, -1)
                                    is_dwelling = False
                                    prev_idx_x, prev_idx_y = 10000, 10000 # Force reset
                                    dwell_timer = time.time() + 1.0 # Pause
                            else:
                                is_dwelling = False
                                prev_idx_x, prev_idx_y = x1, y1
                            
                            cv2.circle(img, (x1, y1), 8, C_MOUSE, -1)

                    # =========================================================
                    # 🎮 MAIN GAUCHE : COMMANDES
                    # =========================================================
                    else:
                        mpDraw.draw_landmarks(img, hand_lms, mpHands.HAND_CONNECTIONS, mpDraw.DrawingSpec(color=C_CMD))
                        
                        # Detection des doigts
                        fingers = []
                        # Pouce
                        fingers.append(1 if lmList[4][0] > lmList[3][0] else 0)
                        for id in [8, 12, 16, 20]:
                            fingers.append(1 if lmList[id][2] < lmList[id-2][2] else 0)
                        
                        idx_up = fingers[1]
                        mid_up = fingers[2]
                        pinky_up = fingers[4]

                        # 1. SCROLL JOYSTICK (Index + Majeur levés)
                        if idx_up and mid_up and not pinky_up:
                            cx, cy = (lmList[8][1] + lmList[12][1]) // 2, (lmList[8][2] + lmList[12][2]) // 2
                            if not is_scrolling:
                                anchor_x, anchor_y = cx, cy
                                is_scrolling = True
                            
                            cv2.line(img, (anchor_x, anchor_y), (cx, cy), C_CMD, 2)
                            cv2.circle(img, (anchor_x, anchor_y), 5, (150,150,150), -1)

                            dy = cy - anchor_y
                            if abs(dy) > 30: # Scroll Vertical
                                speed = int((abs(dy)-30)/5)
                                if dy < 0: pyautogui.scroll(speed)
                                else: pyautogui.scroll(-speed)
                        else:
                            is_scrolling = False

                        # 2. VOLUME (Pince Pouce-Index uniquement)
                        if idx_up and not mid_up:
                            cv2.line(img, (lmList[4][1], lmList[4][2]), (lmList[8][1], lmList[8][2]), C_CMD, 2)
                            dist_vol = math.hypot(lmList[4][1]-lmList[8][1], lmList[4][2]-lmList[8][2])
                            if volume:
                                vol = np.interp(dist_vol, [20, 150], [minVol, maxVol])
                                volume.SetMasterVolumeLevel(vol, None)
                                cv2.putText(img, f"VOL: {int(np.interp(dist_vol, [20, 150], [0, 100]))}%", (50, h-80), cv2.FONT_HERSHEY_SIMPLEX, 1, C_CMD, 2)

            # Feedback Text
            if time.time() - feedback_timer < 1.0:
                cv2.putText(img, feedback_text, (50, h-50), cv2.FONT_HERSHEY_SIMPLEX, 1, C_CLICK, 2)

            # FPS
            cTime = time.time()
            fps = 1 / (cTime - 0.001)
            cv2.putText(img, f"FPS: {int(fps)}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow("JARVIS HUD", img)
            if cv2.waitKey(1) & 0xFF == ord('q'): break
        except Exception as e:
            pass

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()