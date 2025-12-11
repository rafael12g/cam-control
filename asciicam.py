import cv2
import os

# Liste des caractères du plus sombre au plus clair
# Tu peux changer l'ordre ou les caractères pour varier le style
ASCII_CHARS = " .:-=+*#%@"

def pixel_to_ascii(image, new_width=100):
    # 1. Passer l'image en noir et blanc
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 2. Redimensionner l'image
    # Les caractères sont plus hauts que larges, on corrige avec le facteur 0.55
    height, width = gray_image.shape
    aspect_ratio = height / width
    new_height = int(new_width * aspect_ratio * 0.55)
    resized_image = cv2.resize(gray_image, (new_width, new_height))
    
    # 3. Remplacer chaque pixel par un caractère
    ascii_str = ""
    # On calcule quel caractère utiliser selon la luminosité du pixel (0-255)
    divisor = 255 // (len(ASCII_CHARS) - 1)
    
    for pixel_value in resized_image.flatten():
        ascii_str += ASCII_CHARS[pixel_value // divisor]
        
    return ascii_str, new_width

def main():
    # Ouvre la webcam (0 est généralement la webcam par défaut)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Impossible d'ouvrir la webcam !")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convertir la frame en ASCII
            ascii_art, width = pixel_to_ascii(frame)
            
            # Formater l'image finale (ajouter les sauts de ligne)
            final_image = "\n".join(
                [ascii_art[index:(index + width)] for index in range(0, len(ascii_art), width)]
            )
            
            # Nettoyer la console pour afficher la nouvelle frame
            # 'cls' pour Windows, 'clear' pour Mac/Linux
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print(final_image)
            
            # Petite pause pour éviter de faire surchauffer le processeur inutilement
            # (Appuie sur Ctrl+C dans le terminal pour arrêter)
            
    except KeyboardInterrupt:
        print("\nArrêt du programme...")
        cap.release()

if __name__ == "__main__":
    main()