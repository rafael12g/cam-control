import cv2
from cvzone.HandTrackingModule import HandDetector
import numpy as np
import sounddevice as sd

# --- 1. GÉNÉRATEUR DE SON AMÉLIORÉ (Synthé) ---
print("Synthèse des sons en cours...")

def generate_rich_tone(frequency, duration=0.4, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # On mélange 3 ondes pour un son plus "organique"
    # Fondamentale (100%) + Harmonique 2 (50%) + Harmonique 3 (30%)
    tone = (np.sin(frequency * t * 2 * np.pi) + 
            0.5 * np.sin(2 * frequency * t * 2 * np.pi) + 
            0.3 * np.sin(3 * frequency * t * 2 * np.pi))
    
    # Normaliser pour que le volume ne sature pas (rester entre -1 et 1)
    tone = tone / np.max(np.abs(tone))
    
    # Enveloppe ADSR simple (Attack, Release) pour éviter le "clic"
    attack = int(sample_rate * 0.05) # 0.05s de montée
    release = int(sample_rate * 0.1) # 0.1s de descente
    
    envelope = np.ones_like(tone)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)
    
    return tone * envelope

# Gamme de Do Majeur (Do, Ré, Mi, Fa, Sol, La, Si)
notes_freq = {
    "DO": 261.63,
    "RE": 293.66,
    "MI": 329.63,
    "FA": 349.23,
    "SOL": 392.00,
    "LA": 440.00,
    "SI": 493.883,
    "AI": 1500.00
}

# Pré-calcul des sons
sounds = {k: generate_rich_tone(v) for k, v in notes_freq.items()}
print("Prêt !")

# --- 2. CONFIGURATION CAMÉRA & DÉTECTION ---
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)
detector = HandDetector(detectionCon=0.8, maxHands=1)

# Configuration des touches [x, y, w, h, note, couleur, état_précédent]
# L'état précédent sert à savoir si le doigt était DÉJÀ dedans (pour ne pas répéter le son)
keys_config = [
    [50, 300, 150, 250, "DO", (0, 0, 255)],    # Rouge
    [220, 300, 150, 250, "RE", (0, 127, 255)], # Orange
    [390, 300, 150, 250, "MI", (0, 255, 255)], # Jaune
    [560, 300, 150, 250, "FA", (0, 255, 0)],   # Vert
    [730, 300, 150, 250, "SOL", (255, 0, 0)],  # Bleu
    [900, 300, 150, 250, "LA", (130, 0, 75)],  # Indigo
    [1070, 300, 150, 250, "SI", (148, 0, 211)], # Violet
    [1240, 300, 150, 250, "AI", (255, 255, 255)] # Blanc
]

# Dictionnaire pour suivre l'état "appuyé" de chaque touche (False = relâché, True = appuyé)
key_states = {note: False for note in notes_freq}

while True:
    success, img = cap.read()
    if not success: break
    
    img = cv2.flip(img, 1)
    
    # Création d'un calque pour l'effet de transparence (Glassmorphism)
    overlay = img.copy()
    
    hands, img = detector.findHands(img, flipType=False)
    
    # Position du doigt (initialisée hors de l'écran par défaut)
    finger_x, finger_y = -1, -1

    if hands:
        # On prend le bout de l'index (8) ET le bout du majeur (12) pour plus de précision si tu veux
        # Ici on reste sur l'index (8)
        lmList = hands[0]['lmList']
        finger_x, finger_y = lmList[8][0], lmList[8][1]
        
        # Pointeur visuel
        cv2.circle(img, (finger_x, finger_y), 10, (255, 255, 255), cv2.FILLED)
        cv2.circle(img, (finger_x, finger_y), 20, (255, 255, 255), 2)

    # --- BOUCLE SUR LES TOUCHES ---
    for i, key in enumerate(keys_config):
        x, y, w, h, note, color = key
        
        # Vérifier si le doigt est dans la touche
        is_inside = x < finger_x < x + w and y < finger_y < y + h
        
        if is_inside:
            # -- LOGIQUE DE FRAPPE --
            # Si on vient d'entrer (état passe de False à True) -> ON JOUE
            if not key_states[note]:
                sd.play(sounds[note], 44100) # Joue le son de manière asynchrone
                key_states[note] = True      # On mémorise que la touche est enfoncée
            
            # Visuel "Touche Enfoncée" (Pleine couleur + plus clair)
            cv2.rectangle(overlay, (x, y), (x + w, y + h), color, cv2.FILLED)
            # Petit effet de "brillance" quand on appuie
            cv2.rectangle(overlay, (x+10, y+10), (x+w-10, y+h-10), (255, 255, 255), 2)
            
        else:
            # Si le doigt n'est pas dedans, on reset l'état
            key_states[note] = False
            
            # Visuel "Touche Repos" (Juste les contours et un fond très léger)
            cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 4) # Contour épais
            cv2.rectangle(overlay, (x, y), (x + w, y + h), color, cv2.FILLED) # Fond rempli pour la transparence
            
        # Texte de la note
        cv2.putText(img, note, (x + 40, y + h - 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # --- APPLIQUER LA TRANSPARENCE ---
    # On mélange l'image originale (img) avec le calque coloré (overlay)
    # 0.7 = force de l'image caméra, 0.3 = force des couleurs
    img = cv2.addWeighted(overlay, 0.3, img, 0.7, 0)

    cv2.imshow("Piano Virtuel Pro", img)
    
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()